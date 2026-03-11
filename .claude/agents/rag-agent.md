# RAG Agent — Behavioural Specification

## Node: `rag_node`
## File: `app/agents/nodes/rag.py`
## Prompt: `app/agents/prompts/rag_prompt.py`

## Responsibility
Retrieve legal document chunks from Qdrant and generate a cited answer.
Only this node calls `qdrant_service`.

## Inputs (read from AgentState)
- `user_message: str`
- `target_procedure_id: str | None` — used as a Qdrant payload filter
- `entities: dict` — may contain decree numbers for targeted BM25 queries

## Outputs (partial AgentState dict)
- `retrieved_chunks: list[DocumentChunk]`
- `citations: list[Citation]` — structured, ready for the synthesizer

## Retrieval Rules
1. Always use hybrid search (dense + BM25 + RRF). Dense-only is forbidden.
2. Pass `target_procedure_id` as a filter when set — this constrains results to relevant legal docs.
3. Minimum `top_k = 8`. Never fewer.
4. If zero chunks returned: set `citations = []`, append warning to `state["errors"]`, return without calling LLM.

## Citation Rules
- Every `Citation` object must have: `doc_id`, `document_number`, `article`, `excerpt`
- `excerpt` is verbatim text from the retrieved chunk, max 200 characters
- Only citations appearing in `retrieved_chunks` may be included — no invented references
- Citation format in response text: `[Điều X, Nghị định/Thông tư YYY/YYYY/NĐ-CP]`

## Confidence Scoring
Set `state["response_metadata"]["rag_confidence"]`:
- `"high"` — top chunk score > 0.85 AND at least 3 chunks retrieved
- `"medium"` — top chunk score > 0.65
- `"low"` — top chunk score ≤ 0.65 OR fewer than 3 chunks

## Error Handling
On Qdrant failure: append to `state["errors"]`, set empty retrieved_chunks and citations, return.
Do not crash the graph.
