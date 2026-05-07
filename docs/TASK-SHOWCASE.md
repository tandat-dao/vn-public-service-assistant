# TASK-SHOWCASE — End-to-End Agentic Flow Visualization

**Status:** Not started  
**Priority:** High — thesis demo artifact  
**Depends on:** All LangGraph nodes complete (graph.py, all nodes/ files) ✅

---

## Purpose

The system is genuinely multi-step and agentic, but from the UI the user sees only a loading spinner followed by a response — indistinguishable from a single `anthropic.messages.create()` call. This task makes the pipeline visible in real time so a thesis committee can observe:

1. The **router made a decision** (which workers were selected and why)
2. **Parallel execution** occurred (rag_fn + ocr_fn in the same wave)
3. Each worker **found something specific** (RAG chunks, OCR fields, procedure steps)
4. The synthesizer **assembled from multiple sources**

The approach is:
- **Option B** — Collapsible "Agent Activity" timeline panel inside the existing `ChatWidget`, populated in real time as each node completes via SSE events
- **Option D** — Structured multi-source output blocks after the response text: citation cards (already partially exist), OCR extraction summary, procedure plan cards

---

## Files to Read Before Starting

| File | Why |
|---|---|
| `backend/app/agents/graph.py` | Understand `astream_events()` vs `astream()` — this is the event source |
| `backend/app/api/v1/chat.py` | Current SSE endpoint — how events are streamed to frontend |
| `backend/app/agents/state.py` | AgentState fields — what each node writes that you can surface |
| `backend/app/agents/nodes/plan_executor.py` | Wave execution logic — source of parallel_wave events |
| `backend/app/agents/nodes/router.py` | What router writes to state (execution_plan, domain, location_scope) |
| `backend/app/agents/nodes/rag.py` | What RAG writes (retrieved_chunks, citations, scope_used, confidence_tier) |
| `backend/app/agents/nodes/ocr.py` | What OCR writes (personal_data, document_type) |
| `backend/app/agents/nodes/synthesizer.py` | Synthesizer modes — which mode was chosen |
| `frontend/src/components/chat/ChatWidget.tsx` | Existing SSE consumer — where to plug in event handling |
| `frontend/src/lib/api/client.ts` | `streamChat()` generator — where to parse new event types |
| `frontend/src/lib/stores/chatStore.ts` | Zustand store — may need new fields for activity state |

---

## Architecture Decision: `astream_events()` over `astream()`

LangGraph's `graph.astream()` yields state snapshots. `graph.astream_events()` yields granular lifecycle events (node start, node end, LLM token, tool call) with the state delta at each point. **Switch to `astream_events()` in `chat.py`** — this is the only correct source for real-time per-node timing and output.

Key event kinds you will use:
- `on_chain_start` — a node began executing (name in `event["name"]`)
- `on_chain_end` — a node finished (output in `event["data"]["output"]`)
- `on_chain_stream` — streaming output from synthesizer

---

## Backend Changes

### 1. New SSE Event Schema

Define a small set of typed event structures that the backend emits **before the final text stream**. Add these to `backend/app/schemas/` as a new file (e.g. `pipeline_events.py`):

```python
# Event types emitted over SSE (in addition to existing text_delta)
PIPELINE_START       = "pipeline_start"
PLAN_DECIDED         = "plan_decided"        # router output
ENRICHMENT_RESULT    = "enrichment_result"   # procedure plan (if ran)
PARALLEL_WAVE_START  = "parallel_wave_start" # wave of concurrent workers
WORKER_START         = "worker_start"        # individual worker beginning
WORKER_COMPLETE      = "worker_complete"     # individual worker done
RAG_RESULT           = "rag_result"          # chunks count, scope_used, confidence
OCR_RESULT           = "ocr_result"          # document_type, field count, confidence
FORM_RESULT          = "form_result"         # filled_count, unfilled_required
PIPELINE_COMPLETE    = "pipeline_complete"   # total ms, nodes that ran, synthesizer mode
```

