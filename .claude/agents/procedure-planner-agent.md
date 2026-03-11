# Procedure Planner Agent — Behavioural Specification

## Node: `procedure_planner_node`
## File: `app/agents/nodes/procedure_planner.py`

## Responsibility
Resolve the full dependency chain for a target procedure and produce an ordered execution plan.
Only this node queries the procedures database and calls `procedure_graph` core logic.

## Inputs (read from AgentState)
- `target_procedure_id: str | None` — if None, resolve from `entities`
- `completed_procedures: list[str]` — loaded from Redis at graph entry
- `entities: dict` — may contain procedure name strings to resolve to IDs

## Outputs (partial AgentState dict)
- `procedure_execution_plan: ProcedureExecutionPlan`
- `target_procedure_id: str` — confirmed/resolved ID

## Resolution Logic (in order)
1. If `target_procedure_id` is None, fuzzy-match `entities` against procedure names in DB.
   If no match, append error and return empty plan.
2. Load ALL dependency edges for the subgraph rooted at target from DB in a single JOIN query.
3. Call `procedure_graph.resolve_execution_plan()` — the algorithm lives in core, not here.
4. Mark steps in `completed_procedures` as `"completed"`.
5. Mark steps whose direct prerequisites are not completed as `"blocked"`.
6. Return the full plan including completed steps — do not filter them out.

## Critical Constraints
- The topological sort algorithm MUST live in `app/core/procedure_graph.py` — not in this node
- This node's only job is: fetch data → pass to core → return result
- If a cycle is detected (ValueError), return a single-step plan with the target, status "blocked"
- Conditional dependencies (`is_mandatory = False`) are included but flagged separately
- Do NOT N+1 query — load the entire subgraph in one query

## Error Handling
On DB failure: append to `state["errors"]`, return empty plan. Do not crash.
