"""Validated student proposals and director decisions."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.coursework.schemas import Grade
from app.modules.submissions.schemas import DocumentIn


class CreditMapping(BaseModel):
    category: Literal["core", "breadth", "electives"]
    area: Literal["theory", "ai_ml", "systems"] | None = None
    equivalent_course_id: int | None = Field(default=None, gt=0)
    credits: int = Field(ge=1, le=19)
    is_research: bool = False
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def check_mapping(self):
        if self.category == "core" and self.equivalent_course_id is None:
            raise ValueError("Choose the equivalent core course.")
        if self.category == "breadth" and self.area is None:
            raise ValueError("Choose a breadth area.")
        if self.category != "breadth" and self.area is not None:
            raise ValueError("A breadth area applies only to Breadth.")
        if self.category != "electives" and self.is_research:
            raise ValueError("Independent study or research belongs in Electives.")
        if self.category == "breadth" and self.credits < 3:
            raise ValueError("A breadth course must provide at least 3 credits.")
        return self


class TransferIn(CreditMapping):
    institution: str = Field(min_length=1, max_length=255)
    course_code: str = Field(min_length=1, max_length=20)
    course_title: str = Field(min_length=1, max_length=255)
    completed_on: date
    grade: Grade
    files: list[DocumentIn] = Field(min_length=1, max_length=5)
    version: int | None = Field(default=None, ge=1)


class ReviewIn(BaseModel):
    version: int = Field(ge=1)
    decision: Literal["approved", "rejected", "more_information_required"]
    comment: str = Field(default="", max_length=4000)
    mapping: CreditMapping | None = None
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def check_decision(self):
        if self.decision == "approved" and self.mapping is None:
            raise ValueError("Confirm the credits and category to approve.")
        if self.decision != "approved" and not self.comment:
            raise ValueError("Explain the rejection or the additional information needed.")
        if self.decision != "approved" and self.mapping is not None:
            raise ValueError("Credits can only be applied with an approval.")
        return self