Each event is emitted as an SSE line:
```
event: pipeline_event
data: {"type": "plan_decided", "execution_plan": ["rag_fn"], "domain": "housing", "location_scope": "VN-HCM", "procedure_id": "TTHC-001"}

event: pipeline_event
data: {"type": "parallel_wave_start", "workers": ["rag_fn", "ocr_fn"], "wave_index": 0}

event: pipeline_event
data: {"type": "rag_result", "chunk_count": 4, "scope_used": "VN-HCM", "confidence_tier": "high", "top_article": "Điều 20, 68/2020/QH14"}

event: text_delta
data: {"text": "Theo Điều 20 Luật..."}
```

The existing `text_delta` event type is preserved unchanged.

### 2. Modify `chat.py` SSE Generator

In `backend/app/api/v1/chat.py`, replace the current `graph.astream()` loop with `graph.astream_events()`. Translate LangGraph events into the pipeline event schema above before yielding text tokens.

Key mapping:
- `on_chain_start` where `name == "router_node"` → emit `pipeline_start`
- `on_chain_end` where `name == "router_node"` → emit `plan_decided` (read `execution_plan`, `domain`, `location_scope`, `procedure_id` from output)
- `on_chain_end` where `name == "enrichment_node"` and output has `procedure_execution_plan` → emit `enrichment_result`
- `on_chain_start` where `name == "plan_executor_node"` → emit `worker_start` for the current cursor item
- `on_chain_end` where `name == "plan_executor_node"` → emit `worker_complete` with relevant fields from state delta
- `on_chain_end` where `name == "synthesizer_node"` → emit `pipeline_complete`

Parallel wave detection: when two `worker_start` events fire without an intervening `worker_complete`, that is a parallel wave. Alternatively, read `NODE_DEPENDENCIES` from `node_registry.py` in the router — you know statically which steps can be concurrent.

### 3. Hard Constraint — No Blocking

Pipeline events must be emitted asynchronously as they arrive. Do NOT buffer all events and emit at the end. The activity panel must update in real time. Each `yield` in the SSE generator should send the event immediately.

### 4. Hard Constraint — Backward Compatibility

The frontend's existing `text_delta` parsing must continue to work. New event types use `event: pipeline_event` SSE field; existing text uses `event: text_delta`. A frontend that ignores `pipeline_event` lines must still receive a complete response.

---

## Frontend Changes

### 1. Parse Pipeline Events in `client.ts`

In `streamChat()` (or wherever the SSE stream is consumed), add handling for `event: pipeline_event` lines. Parse the JSON payload and call a new callback:

```typescript
onPipelineEvent?: (event: PipelineEvent) => void
```

Define `PipelineEvent` as a discriminated union type in `frontend/src/lib/types/`:
```typescript
type PipelineEvent =
  | { type: "pipeline_start" }
  | { type: "plan_decided"; execution_plan: string[]; domain: string | null; location_scope: string | null; procedure_id: string | null }
  | { type: "parallel_wave_start"; workers: string[]; wave_index: number }
  | { type: "worker_start"; worker: string }
  | { type: "worker_complete"; worker: string; duration_ms: number; summary: string }
  | { type: "rag_result"; chunk_count: number; scope_used: string; confidence_tier: string; top_article: string | null }
  | { type: "ocr_result"; document_type: string; field_count: number; confidence: number }
  | { type: "form_result"; filled_count: number; unfilled_required: string[] }
  | { type: "pipeline_complete"; total_ms: number; synthesizer_mode: string }
```

### 2. New `AgentActivityPanel` Component

Create `frontend/src/components/chat/AgentActivityPanel.tsx`.

**Behavior:**
- Collapsible — collapsed by default, auto-expands when `pipeline_start` arrives, collapses back after `pipeline_complete` (3s delay)
- Shows a vertical timeline of steps, each with a status icon (spinner → checkmark)
- Parallel wave: two items side-by-side with a "parallel" label between them
- Timing: each completed step shows its duration in ms

**Visual structure (collapsed):**
```
▶ Agent ran 3 steps in 1.8s — rag_fn · ocr_fn · form_filler_fn
```

