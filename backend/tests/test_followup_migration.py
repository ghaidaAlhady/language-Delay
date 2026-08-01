from __future__ import annotations

import runpy
from pathlib import Path
from unittest.mock import Mock

import pytest

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "5f31d8aee912_link_followups_to_weekly_plans.py"
)


def _load_migration() -> dict[str, object]:
    return runpy.run_path(str(MIGRATION_PATH))


def _mock_unique_constraints(
    monkeypatch: pytest.MonkeyPatch,
    migration: dict[str, object],
    constraints: list[dict[str, object]],
) -> None:
    inspector = Mock()
    inspector.get_unique_constraints.return_value = constraints
    monkeypatch.setattr(migration["sa"], "inspect", lambda _connection: inspector)
    monkeypatch.setattr(migration["op"], "get_bind", lambda: object())


def test_postgresql_generated_constraint_name_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _load_migration()
    _mock_unique_constraints(
        monkeypatch,
        migration,
        [
            {
                "name": "followups_current_assessment_id_key",
                "column_names": ["current_assessment_id"],
            }
        ],
    )

    assert (
        migration["_current_assessment_unique_constraint_name"]()
        == "followups_current_assessment_id_key"
    )


def test_sqlite_unnamed_constraint_uses_batch_convention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _load_migration()
    _mock_unique_constraints(
        monkeypatch,
        migration,
        [{"name": None, "column_names": ["current_assessment_id"]}],
    )

    assert (
        migration["_current_assessment_unique_constraint_name"]()
        == "uq_followups_current_assessment_id"
    )


def test_missing_constraint_is_not_suppressed(monkeypatch: pytest.MonkeyPatch) -> None:
    migration = _load_migration()
    _mock_unique_constraints(monkeypatch, migration, [])

    with pytest.raises(RuntimeError, match="Expected exactly one unique constraint"):
        migration["_current_assessment_unique_constraint_name"]()
