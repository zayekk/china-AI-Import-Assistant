"""
Tests unitaires : MistralClient.ocr_extract_text (appel HTTP vers l'API OCR
dédiée de Mistral), sans réseau réel (httpx.Client mocké).
"""
import base64
from unittest.mock import MagicMock, patch

import pytest

from ai_engine.services.mistral_client import MistralAPIError, MistralClient


def _mock_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    if status_code >= 400:
        import httpx

        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def test_ocr_extract_text_builds_correct_payload_and_parses_markdown():
    client = MistralClient(api_key="test-key")
    image_bytes = b"fake-png-bytes"

    with patch("httpx.Client") as mock_httpx_client:
        instance = mock_httpx_client.return_value.__enter__.return_value
        instance.post.return_value = _mock_response(
            200, {"pages": [{"index": 0, "markdown": "Prix: 39.9 EUR"}]}
        )

        text = client.ocr_extract_text(image_bytes, content_type="image/png")

    assert text == "Prix: 39.9 EUR"

    call_args = instance.post.call_args
    assert call_args.args[0] == client.ocr_api_url
    payload = call_args.kwargs["json"]
    assert payload["model"] == client.ocr_model
    assert payload["document"]["type"] == "image_url"
    expected_b64 = base64.b64encode(image_bytes).decode("utf-8")
    assert payload["document"]["image_url"] == f"data:image/png;base64,{expected_b64}"


def test_ocr_extract_text_concatenates_multiple_pages():
    client = MistralClient(api_key="test-key")

    with patch("httpx.Client") as mock_httpx_client:
        instance = mock_httpx_client.return_value.__enter__.return_value
        instance.post.return_value = _mock_response(
            200,
            {
                "pages": [
                    {"index": 0, "markdown": "Page 1"},
                    {"index": 1, "markdown": "Page 2"},
                ]
            },
        )
        text = client.ocr_extract_text(b"bytes")

    assert text == "Page 1\nPage 2"


def test_ocr_extract_text_raises_mistral_api_error_on_auth_failure():
    client = MistralClient(api_key="bad-key")

    with patch("httpx.Client") as mock_httpx_client:
        instance = mock_httpx_client.return_value.__enter__.return_value
        instance.post.return_value = _mock_response(401, {})

        with pytest.raises(MistralAPIError):
            client.ocr_extract_text(b"bytes")

    # Pas de retry sur une erreur d'authentification : un seul appel HTTP.
    assert instance.post.call_count == 1


def test_ocr_extract_text_requires_api_key():
    client = MistralClient(api_key="")

    with pytest.raises(MistralAPIError):
        client.ocr_extract_text(b"bytes")
