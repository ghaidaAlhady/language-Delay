"""Exceptions raised while loading, validating, or querying the knowledge base."""
from __future__ import annotations


class KnowledgeBaseLoadError(Exception):
    """Raised when a KB workbook is missing, malformed, or fails validation.

    This is a startup-time / data-integrity failure and is intentionally not
    an ``AppError`` — it should surface as a hard failure (fail fast) rather
    than be caught and turned into a per-request HTTP response.
    """


class KnowledgeBaseLookupError(Exception):
    """Raised when a query cannot find an expected record (e.g. no decision
    rule matches a score, or a referenced activity/rule ID does not exist).

    This indicates a genuine data-coverage gap. Callers must not fabricate a
    result; they should propagate this as a service-unavailable response.
    """
