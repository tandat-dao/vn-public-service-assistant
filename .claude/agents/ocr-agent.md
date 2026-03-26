# OCR Agent — Behavioural Specification

## Worker function: `ocr_fn`
## File: `app/agents/nodes/ocr.py`
## Prompts: `app/agents/prompts/ocr_extraction_prompt.py`, `app/agents/prompts/document_classifier_prompt.py`

---

## Responsibility

Extract personal data from an uploaded identity document image and return a populated
`PersonalData` object. Uses a QR decode fast path for CCCD documents; falls back to full
OCR + LLM extraction for all other document types and failed QR reads.

`ocr_fn` is a **plain async function**, not a LangGraph graph node. It is called by
`plan_executor` via `NODE_REGISTRY["ocr_fn"]`. Never import from `graph.py`.

---

## Inputs (read from AgentState)

- `uploaded_image_path: str | None` — path to the uploaded image on disk (not MinIO path)
- If `uploaded_image_path` is `None`, return `{"personal_data": None, "document_type": None}` immediately

---

## Outputs (partial AgentState dict)

```python
{"personal_data": PersonalData | None, "document_type": str | None}
```

---

## Two-Path Pipeline

### Path A — QR Decode (primary for CCCD, attempted on every upload)

1. Call `OCRService.decode_qr(image_path)`
2. If `PersonalData` is returned → skip all OCR and LLM steps entirely → return immediately
3. If `None` → fall through to Path B

QR decode is ~200ms, zero-token cost. Always attempt first.

### Path B — OCR + LLM Extraction (CCCD fallback + all non-CCCD)

1. Call `OCRService.classify_document_type(image_path)` → vision LLM → `document_type` string
2. Call `OCRService.extract(image_path, document_type)` which internally:
   a. Pre-process image (CLAHE → deskew → denoise) in `run_in_executor`
   b. Run PaddleOCR in `run_in_executor` (NEVER in async context directly)
   c. `_filter_ocr_results()` — drop low confidence, short text, deduplicate IoU > 0.5
   d. Truncate joined OCR text to 8,000 token cap (len // 4 estimate); log WARNING if truncated
   e. Call `LLMService.async_invoke()` with extraction prompt → JSON → PersonalData
3. Return `{"personal_data": personal_data, "document_type": document_type}`

---

## Orchestration Code (exact)

```python
async def ocr_fn(state: AgentState) -> dict:
    image_path = state.get("uploaded_image_path")
    if not image_path:
        return {"personal_data": None, "document_type": None}

    # QR path — attempt first for all uploads
    personal_data = await ocr_service.decode_qr(image_path)
    if personal_data is not None:
        return {"personal_data": personal_data, "document_type": "cccd"}

    # OCR path — QR failed or non-CCCD document
    document_type = await ocr_service.classify_document_type(image_path)
    personal_data = await ocr_service.extract(image_path, document_type)
    return {"personal_data": personal_data, "document_type": document_type}
```

---

## LLM Calls — Two Separate Calls, Two Separate Prompts

| Call | Function | Prompt file | Input | Output |
|---|---|---|---|---|
| 1 | `classify_document_type()` | `document_classifier_prompt.py` | base64 image | one of 5 type strings |
| 2 | `extract()` | `ocr_extraction_prompt.py` | filtered OCR text + doc type | PersonalData JSON |

**Never merge these calls.** They use different model capabilities (vision vs text) and must
remain independently observable in LangSmith traces.

---

## QR Decode Format

CCCD QR code: pipe-delimited, exactly 7+ elements:

```
id_number||full_name|date_of_birth|gender|permanent_address|issue_date
index: 0   1  2        3              4      5                  6
```

- Index 1 is **always empty** — never map to any field
- Dates are `DDMMYYYY` format → parse to `date(YYYY, MM, DD)`
- Province code = `int(id_number[:3])` must be in range 1–96 (settings.CCCD_PROVINCE_CODE_MAX)
- All populated fields receive `field_confidences[field] = 1.0`
- `extraction_confidence = 1.0`

---

## Confidence Contract

| Path | `extraction_confidence` | `field_confidences` |
|---|---|---|
| QR decode | 1.0 | 1.0 for every populated field |
| OCR + LLM | mean PaddleOCR confidence of filtered detections | mean confidence for every non-null field |

QR-decoded values **always win** in `SessionDataAccumulator.merge()` regardless of OCR confidence.

---

## Failure Handling

| Failure | Behaviour |
|---|---|
| `uploaded_image_path` is None | Return `{"personal_data": None, "document_type": None}` |
| QR all 5 attempts fail | Fall through to OCR path silently |
| `classify_document_type()` returns unexpected value | Log warning, use `"other"` |
| LLM JSON parse fails in `extract()` | Log warning, return empty PersonalData (all fields None, confidence=0.0) |
| Image file unreadable | Return `{"personal_data": None, "document_type": None}` |

Never raise exceptions from `ocr_fn`. Always return a dict.

---

## PaddleOCR Threading Rule

PaddleOCR is **synchronous**. Calling `paddleocr_engine.ocr()` directly in an async function
blocks the event loop for 3–8 seconds on CPU mode.

```python
# CORRECT
raw = await asyncio.get_event_loop().run_in_executor(None, self._run_paddle_ocr, path)

# WRONG — blocks event loop
raw = self._get_paddle_engine().ocr(path, cls=True)
```

---

## Document Type Valid Values

```python
VALID_DOCUMENT_TYPES = frozenset({
    "cccd", "birth_certificate", "land_certificate", "household_book", "other"
})
```

---

## State Keys This Worker Reads/Writes

| Key | Read/Write | Notes |
|---|---|---|
| `uploaded_image_path` | Read | Must exist; if None → return empty dict |
| `personal_data` | Write | `PersonalData \| None` |
| `document_type` | Write | One of the 5 valid type strings, or None |
