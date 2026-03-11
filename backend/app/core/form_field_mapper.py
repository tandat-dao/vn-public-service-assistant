"""Semantic form field mapper — uses LLM to map PersonalData fields to PDF field names."""

from app.schemas.personal_data import PersonalData


def map_fields(personal_data: PersonalData, pdf_field_names: list[str]) -> dict[str, str]:
    """
    Map PersonalData fields to PDF form field names using LLM semantic matching.
    Returns a dict of {pdf_field_name: value}. Never hard-codes field name mappings.
    """
    raise NotImplementedError
