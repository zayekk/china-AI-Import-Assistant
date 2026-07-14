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

logger = logging.getLogger(__name__)


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

        last_error: Exception | None = None

        for attempt in range(1, max_retries + 2):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        self.api_url, headers=self._headers(), json=payload
                    )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return self._safe_json_parse(content)

            except httpx.HTTPStatusError as exc:
                last_error = exc
                logger.warning(
                    "Mistral API HTTP error (attempt %s/%s): %s - %s",
                    attempt,
                    max_retries + 1,
                    exc.response.status_code,
                    exc.response.text[:500],
                )
                if exc.response.status_code in (401, 403):
                    # Inutile de retry sur une erreur d'authentification
                    break
                time.sleep(min(2 ** attempt, 8))

            except (httpx.RequestError, KeyError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.warning(
                    "Mistral API error (attempt %s/%s): %s",
                    attempt,
                    max_retries + 1,
                    str(exc),
                )
                time.sleep(min(2 ** attempt, 8))

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

        for attempt in range(1, max_retries + 2):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        self.ocr_api_url, headers=self._headers(), json=payload
                    )
                response.raise_for_status()
                data = response.json()
                pages = data.get("pages", [])
                return "\n".join(page.get("markdown", "") for page in pages).strip()

            except httpx.HTTPStatusError as exc:
                last_error = exc
                logger.warning(
                    "Mistral OCR API HTTP error (attempt %s/%s): %s - %s",
                    attempt,
                    max_retries + 1,
                    exc.response.status_code,
                    exc.response.text[:500],
                )
                if exc.response.status_code in (401, 403):
                    break
                time.sleep(min(2 ** attempt, 8))

            except (httpx.RequestError, KeyError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.warning(
                    "Mistral OCR API error (attempt %s/%s): %s",
                    attempt,
                    max_retries + 1,
                    str(exc),
                )
                time.sleep(min(2 ** attempt, 8))

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
