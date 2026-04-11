"""Session data accumulator — merges PersonalData objects by field confidence.

The accumulator keeps a single canonical PersonalData that grows more complete
and confident as the user supplies additional identity documents during a session.

Merge rules:
  - If only one side has a value for a field, that value wins unconditionally.
  - If both sides have a value, the higher ``field_confidences`` score wins.
  - On a tie the *existing* (older) value is kept for stability.
  - Neither input object is ever mutated — a new PersonalData is returned.

Zero infrastructure dependencies: this module only imports from app.schemas.
"""

from __future__ import annotations

from app.schemas.personal_data import PersonalData

# Fields that carry document provenance, not extracted personal data.
# These are handled separately from the per-field confidence comparison.
_PROVENANCE_FIELDS: frozenset[str] = frozenset({
    "source_document_type",
    "source_image_path",
    "extraction_confidence",
    "field_confidences",
    "extracted_at",
})


class SessionDataAccumulator:
    """Merges two PersonalData snapshots into one using confidence-based field selection."""

    def merge(
        self,
        existing: PersonalData | None,
        incoming: PersonalData | None,
    ) -> PersonalData | None:
        """Return a new PersonalData merging existing and incoming by field confidence.

        Args:
            existing: Previously accumulated PersonalData (may be None on first OCR).
            incoming: Freshly extracted PersonalData (may be None if OCR produced nothing).

        Returns:
            Merged PersonalData, or None if both inputs are None.
        """
        if existing is None:
            return incoming
        if incoming is None:
            return existing

        # ── Build merged data fields ──────────────────────────────────────────
        merged_data: dict = {}
        merged_confs: dict[str, float] = {}

        data_fields = [
            f for f in PersonalData.model_fields
            if f not in _PROVENANCE_FIELDS
        ]

        for field_name in data_fields:
            e_val = getattr(existing, field_name)
            i_val = getattr(incoming, field_name)
            e_conf = existing.field_confidences.get(field_name, 0.0)
            i_conf = incoming.field_confidences.get(field_name, 0.0)

            if e_val is None and i_val is None:
                merged_data[field_name] = None
            elif e_val is None:
                # Only incoming has a value — take it.
                merged_data[field_name] = i_val
                merged_confs[field_name] = i_conf
            elif i_val is None:
                # Only existing has a value — keep it.
                merged_data[field_name] = e_val
                merged_confs[field_name] = e_conf
            elif i_conf > e_conf:
                # Incoming is more confident — prefer it.
                merged_data[field_name] = i_val
                merged_confs[field_name] = i_conf
            else:
                # Tie or existing is more confident — keep existing for stability.
                merged_data[field_name] = e_val
                merged_confs[field_name] = e_conf

        # ── Merge field_confidences: take the max per key ─────────────────────
        all_conf_keys = set(existing.field_confidences) | set(incoming.field_confidences)
        merged_field_confs: dict[str, float] = {
            k: max(
                existing.field_confidences.get(k, 0.0),
                incoming.field_confidences.get(k, 0.0),
            )
            for k in all_conf_keys
        }
        # Incorporate any newly resolved confidences from this merge pass.
        for k, v in merged_confs.items():
            merged_field_confs[k] = max(merged_field_confs.get(k, 0.0), v)

        # ── Build provenance for the merged object ────────────────────────────
        # Use incoming's source metadata (newest document), but take the max
        # of both extraction_confidence values.
        return PersonalData(
            **merged_data,
            source_document_type=incoming.source_document_type,
            source_image_path=incoming.source_image_path,
            extraction_confidence=max(
                existing.extraction_confidence,
                incoming.extraction_confidence,
            ),
            field_confidences=merged_field_confs,
            extracted_at=incoming.extracted_at,
        )
