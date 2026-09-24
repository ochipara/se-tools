from typing import List, Set
from .graph import ProgramGraph
from .nodes import NodeKind
from .edges import EdgeKind

def traverse_from_entry_points(graph: ProgramGraph, entry_points: List[str], max_depth: int) -> ProgramGraph:
    reachable_nodes: Set[str] = set()
    reachable_edges = []

    start_nodes = []
    for ep in entry_points:
        matched = False
        ep_parts = ep.split("::")
        if len(ep_parts) == 2:
            mod_path = ep_parts[0]
            if mod_path.endswith(".py"):
                mod_path = mod_path[:-3]
            mod_id = mod_path.replace("/", ".")
            symbol_name = ep_parts[1]
            exact_id = f"{mod_id}.{symbol_name}"
            method_id = f"{mod_id}::{symbol_name}"

            if exact_id in graph.nodes:
                start_nodes.append(exact_id)
                matched = True
            elif method_id in graph.nodes:
                start_nodes.append(method_id)
                matched = True
            else:
                # Suffix and fuzzy match if module path had different prefix
                for nid in graph.nodes:
                    if (nid.endswith(f".{symbol_name}") or nid.endswith(f"::{symbol_name}")):
                        # Check if mod_id is part of nid or vice versa
                        norm_mod = mod_id.lstrip(".")
                        if norm_mod in nid or any(part in nid for part in norm_mod.split(".") if len(part) > 2):
                            start_nodes.append(nid)
                            matched = True
                            break
        else:
            for nid, n in graph.nodes.items():
                if n.name == ep or nid == ep:
                    start_nodes.append(nid)
                    matched = True

        if not matched:
            print(f"Warning: Entry point target '{ep}' not found in graph.")

    queue = [(nid, 0) for nid in start_nodes]
    visited = set()

    valid_edges = {EdgeKind.CALLS, EdgeKind.CONTAINS, EdgeKind.IMPORTS, EdgeKind.DEPENDS_ON, EdgeKind.PASSES_VALUE, EdgeKind.RETURNS}

    while queue:
        current_id, depth = queue.pop(0)
        if current_id in visited or depth > max_depth:
            continue

        visited.add(current_id)
        reachable_nodes.add(current_id)

        for edge in graph.edges:
            if edge.source == current_id and edge.kind in valid_edges:
                reachable_edges.append(edge)
                # Some edges point to external things that might not be formally in graph.nodes if we didn't add them.
                if edge.target in graph.nodes and edge.target not in visited:
                    queue.append((edge.target, depth + 1))

            elif edge.target == current_id and edge.kind in {EdgeKind.CONTAINS, EdgeKind.IMPORTS}:
                reachable_edges.append(edge)
                if edge.source in graph.nodes and edge.source not in visited:
                    queue.append((edge.source, depth + 1))

    sub_graph = ProgramGraph()
    for nid in reachable_nodes:
        if nid in graph.nodes:
            sub_graph.nodes[nid] = graph.nodes[nid]

    sub_graph.edges = list({(e.source, e.target, e.kind): e for e in reachable_edges}.values())

    for e in sub_graph.edges:
        if e.target in graph.nodes and graph.nodes[e.target].kind == NodeKind.DISTRIBUTION:
            sub_graph.nodes[e.target] = graph.nodes[e.target]

    return sub_graph
