"""
Tests unitaires : MistralClient.chat_completion_json / _safe_json_parse (appel chat
completion vers l'API Mistral), sans réseau réel (httpx.Client mocké).

Couvre la régression diagnostiquée où toute analyse basculait silencieusement sur le
repli local : MISTRAL_API_KEY non chargée (voir test_config_mistral_client.py pour la
cause racine, ce fichier couvre le comportement du client une fois la clé disponible)
et le durcissement du parsing JSON (extraction du bloc {...} si le modèle entoure sa
réponse de texte malgré response_format=json_object).
"""
from unittest.mock import MagicMock, patch

import httpx
import pytest

from ai_engine.services.mistral_client import MistralAPIError, MistralClient


def _mock_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def _completion_payload(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


# ---------------------------------------------------------------------------
# _safe_json_parse() : parsing direct + repli d'extraction de bloc {...}
# ---------------------------------------------------------------------------


def test_safe_json_parse_valid_json():
    result = MistralClient._safe_json_parse('{"recommendation": "BUY"}')
    assert result == {"recommendation": "BUY"}


def test_safe_json_parse_strips_markdown_fences():
    result = MistralClient._safe_json_parse('```json\n{"recommendation": "BUY"}\n```')
    assert result == {"recommendation": "BUY"}


def test_safe_json_parse_recovers_json_wrapped_in_prose():
    """Repli : le modèle a ajouté une phrase avant/après le JSON malgré json_object mode —
    le bloc {...} équilibré est isolé et parsé, sans toucher à son contenu."""
    content = 'Voici le résultat demandé :\n{"recommendation": "BUY", "final_score": 80}\nJ\'espère que cela aide.'
    result = MistralClient._safe_json_parse(content)
    assert result == {"recommendation": "BUY", "final_score": 80}


def test_safe_json_parse_recovers_with_nested_braces_and_strings_containing_braces():
    """Le comptage d'accolades ne doit pas être perturbé par des accolades DANS une chaîne
    JSON (ex: un warning mentionnant du texte entre accolades)."""
    content = (
        'Réponse : {"warnings": ["Attention aux { faux accolades } dans le texte"], '
        '"nested": {"a": 1}} -- fin.'
    )
    result = MistralClient._safe_json_parse(content)
    assert result == {
        "warnings": ["Attention aux { faux accolades } dans le texte"],
        "nested": {"a": 1},
    }


def test_safe_json_parse_raises_clean_error_when_truly_unparsable():
    with pytest.raises(MistralAPIError):
        MistralClient._safe_json_parse("Ceci n'est pas du JSON du tout.")


def test_safe_json_parse_raises_when_extracted_block_is_itself_invalid():
    """Un bloc {...} équilibré mais syntaxiquement invalide (virgule finale) doit remonter
    l'erreur d'origine proprement, pas planter silencieusement."""
    with pytest.raises(MistralAPIError):
        MistralClient._safe_json_parse('Résultat: {"a": 1,}')


# ---------------------------------------------------------------------------
# chat_completion_json() : bout-en-bout avec httpx mocké
# ---------------------------------------------------------------------------


def test_chat_completion_json_requires_api_key():
    """
    MistralClient(api_key="") ne suffit PAS à isoler ce test : __init__ fait
    `api_key or settings.MISTRAL_API_KEY`, donc une chaîne vide retombe sur la clé réelle
    de l'environnement si backend/.env en contient une — ce qui déclencherait un VRAI appel
    réseau ici. On neutralise explicitement `settings.MISTRAL_API_KEY` pour rester isolé,
    déterministe et sans dépendance à la présence d'un .env local.
    """
    with patch("ai_engine.services.mistral_client.settings") as mock_settings:
        mock_settings.MISTRAL_API_KEY = ""
        mock_settings.MISTRAL_MODEL = "mistral-large-latest"
        mock_settings.MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
        mock_settings.MISTRAL_TIMEOUT_SECONDS = 60
        mock_settings.MISTRAL_OCR_API_URL = "https://api.mistral.ai/v1/ocr"
        mock_settings.MISTRAL_OCR_MODEL = "mistral-ocr-latest"
        client = MistralClient(api_key="")

        with pytest.raises(MistralAPIError, match="MISTRAL_API_KEY"):
            client.chat_completion_json(system_prompt="sys", user_prompt="user")


def test_chat_completion_json_returns_parsed_dict_on_success():
    client = MistralClient(api_key="test-key")
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.post.return_value = _mock_response(
            json_data=_completion_payload('{"recommendation": "BUY"}')
        )
        mock_client_cls.return_value.__enter__.return_value = mock_client

        result = client.chat_completion_json(system_prompt="sys", user_prompt="user")

    assert result == {"recommendation": "BUY"}


def test_chat_completion_json_recovers_prose_wrapped_json_end_to_end():
    client = MistralClient(api_key="test-key")
    content = 'Voici : {"recommendation": "CAUTION"} Merci.'
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.post.return_value = _mock_response(json_data=_completion_payload(content))
        mock_client_cls.return_value.__enter__.return_value = mock_client

        result = client.chat_completion_json(system_prompt="sys", user_prompt="user")

    assert result == {"recommendation": "CAUTION"}


def test_chat_completion_json_does_not_retry_on_auth_failure():
    client = MistralClient(api_key="bad-key")
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.post.return_value = _mock_response(status_code=401)
        mock_client_cls.return_value.__enter__.return_value = mock_client

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(MistralAPIError):
                client.chat_completion_json(system_prompt="sys", user_prompt="user", max_retries=2)

    # 401 -> abandon immédiat (pas d'intérêt à retenter avec la même clé invalide).
    assert mock_client.post.call_count == 1
    mock_sleep.assert_not_called()


def test_chat_completion_json_retries_on_transient_http_error():
    client = MistralClient(api_key="test-key")
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.post.side_effect = [
            _mock_response(status_code=500),
            _mock_response(json_data=_completion_payload('{"recommendation": "BUY"}')),
        ]
        mock_client_cls.return_value.__enter__.return_value = mock_client

        with patch("time.sleep"):
            result = client.chat_completion_json(system_prompt="sys", user_prompt="user", max_retries=2)

    assert result == {"recommendation": "BUY"}
    assert mock_client.post.call_count == 2


def test_chat_completion_json_error_message_includes_underlying_cause():
    """La MistralAPIError finale doit porter la cause exacte (statut HTTP, timeout...),
    pas un message générique — c'est ce message qui est journalisé avant le repli local."""
    client = MistralClient(api_key="test-key")
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.post.return_value = _mock_response(status_code=401)
        mock_client_cls.return_value.__enter__.return_value = mock_client

        with pytest.raises(MistralAPIError) as exc_info:
            client.chat_completion_json(system_prompt="sys", user_prompt="user")

    assert "401" in str(exc_info.value) or "error" in str(exc_info.value).lower()
