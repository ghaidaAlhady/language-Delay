from __future__ import annotations

import json
from typing import Any

import pytest
from google.genai import types

from app.ai.protocols import ProviderRequest
from app.ai.providers.gemini import (
    GeminiAIProvider,
    _build_generate_content_config,
    _safe_provider_error_metadata,
)
from app.ai.schemas import AssistanceContext, AssistanceOperation


def test_generate_config_uses_sdk_compatible_json_schema_and_disables_afc() -> None:
    config = _build_generate_content_config(types)

    assert config.response_mime_type == "application/json"
    assert config.response_schema is None
    assert config.response_json_schema
    assert config.automatic_function_calling
    assert config.automatic_function_calling.disable is True

    serialized_schema = json.dumps(config.response_json_schema)
    assert '"additionalProperties": false' in serialized_schema
    assert "minLength" not in serialized_schema
    assert "maxLength" not in serialized_schema
    assert '"default"' not in serialized_schema


@pytest.mark.asyncio
async def test_provider_request_serializes_through_google_genai_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = GeminiAIProvider(
        api_key="offline-test-key",
        model="gemini-2.5-flash",
        timeout_seconds=2,
        max_retries=0,
    )
    captured: dict[str, Any] = {}

    async def fake_async_request(
        http_method: str,
        path: str,
        request_dict: dict[str, object],
        http_options: object = None,
    ) -> types.HttpResponse:
        captured.update(
            method=http_method,
            path=path,
            request=request_dict,
            http_options=http_options,
        )
        body = {
            "candidates": [
                {
                    "content": {
                        "role": "model",
                        "parts": [{"text": "{}"}],
                    },
                    "finishReason": "STOP",
                }
            ]
        }
        return types.HttpResponse(headers={}, body=json.dumps(body))

    monkeypatch.setattr(
        provider._client.aio.models._api_client,
        "async_request",
        fake_async_request,
    )
    context = AssistanceContext(
        operation=AssistanceOperation.ASSESSMENT_EXPLANATION,
        age_band="2-3",
        immutable_facts={},
        approved_sources=[],
    )
    try:
        result = await provider.generate(
            ProviderRequest(
                operation=context.operation,
                prompt="offline adapter test",
                context=context,
            )
        )
    finally:
        await provider.aclose()

    assert result == "{}"
    assert captured["method"] == "post"
    assert captured["path"] == "models/gemini-2.5-flash:generateContent"
    request = captured["request"]
    assert isinstance(request, dict)
    generation_config = request["generationConfig"]
    assert isinstance(generation_config, dict)
    assert generation_config["responseMimeType"] == "application/json"
    assert "responseJsonSchema" in generation_config
    assert "responseSchema" not in generation_config
    response_json_schema = generation_config["responseJsonSchema"]
    assert isinstance(response_json_schema, dict)
    assert response_json_schema["additionalProperties"] is False
    assert "additional_properties" not in response_json_schema
    action_tips = response_json_schema["properties"]["action_tips"]
    assert action_tips["items"] == {"$ref": "#/$defs/ActionTip"}
    action_tip_schema = response_json_schema["$defs"]["ActionTip"]
    assert action_tip_schema["additionalProperties"] is False
    assert "additional_properties" not in action_tip_schema
    assert "tools" not in request
    assert provider._client._api_client._http_options.api_version == "v1beta"


def test_safe_error_metadata_never_retains_raw_provider_message() -> None:
    private_marker = "parent-private-value"

    class SyntheticProviderError(Exception):
        code = 400
        status = "INVALID_ARGUMENT"
        message = (
            'Unknown name "additional_properties" at '
            f"generation_config.response_schema; {private_marker}"
        )

    metadata = _safe_provider_error_metadata(SyntheticProviderError())

    assert metadata == {
        "provider": "gemini",
        "provider_error_kind": (
            "invalid_legacy_response_schema_additional_properties"
        ),
        "provider_http_status": 400,
        "provider_status": "INVALID_ARGUMENT",
    }
    assert private_marker not in repr(metadata)
