"""
Client HTTP pour l'API Mistral.
Encapsule les appels chat completions avec gestion d'erreurs et retries.
"""
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

    @staticmethod
    def _safe_json_parse(content: str) -> dict[str, Any]:
        """Parse le JSON renvoyé par le modèle, en nettoyant d'éventuelles balises markdown."""
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise MistralAPIError(f"Réponse IA non parsable en JSON: {exc}\nContenu: {content[:500]}")


mistral_client = MistralClient()