**Visual structure (expanded):**
```
▼ Agent Activity  (3 steps, 1.8s)

  ✓ Router            Routing to: [rag_fn, ocr_fn → form_filler_fn]
                      Domain: housing · Scope: VN-HCM

  ✓ Wave 1 (parallel, 0.9s)
     ├ ✓ RAG         4 chunks · Điều 20, 68/2020/QH14 · scope: VN-HCM · high confidence
     └ ✓ OCR         CCCD detected · 8 fields extracted · confidence 0.94

  ✓ Wave 2
     └ ✓ Form filler  7/9 fields filled · 2 required fields missing

  ✓ Synthesizer       Mode: form_fill_partial
```

**Placement:** Directly above the assistant message bubble it corresponds to. Tied to that specific message, not a global panel.

### 3. Extend `chatStore.ts`

Add `activityEvents: PipelineEvent[]` to the message type (or a parallel `activityByMessageId: Record<string, PipelineEvent[]>` map). The panel reads from this as events arrive.

### 4. Multi-Source Output Blocks (Option D)

After the response text, render structured data blocks for the sources that were used. These are always visible (not collapsible) and serve as evidence of multi-source assembly:

- **If RAG ran:** Citation chips already exist — no change needed
- **If OCR ran:** An "Extracted from document" card showing the `PersonalData` fields that were extracted (name, DOB, ID number — mask sensitive fields) with their confidence scores
- **If enrichment ran:** A "Procedure checklist" card showing the `procedure_execution_plan` steps with PENDING/COMPLETED status
- **If form fill ran:** A "Form filled" notice showing field count and a link to download the PDF

These blocks are derived from the `pipeline_complete` event payload (which should include a `used_sources` summary field).

---

## Definition of Done

- [ ] `graph.astream_events()` used in `chat.py` — NOT `astream()`
- [ ] Pipeline events emitted over SSE before and during text stream, not after
- [ ] `plan_decided` event emitted with correct `execution_plan`, `domain`, `location_scope`, `procedure_id` on every request
- [ ] `parallel_wave_start` event emitted when `plan_executor` runs multiple workers concurrently (e.g. rag_fn + ocr_fn)
- [ ] `worker_complete` events include duration_ms (wall clock from worker_start to worker_complete)
- [ ] `AgentActivityPanel` shows correct step order with parallel wave rendered side-by-side
- [ ] Panel auto-expands on new message, collapses after completion
- [ ] Existing `text_delta` streaming is unaffected — a browser with no pipeline_event handling still receives the full response
- [ ] At least one multi-source output block rendered (citation chips existing + one new block)
- [ ] End-to-end test: send "hướng dẫn tôi đăng ký thường trú và upload CCCD" — panel should show router → parallel wave (rag_fn + ocr_fn) → form_filler_fn → synthesizer, all with correct data
- [ ] No new TypeScript errors. Existing 366 unit tests still pass.
- [ ] `docs/PROJECT_STATUS.md` updated with a new version entry describing what was implemented: new SSE event types, `AgentActivityPanel` component, multi-source output blocks, and any new files created. Follow the existing changelog format (version number, date, bullet-point summary of changes, test count).

---

## Hard Constraints

- Do NOT switch from SSE to WebSocket. The existing SSE infrastructure is correct for this pattern.
- Do NOT emit raw `AgentState` to the frontend. Only emit the specific fields listed in the event schema. PII (full PersonalData) must never appear in SSE events — only summaries (field count, confidence, document type).
- Do NOT add a second SSE endpoint. Pipeline events and text_delta must share the same SSE connection — the frontend opens one connection per message.
- Do NOT block the text stream waiting for all pipeline events. Text tokens from the synthesizer must stream as they arrive, interleaved with pipeline events if necessary.
- The `AgentActivityPanel` must be tied to its message, not a global sidebar. If the user sends multiple messages, each has its own activity record.

---

## Notes

- LangGraph event names: in `astream_events()`, the `event["name"]` field uses the name the node was registered with in `graph.py`. Verify the exact names there before writing event handlers.
- Timing: record `time.monotonic()` at `worker_start` and compute delta at `worker_complete`. Pass `duration_ms` in the event payload.
- For the thesis demo: keep the panel auto-expanded during the live demo. The collapsing behavior is for production; for the demo, hardcode `defaultOpen=true` via an env/config flag.
