# Skill: Review Agent Node

You are reviewing a LangGraph agent node for the DichVuCong project.
Apply every check below in order. Report each as PASS, WARN, or FAIL.

## Checks

### State Contract
- FAIL if the function signature is not `def <name>_node(state: AgentState) -> dict`
- FAIL if the node returns the full AgentState instead of a partial dict
- FAIL if the node mutates `state` in place before returning
- WARN if the node modifies more than 4 state keys — consider splitting

### Infrastructure Isolation
- FAIL if the node imports from `app.core` AND directly calls a service in the same function body
- FAIL if the node instantiates any client (Anthropic, Qdrant, Redis) directly
- WARN if the node body exceeds 60 lines

### Error Handling
- FAIL if the node makes any external call with no try/except
- FAIL if exceptions are silently swallowed (bare `except: pass`)
- WARN if errors are not appended to `state["errors"]` before returning

### Routing Functions
- FAIL if a conditional routing function has any side effects
- FAIL if routing logic is a lambda instead of a named function
- FAIL if a routing function does anything except inspect state and return a node name string

### Prompts
- FAIL if the LLM prompt is a string literal defined inline inside the node
- WARN if the prompt does not instruct the model to return null for missing fields

## Output Format
`[PASS|WARN|FAIL] <check>: <one line reason>`
End with: PASS count / WARN count / FAIL count + one recommended action.
