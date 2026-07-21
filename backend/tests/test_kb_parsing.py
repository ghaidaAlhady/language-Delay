import pytest

from app.rag.exceptions import KnowledgeBaseLoadError
from app.rag.parsing import parse_id_list, parse_score_threshold


def test_parse_id_list_explicit_comma_list() -> None:
    assert parse_id_list("A001,A002,A003,A005") == ["A001", "A002", "A003", "A005"]


def test_parse_id_list_range_shorthand() -> None:
    assert parse_id_list("A019-A025") == ["A019", "A020", "A021", "A022", "A023", "A024", "A025"]


def test_parse_id_list_mixed_tokens() -> None:
    assert parse_id_list("R001-R002,R010") == ["R001", "R002", "R010"]


def test_parse_id_list_empty_or_none() -> None:
    assert parse_id_list(None) == []
    assert parse_id_list("") == []


def test_parse_id_list_rejects_descending_range() -> None:
    with pytest.raises(KnowledgeBaseLoadError):
        parse_id_list("A010-A001")


def test_parse_id_list_rejects_malformed_token() -> None:
    with pytest.raises(KnowledgeBaseLoadError):
        parse_id_list("not-an-id")


def test_parse_id_list_rejects_mismatched_range_prefix() -> None:
    with pytest.raises(KnowledgeBaseLoadError):
        parse_id_list("A001-R005")


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ("Score ≥ 85%", 85.0),
        ("Score 70–84%", 70.0),
        ("Score 50–69%", 50.0),
        ("Score < 50%", 0.0),
    ],
)
def test_parse_score_threshold(condition: str, expected: float) -> None:
    assert parse_score_threshold(condition) == expected


def test_parse_score_threshold_rejects_unknown_format() -> None:
    with pytest.raises(KnowledgeBaseLoadError):
        parse_score_threshold("not a condition")
