# Agent Specification Files

Read the relevant file before implementing or modifying any LangGraph node.

| File | Node | Source Location |
|---|---|---|
| router-agent.md | router_node | app/agents/nodes/router.py |
| rag-agent.md | rag_node | app/agents/nodes/rag.py |
| ocr-agent.md | ocr_node | app/agents/nodes/ocr.py |
| procedure-planner-agent.md | procedure_planner_node | app/agents/nodes/procedure_planner.py |
| form-filler-agent.md | form_filler_node | app/agents/nodes/form_filler.py |
| synthesizer-agent.md | synthesizer_node | app/agents/nodes/synthesizer.py |

## Workflow
1. Read the spec file before writing any code.
2. After implementing, self-review with `.claude/skills/code-review/review-agent-node.md`.
3. If behaviour needs to change, update the spec file first and note why in the commit.
