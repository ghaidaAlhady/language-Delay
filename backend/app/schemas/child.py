"""Request/response schemas for child profiles."""
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class ChildCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    date_of_birth: date
    gender: Gender
    home_language: str = Field(min_length=1, max_length=50)
    has_previous_diagnosis: bool = False
    previous_diagnosis_details: str | None = Field(default=None, max_length=2000)
    has_hearing_problems: bool = False
    uses_hearing_aid: bool = False
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("date_of_birth")
    @classmethod
    def date_of_birth_not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return value


class ChildUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    date_of_birth: date | None = None
    gender: Gender | None = None
    home_language: str | None = Field(default=None, min_length=1, max_length=50)
    has_previous_diagnosis: bool | None = None
    previous_diagnosis_details: str | None = Field(default=None, max_length=2000)
    has_hearing_problems: bool | None = None
    uses_hearing_aid: bool | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("date_of_birth")
    @classmethod
    def date_of_birth_not_in_future(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return value


class ChildResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    date_of_birth: date
    gender: Gender
    home_language: str
    has_previous_diagnosis: bool
    previous_diagnosis_details: str | None
    has_hearing_problems: bool
    uses_hearing_aid: bool
    notes: str | None
    age_years: int
    is_assessment_age_eligible: bool
    created_at: datetime
    updated_at: datetime
