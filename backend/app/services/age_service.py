"""Age computation shared by child profiles and assessment eligibility.

The knowledge base only covers ages 2-5 inclusive (KB01/KB02/KB03/KB05 each
have exactly one sheet/segment per age in that range). A child's age changes
over time, so it is always computed from date of birth rather than stored.
"""
from __future__ import annotations

from datetime import date

MIN_ASSESSMENT_AGE = 2
MAX_ASSESSMENT_AGE = 5


def compute_age_years(date_of_birth: date, as_of: date | None = None) -> int:
    today = as_of or date.today()
    if date_of_birth > today:
        raise ValueError("Date of birth cannot be in the future.")

    age = today.year - date_of_birth.year
    had_birthday = (today.month, today.day) >= (date_of_birth.month, date_of_birth.day)
    if not had_birthday:
        age -= 1
    return age


def is_assessment_age_eligible(age_years: int) -> bool:
    return MIN_ASSESSMENT_AGE <= age_years <= MAX_ASSESSMENT_AGE
