"""
Client HTTP pour l'API Mistral.
Encapsule les appels chat completions et OCR avec gestion d'erreurs et retries.
"""
import base64
import json
import logging
import time
from typing import Any

import httpx

from app.core.config import settings

from ai_engine.services.timing import StepTimer, estimate_tokens, log_step

logger = logging.getLogger(__name__)

# Plafond du backoff exponentiel entre tentatives sur erreur TRANSITOIRE (5xx, erreur réseau,
# rate limit sans Retry-After) : 2, 4, 8, 16... secondes, plafonné à 16s. Un plafond plus élevé
# qu'avant (8s) car les erreurs transitoires bénéficient réellement d'une pause plus longue.
_BACKOFF_CAP_SECONDS = 16

# Sur un ReadTimeout, retenter avec EXACTEMENT le même prompt (donc probablement le même temps
# de génération) a un rendement décroissant : une seule tentative supplémentaire suffit à
# absorber une lenteur ponctuelle, sans faire attendre l'utilisateur 3x le timeout complet
# (avec max_retries=2 classique, un pire cas de 3 tentatives à 90s chacune = 4m30 d'attente
# avant le repli local). Les erreurs transitoires (réseau, 5xx, 429) gardent le budget complet.
_MAX_RETRIES_ON_TIMEOUT = 1


def _parse_retry_after(header_value: str) -> float:
    """
    Parse l'en-tête HTTP Retry-After (RFC 9110) : soit un nombre de secondes, soit une date
    HTTP. On ne gère explicitement que le format numérique (de très loin le plus utilisé par
    les API de rate limiting comme celle de Mistral) ; toute valeur non numérique retombe sur
    le backoff exponentiel standard plutôt que d'échouer sur un format de date à parser.
    """
    try:
        return max(0.0, float(header_value))
    except (TypeError, ValueError):
        return float(_BACKOFF_CAP_SECONDS)


class MistralAPIError(Exception):
    """Erreur levée en cas d'échec de l'appel à l'API Mistral."""


class MistralClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        api_url: str | None = None,
        timeout: int | None = None,
    ):
        self.api_key = api_key or settings.MISTRAL_API_KEY
        self.model = model or settings.MISTRAL_MODEL
        self.api_url = api_url or settings.MISTRAL_API_URL
        self.timeout = timeout or settings.MISTRAL_TIMEOUT_SECONDS
        self.ocr_api_url = settings.MISTRAL_OCR_API_URL
        self.ocr_model = settings.MISTRAL_OCR_MODEL

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise MistralAPIError(
                "MISTRAL_API_KEY non configurée. Définissez-la dans le fichier .env"
            )
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat_completion_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_retries: int = 2,
    ) -> dict[str, Any]:
        """
        Appelle Mistral en mode chat completion et force une réponse JSON.
        Retourne le dict Python parsé depuis la réponse du modèle.

        Stratégie de retry DIFFÉRENCIÉE par type d'erreur (voir _MAX_RETRIES_ON_TIMEOUT et
        _BACKOFF_CAP_SECONDS) : un ReadTimeout sur un prompt volumineux a peu de chances d'être
        résolu par une 3e tentative identique (même prompt, même modèle, temps de génération
        probablement similaire) — une seule tentative supplémentaire suffit, pour ne pas faire
        attendre l'utilisateur plusieurs multiples du timeout avant le repli local. Les erreurs
        réellement transitoires (réseau, 5xx, rate limit) gardent le budget complet de retries,
        avec un vrai backoff exponentiel (et Retry-After honoré sur 429 si présent).
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        system_tokens = estimate_tokens(system_prompt)
        user_tokens = estimate_tokens(user_prompt)
        log_step(
            "prompt_size",
            0.0,
            model=self.model,
            system_chars=len(system_prompt),
            system_tokens_est=system_tokens,
            user_chars=len(user_prompt),
            user_tokens_est=user_tokens,
            total_tokens_est=system_tokens + user_tokens,
            timeout_s=self.timeout,
        )

        last_error: Exception | None = None
        call_timer = StepTimer()
        attempt = 0
        # Nombre de tentatives déjà "consommées" spécifiquement par des timeouts, pour
        # appliquer le budget réduit (_MAX_RETRIES_ON_TIMEOUT) indépendamment des tentatives
        # consommées par d'autres types d'erreur (qui gardent le budget `max_retries` complet).
        timeout_attempts = 0

        while True:
            attempt += 1
            attempt_timer = StepTimer()
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        self.api_url, headers=self._headers(), json=payload
                    )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                network_duration = attempt_timer.elapsed()

                parse_timer = StepTimer()
                result = self._safe_json_parse(content)
                log_step(
                    "mistral_call",
                    network_duration,
                    attempt=attempt,
                    model=self.model,
                    outcome="success",
                    response_chars=len(content),
                )
                log_step("json_parse", parse_timer.elapsed(), response_chars=len(content))
                log_step("mistral_call_total", call_timer.elapsed(), attempts=attempt, outcome="success")
                return result

            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code
                log_step(
                    "mistral_call",
                    attempt_timer.elapsed(),
                    attempt=attempt,
                    model=self.model,
                    outcome=f"http_{status}",
                )
                logger.warning(
                    "Mistral API HTTP error (attempt %s): %s - %s",
                    attempt,
                    status,
                    exc.response.text[:500],
                )
                if status in (401, 403):
                    break  # inutile de retry sur une erreur d'authentification
                if attempt > max_retries:
                    break
                retry_after = exc.response.headers.get("Retry-After")
                if status == 429 and retry_after:
                    wait_seconds = _parse_retry_after(retry_after)
                else:
                    wait_seconds = min(2 ** attempt, _BACKOFF_CAP_SECONDS)
                logger.info("Nouvelle tentative dans %.1fs (backoff)", wait_seconds)
                time.sleep(wait_seconds)

            except httpx.TimeoutException as exc:
                last_error = exc
                timeout_attempts += 1
                log_step(
                    "mistral_call",
                    attempt_timer.elapsed(),
                    attempt=attempt,
                    model=self.model,
                    outcome="timeout",
                )
                logger.warning(
                    "Mistral API timeout (attempt %s, budget timeout %s/%s) après %.1fs — "
                    "prompt total ≈%s tokens, timeout configuré %ss.",
                    attempt,
                    timeout_attempts,
                    _MAX_RETRIES_ON_TIMEOUT + 1,
                    attempt_timer.elapsed(),
                    system_tokens + user_tokens,
                    self.timeout,
                )
                if timeout_attempts > _MAX_RETRIES_ON_TIMEOUT:
                    break
                time.sleep(min(2 ** attempt, _BACKOFF_CAP_SECONDS))

            except (httpx.RequestError, KeyError, json.JSONDecodeError) as exc:
                last_error = exc
                log_step(
                    "mistral_call",
                    attempt_timer.elapsed(),
                    attempt=attempt,
                    model=self.model,
                    outcome=type(exc).__name__,
                )
                logger.warning("Mistral API error (attempt %s): %s", attempt, str(exc))
                if attempt > max_retries:
                    break
                time.sleep(min(2 ** attempt, _BACKOFF_CAP_SECONDS))

        log_step("mistral_call_total", call_timer.elapsed(), attempts=attempt, outcome="failed")
        raise MistralAPIError(f"Échec de l'appel à Mistral après plusieurs tentatives: {last_error}")

    def ocr_extract_text(
        self,
        image_bytes: bytes,
        content_type: str = "image/png",
        max_retries: int = 2,
    ) -> str:
        """
        Extrait le texte d'une image via l'API OCR dédiée de Mistral (mistral-ocr-latest).
        Utilisée en repli par ai_engine/services/ocr_service.py lorsque le binaire
        Tesseract local n'est pas disponible (ex. environnement serverless comme Vercel).
        """
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        payload = {
            "model": self.ocr_model,
            "document": {
                "type": "image_url",
                "image_url": f"data:{content_type};base64,{b64_image}",
            },
        }

        last_error: Exception | None = None
        total_timer = StepTimer()

        for attempt in range(1, max_retries + 2):
            call_timer = StepTimer()
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        self.ocr_api_url, headers=self._headers(), json=payload
                    )
                response.raise_for_status()
                data = response.json()
                pages = data.get("pages", [])
                text = "\n".join(page.get("markdown", "") for page in pages).strip()
                log_step(
                    "mistral_ocr_call",
                    call_timer.elapsed(),
                    attempt=attempt,
                    model=self.ocr_model,
                    image_bytes=len(image_bytes),
                    result_chars=len(text),
                    outcome="success",
                )
                log_step("mistral_ocr_call_total", total_timer.elapsed(), attempts=attempt, outcome="success")
                return text

            except httpx.TimeoutException as exc:
                last_error = exc
                log_step(
                    "mistral_ocr_call",
                    call_timer.elapsed(),
                    attempt=attempt,
                    model=self.ocr_model,
                    timeout_configured=self.timeout,
                    outcome="timeout",
                )
                logger.warning(
                    "Mistral OCR API timeout (attempt %s/%s, timeout configuré=%ss): %s",
                    attempt,
                    max_retries + 1,
                    self.timeout,
                    str(exc),
                )
                time.sleep(min(2 ** attempt, _BACKOFF_CAP_SECONDS))

            except httpx.HTTPStatusError as exc:
                last_error = exc
                log_step(
                    "mistral_ocr_call",
                    call_timer.elapsed(),
                    attempt=attempt,
                    model=self.ocr_model,
                    status_code=exc.response.status_code,
                    outcome="http_error",
                )
                logger.warning(
                    "Mistral OCR API HTTP error (attempt %s/%s): %s - %s",
                    attempt,
                    max_retries + 1,
                    exc.response.status_code,
                    exc.response.text[:500],
                )
                if exc.response.status_code in (401, 403):
                    break
                time.sleep(min(2 ** attempt, _BACKOFF_CAP_SECONDS))

            except (httpx.RequestError, KeyError, json.JSONDecodeError) as exc:
                last_error = exc
                log_step(
                    "mistral_ocr_call",
                    call_timer.elapsed(),
                    attempt=attempt,
                    model=self.ocr_model,
                    outcome="request_error",
                )
                logger.warning(
                    "Mistral OCR API error (attempt %s/%s): %s",
                    attempt,
                    max_retries + 1,
                    str(exc),
                )
                time.sleep(min(2 ** attempt, _BACKOFF_CAP_SECONDS))

        log_step("mistral_ocr_call_total", total_timer.elapsed(), outcome="failed")
        raise MistralAPIError(f"Échec de l'appel OCR à Mistral après plusieurs tentatives: {last_error}")

    @staticmethod
    def _extract_json_object(text: str) -> str | None:
        """
        Extrait le premier bloc {...} équilibré du texte (comptage d'accolades, en ignorant
        celles présentes dans les chaînes JSON). Utilisé UNIQUEMENT en repli quand le parsing
        direct échoue (ex: le modèle a ajouté une phrase avant/après le JSON malgré le mode
        response_format=json_object) — ne modifie jamais le contenu du JSON lui-même, se
        contente d'en isoler les bornes exactes. Retourne None si aucun bloc équilibré trouvé.
        """
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escaped = False
        for idx in range(start, len(text)):
            char = text[idx]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : idx + 1]
        return None

    @classmethod
    def _safe_json_parse(cls, content: str) -> dict[str, Any]:
        """
        Parse le JSON renvoyé par le modèle, en nettoyant d'éventuelles balises markdown, avec
        un repli qui isole le bloc {...} équilibré si le modèle a entouré le JSON de texte
        (jamais de correction du CONTENU JSON lui-même — uniquement de ses bornes — donc aucune
        perte de qualité/fidélité sur les champs renvoyés par l'IA).
        """
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as first_error:
            extracted = cls._extract_json_object(cleaned)
            if extracted is not None:
                try:
                    return json.loads(extracted)
                except json.JSONDecodeError:
                    pass  # le bloc extrait n'était pas valide non plus -> on remonte l'erreur d'origine
            raise MistralAPIError(
                f"Réponse IA non parsable en JSON: {first_error}\nContenu: {content[:500]}"
            )


mistral_client = MistralClient()
