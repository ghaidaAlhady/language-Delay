"""Structured logging configuration.

Sensitive fields (tokens, passwords, free-text health data, chatbot messages,
generated reports) must never be logged. ``REDACTED_KEYS`` is applied to every
event before it is emitted.
"""
from __future__ import annotations

import logging

import structlog

REDACTED_KEYS = {
    "password",
    "hashed_password",
    "access_token",
    "refresh_token",
    "token",
    "authorization",
    "secret_key",
    "llm_api_key",
    "gemini_api_key",
    "prompt",
    "raw_prompt",
    "raw_response",
    "provider_response",
    "ai_context",
    "answer_text",
    "message",
    "report_text",
    "notes",
}


def _redact_sensitive(
    _logger: structlog.types.WrappedLogger,
    _method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    for key in list(event_dict.keys()):
        if key.lower() in REDACTED_KEYS:
            event_dict[key] = "***redacted***"
    return event_dict


def configure_logging(log_level: str) -> None:
    logging.basicConfig(level=log_level, format="%(message)s")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _redact_sensitive,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(log_level)),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.types.FilteringBoundLogger:
    return structlog.get_logger(name)
