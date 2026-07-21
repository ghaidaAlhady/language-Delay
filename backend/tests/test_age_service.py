from __future__ import annotations

from datetime import date

import pytest

from app.services.age_service import compute_age_years, is_assessment_age_eligible

TODAY = date(2026, 7, 21)


@pytest.mark.parametrize(
    ("date_of_birth", "expected_age"),
    [
        (date(2024, 7, 21), 2),  # exact 2nd birthday today
        (date(2024, 7, 22), 1),  # turns 2 tomorrow
        (date(2023, 7, 20), 3),  # birthday was yesterday
        (date(2021, 7, 21), 5),  # exact 5th birthday today
        (date(2020, 7, 22), 5),  # turns 6 tomorrow
        (date(2020, 7, 21), 6),  # exact 6th birthday today
    ],
)
def test_compute_age_years(date_of_birth: date, expected_age: int) -> None:
    assert compute_age_years(date_of_birth, as_of=TODAY) == expected_age


def test_compute_age_years_rejects_future_dob() -> None:
    with pytest.raises(ValueError, match="future"):
        compute_age_years(date(2027, 1, 1), as_of=TODAY)


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (0, False),
        (1, False),
        (2, True),
        (3, True),
        (4, True),
        (5, True),
        (6, False),
        (12, False),
    ],
)
def test_is_assessment_age_eligible_boundaries(age: int, expected: bool) -> None:
    assert is_assessment_age_eligible(age) is expected
