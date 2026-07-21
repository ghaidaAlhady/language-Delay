"""Shared "which domain needs attention most" ranking.

Used by scoring (all domains, worst-first), report generation, and
follow-up (both pick the single worst domain as the focus for a goal).
"""
from __future__ import annotations

from collections.abc import Iterable

from app.rag.schemas import SEVERITY_ORDER, Domain, Severity


def rank_domains_by_priority(
    rows: Iterable[tuple[Domain, Severity, float]],
) -> list[Domain]:
    """Worst severity first; ties broken by lower score first."""
    return [
        domain
        for domain, _severity, _score in sorted(
            rows, key=lambda row: (-SEVERITY_ORDER.index(row[1]), row[2])
        )
    ]


def pick_priority_domain(rows: Iterable[tuple[Domain, Severity, float]]) -> Domain:
    return rank_domains_by_priority(rows)[0]
