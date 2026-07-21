"""Pure parsing helpers for values embedded as text in the knowledge base."""
from __future__ import annotations

import re

from app.rag.exceptions import KnowledgeBaseLoadError

_ID_TOKEN = re.compile(r"^([A-Za-z]+)(\d+)$")

_SCORE_GE = re.compile(r"Score\s*≥\s*(\d+(?:\.\d+)?)\s*%")
_SCORE_RANGE = re.compile(r"Score\s*(\d+(?:\.\d+)?)\s*[–‒-]\s*(\d+(?:\.\d+)?)\s*%")
_SCORE_LT = re.compile(r"Score\s*<\s*(\d+(?:\.\d+)?)\s*%")


def parse_id_list(raw: str | None) -> list[str]:
    """Expand a KB reference string into an explicit list of IDs.

    Supports both formats found in KB03/KB05: an explicit comma-separated
    list (``"A001,A002,A005"``) and an inclusive shorthand range
    (``"A019-A025"``). Mixed input (e.g. a comma list containing one range
    token) is also supported since each token is parsed independently.
    """
    if not raw:
        return []

    ids: list[str] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            start_raw, _, end_raw = token.partition("-")
            start_match = _ID_TOKEN.match(start_raw.strip())
            end_match = _ID_TOKEN.match(end_raw.strip())
            if not start_match or not end_match or start_match.group(1) != end_match.group(1):
                raise KnowledgeBaseLoadError(f"Unrecognized ID range token: {token!r}")
            prefix = start_match.group(1)
            width = len(start_match.group(2))
            start_num = int(start_match.group(2))
            end_num = int(end_match.group(2))
            if end_num < start_num:
                raise KnowledgeBaseLoadError(f"ID range is descending: {token!r}")
            ids.extend(f"{prefix}{n:0{width}d}" for n in range(start_num, end_num + 1))
        else:
            if not _ID_TOKEN.match(token):
                raise KnowledgeBaseLoadError(f"Unrecognized ID token: {token!r}")
            ids.append(token)
    return ids


def parse_score_threshold(condition: str) -> float:
    """Parse a KB03 ``شرط التقييم`` string into its lower score bound.

    ``"Score ≥ 85%"`` -> 85.0, ``"Score 70–84%"`` -> 70.0, ``"Score < 50%"``
    -> 0.0. The upper bound of each band is intentionally *not* derived from
    this string in isolation: the repository builds it from the next-lowest
    threshold within the same (age, domain) group of four rules, so the four
    bands always partition ``[0, 100]`` with no gap or overlap regardless of
    the exact wording used in the workbook.
    """
    condition = condition.strip()

    if match := _SCORE_GE.fullmatch(condition):
        return float(match.group(1))

    if match := _SCORE_RANGE.fullmatch(condition):
        return float(match.group(1))

    if match := _SCORE_LT.fullmatch(condition):
        return 0.0

    raise KnowledgeBaseLoadError(f"Unrecognized score condition: {condition!r}")
