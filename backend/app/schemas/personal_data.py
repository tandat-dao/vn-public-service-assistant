"""Pydantic schemas for personal data extracted from identity documents."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Address(BaseModel):
    street: str | None = None
    ward: str | None = None
    district: str | None = None
    province: str | None = None
    country: str = "Việt Nam"


class PersonalData(BaseModel):
    full_name: str | None = None
    full_name_latin: str | None = None
    date_of_birth: date | None = None
    gender: Literal["Nam", "Nữ"] | None = None
    nationality: str = "Việt Nam"
    id_number: str | None = None
    id_issue_date: date | None = None
    id_issue_place: str | None = None
    permanent_address: Address | None = None
    temporary_address: Address | None = None

    # Provenance — never omit these
    source_document_type: str
    source_image_path: str
    extraction_confidence: float
    field_confidences: dict[str, float] = Field(default_factory=dict)
    extracted_at: datetime

    @model_validator(mode="after")
    def _validate_confidence(self) -> "PersonalData":
        if not (0.0 <= self.extraction_confidence <= 1.0):
            raise ValueError("extraction_confidence must be between 0.0 and 1.0")
        return self
