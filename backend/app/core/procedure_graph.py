"""Pure domain logic for procedure dependency graph traversal.

No database queries, no HTTP calls, no FastAPI imports allowed here.
All functions are synchronous and fully testable in isolation.
"""

from collections import deque

from app.schemas.procedure import ProcedureDependency, ProcedureExecutionPlan, ProcedureStep


def build_adjacency_list(dependencies: list[ProcedureDependency]) -> dict[str, list[str]]:
    """Build an adjacency list from a flat list of dependency edges.

    The adjacency list maps each procedure_id to the list of procedure IDs
    it directly depends on (i.e., must be completed first).
    """
    adj: dict[str, list[str]] = {}
    for dep in dependencies:
        adj.setdefault(dep.procedure_id, [])
        adj.setdefault(dep.depends_on_procedure_id, [])
        adj[dep.procedure_id].append(dep.depends_on_procedure_id)
    return adj


def topological_sort(adjacency: dict[str, list[str]]) -> list[str]:
    """Kahn's algorithm. Raises ValueError if a cycle is detected.

    Returns nodes in topological order: prerequisites come before dependents.
    An edge A → B means A depends on B, so B appears before A in the output.
    """
    # Build in-degree count (number of nodes that depend on each node)
    # In our graph, edge A → B means "A depends on B"
    # For Kahn's we need: in-degree = number of *prerequisites* that must come before
    # Re-interpret: treat each edge A→B as "B must come before A"
    # So for Kahn's ordering (prerequisites first), use the reverse graph.

    all_nodes = set(adjacency.keys())
    # in_degree for Kahn: how many dependencies (predecessors in the reversed topo sense)
    # We want nodes with no prerequisites to come first.
    # in_degree[node] = number of nodes that node depends on (i.e., len(adjacency[node]))
    # But Kahn's algorithm works on edges pointing from prerequisite to dependent:
    # We'll build a "dependents" map: prereq → list of nodes that depend on prereq
    dependents: dict[str, list[str]] = {node: [] for node in all_nodes}
    in_degree: dict[str, int] = {node: 0 for node in all_nodes}

    for node, prereqs in adjacency.items():
        for prereq in prereqs:
            dependents[prereq].append(node)
            in_degree[node] += 1

    # Start with nodes that have no prerequisites
    queue: deque[str] = deque(n for n in all_nodes if in_degree[n] == 0)
    result: list[str] = []

    while queue:
        node = queue.popleft()
        result.append(node)
        for dependent in dependents[node]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(result) != len(all_nodes):
        raise ValueError(
            f"Cycle detected in procedure dependency graph. "
            f"Could not sort {len(all_nodes) - len(result)} node(s)."
        )

    return result


def resolve_execution_plan(
    target_procedure_id: str,
    all_dependencies: list[ProcedureDependency],
    completed_ids: set[str],
    procedure_names: dict[str, str],
) -> ProcedureExecutionPlan:
    """Return an ordered execution plan for reaching target_procedure_id.

    Steps already in completed_ids are marked 'completed'.
    Steps whose direct prerequisites are not yet met are marked 'blocked'.
    All other pending steps are marked 'pending'.
    """
    # Collect all nodes reachable from target (including target itself)
    adj = build_adjacency_list(all_dependencies)

    # BFS/DFS to find all ancestors of target_procedure_id
    relevant: set[str] = set()
    stack = [target_procedure_id]
    while stack:
        node = stack.pop()
        if node in relevant:
            continue
        relevant.add(node)
        for prereq in adj.get(node, []):
            if prereq not in relevant:
                stack.append(prereq)

    # Build a sub-adjacency for only relevant nodes
    sub_adj: dict[str, list[str]] = {
        node: [p for p in adj.get(node, []) if p in relevant]
        for node in relevant
    }

    ordered = topological_sort(sub_adj)

    steps: list[ProcedureStep] = []
    for order, proc_id in enumerate(ordered):
        if proc_id in completed_ids:
            status = "completed"
        else:
            # Check whether all direct prerequisites are completed
            direct_prereqs = sub_adj.get(proc_id, [])
            if all(p in completed_ids for p in direct_prereqs):
                status = "pending"
            else:
                status = "blocked"

        steps.append(
            ProcedureStep(
                procedure_id=proc_id,
                procedure_name=procedure_names.get(proc_id, proc_id),
                status=status,
                order=order,
            )
        )

    return ProcedureExecutionPlan(
        target_procedure_id=target_procedure_id,
        steps=steps,
        missing_documents=[],
    )


def find_missing_prerequisites(
    plan: list[str],
    completed: set[str],
    mandatory_only: bool = True,
) -> list[str]:
    """Return procedure IDs in plan that are not in completed.

    Only returns procedures that are direct blockers — i.e., procedures that
    are not completed and appear in the plan before other incomplete procedures.
    """
    return [proc_id for proc_id in plan if proc_id not in completed]
