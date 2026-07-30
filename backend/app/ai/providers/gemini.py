"""Official google-genai adapter for server-side structured generation."""
from __future__ import annotations

import asyncio
from typing import Any

from app.ai.protocols import (
    ProviderError,
    ProviderRequest,
    ProviderTimeoutError,
)
from app.ai.schemas import AssistanceContent
from app.core.logging import get_logger

logger = get_logger(__name__)

# google-genai's response_json_schema field accepts this documented subset.
# Pydantic's string length keywords remain enforced after generation by
# AssistanceContent.model_validate_json(), but they cannot be sent to Gemini.
_SUPPORTED_RESPONSE_JSON_SCHEMA_KEYWORDS = frozenset(
    {
        "$anchor",
        "$defs",
        "$id",
        "$ref",
        "additionalProperties",
        "anyOf",
        "description",
        "enum",
        "format",
        "items",
        "maxItems",
        "maximum",
        "minItems",
        "minimum",
        "oneOf",
        "prefixItems",
        "properties",
        "propertyOrdering",
        "required",
        "title",
        "type",
    }
)
_SAFE_PROVIDER_STATUSES = frozenset(
    {
        "ABORTED",
        "DEADLINE_EXCEEDED",
        "FAILED_PRECONDITION",
        "INTERNAL",
        "INVALID_ARGUMENT",
        "NOT_FOUND",
        "PERMISSION_DENIED",
        "RESOURCE_EXHAUSTED",
        "UNAVAILABLE",
        "UNAUTHENTICATED",
    }
)


def _filter_supported_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return the Gemini-supported subset of a trusted Pydantic JSON schema."""
    filtered: dict[str, Any] = {}
    for keyword, value in schema.items():
        if keyword not in _SUPPORTED_RESPONSE_JSON_SCHEMA_KEYWORDS:
            continue
        if keyword in {"$defs", "properties"}:
            filtered[keyword] = {
                name: _filter_supported_json_schema(subschema)
                for name, subschema in value.items()
            }
        elif keyword in {"anyOf", "oneOf", "prefixItems"}:
            filtered[keyword] = [
                _filter_supported_json_schema(subschema) for subschema in value
            ]
        elif keyword in {"additionalProperties", "items"} and isinstance(
            value, dict
        ):
            filtered[keyword] = _filter_supported_json_schema(value)
        else:
            filtered[keyword] = value
    return filtered


def _build_generate_content_config(types: Any) -> Any:
    """Build an SDK config that uses native JSON Schema, with no tools or AFC."""
    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=_filter_supported_json_schema(
            AssistanceContent.model_json_schema()
        ),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
    )


def _safe_provider_error_metadata(exc: Exception) -> dict[str, int | str]:
    """Classify an SDK error without retaining provider text or request data."""
    metadata: dict[str, int | str] = {
        "provider": "gemini",
        "provider_error_kind": "provider_error",
    }
    code = getattr(exc, "code", None)
    if isinstance(code, int) and 100 <= code <= 599:
        metadata["provider_http_status"] = code

    status = getattr(exc, "status", None)
    if isinstance(status, str) and status in _SAFE_PROVIDER_STATUSES:
        metadata["provider_status"] = status

    raw_message = getattr(exc, "message", None)
    message = raw_message.casefold() if isinstance(raw_message, str) else ""
    if "additional_properties" in message or "additionalproperties" in message:
        metadata["provider_error_kind"] = (
            "invalid_legacy_response_schema_additional_properties"
        )
    elif "response_json_schema" in message or "responsejsonschema" in message:
        metadata["provider_error_kind"] = "invalid_response_json_schema"
    elif "response_schema" in message or "responseschema" in message:
        metadata["provider_error_kind"] = "invalid_legacy_response_schema"
    elif code == 400 or status == "INVALID_ARGUMENT":
        metadata["provider_error_kind"] = "invalid_request"
    return metadata


class GeminiAIProvider:
    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int,
        max_retries: int,
    ) -> None:
        # Imported only when Gemini is explicitly enabled so the default,
        # deterministic application can still start before optional
        # dependencies are installed.
        from google import genai
        from google.genai import types

        self._model = model
        self._timeout_seconds = timeout_seconds
        self._types: Any = types
        self._client: Any = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=timeout_seconds * 1000,
                retry_options=types.HttpRetryOptions(
                    attempts=max_retries + 1
                ),
            ),
        )

    async def generate(self, request: ProviderRequest) -> str:
        try:
            async with asyncio.timeout(self._timeout_seconds):
                response = await self._client.aio.models.generate_content(
                    model=self._model,
                    contents=request.prompt,
                    config=_build_generate_content_config(self._types),
                )
        except TimeoutError as exc:
            raise ProviderTimeoutError from exc
        except Exception as exc:
            logger.warning(
                "gemini_generate_failed",
                **_safe_provider_error_metadata(exc),
            )
            # Do not retain raw SDK error details in the application exception.
            raise ProviderError from None

        if not response.text:
            raise ProviderError
        return response.text

    async def aclose(self) -> None:
        await self._client.aio.aclose()
