"""Session data accumulator — merges PersonalData objects by field confidence."""

from app.schemas.personal_data import PersonalData


def merge(existing: PersonalData, incoming: PersonalData) -> PersonalData:
    """
    Merge two PersonalData objects. For each field, keep the value with the higher
    confidence score. Never overwrite a higher-confidence value with a lower-confidence one.
    """
    raise NotImplementedError
