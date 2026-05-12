"""SSE pipeline event types for the agentic flow visualization (TASK-SHOWCASE).

Events are emitted over SSE before the final text stream. They allow the
frontend AgentActivityPanel to show real-time agent activity as each node
completes.

SSE format used for these events:
    event: pipeline_event
    data: {"type": "<EVENT_TYPE>", ...fields}

HARD CONSTRAINT: Never include PII or raw PersonalData in any event payload.
Only summaries (field counts, confidence scores, document type) are permitted.
"""

# ---------------------------------------------------------------------------
# Event type string constants
# ---------------------------------------------------------------------------

PIPELINE_START = "pipeline_start"
"""Emitted when router_node begins — signals that the pipeline has started."""

PLAN_DECIDED = "plan_decided"
"""Emitted when router_node ends — contains execution_plan, domain, location_scope."""

ENRICHMENT_RESULT = "enrichment_result"
"""Emitted when enrichment_node ends and a procedure plan was produced."""

PARALLEL_WAVE_START = "parallel_wave_start"
"""Emitted before a wave of concurrent workers fires (wave size >= 2)."""

WORKER_START = "worker_start"
"""Emitted for each individual worker as its wave begins."""

WORKER_COMPLETE = "worker_complete"
"""Emitted for each worker when its wave completes, with duration_ms."""

RAG_RESULT = "rag_result"
"""Emitted after rag_fn completes — chunk count, scope, confidence tier."""

OCR_RESULT = "ocr_result"
"""Emitted after ocr_fn completes — document type, field count, confidence."""

FORM_RESULT = "form_result"
"""Emitted after form_filler_fn completes — filled count, unfilled required fields."""

PIPELINE_COMPLETE = "pipeline_complete"
"""Emitted when synthesizer_node ends — total wall-clock ms, synthesizer mode."""

# ---------------------------------------------------------------------------
# Human-readable worker labels for the frontend panel
# ---------------------------------------------------------------------------

WORKER_LABELS: dict[str, str] = {
    "rag_fn": "RAG",
    "ocr_fn": "OCR",
    "form_filler_fn": "Form filler",
}
