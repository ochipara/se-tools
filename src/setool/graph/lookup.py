from typing import Optional
from .graph import ProgramGraph
from .nodes import NodeKind

def get_enclosing_module_id(graph: ProgramGraph, scope_id: str) -> Optional[str]:
    """Finds the ID of the enclosing module for a given scope ID."""
    if scope_id in graph.nodes and graph.nodes[scope_id].kind == NodeKind.MODULE:
        return scope_id
    base = scope_id.split("::")[0]
    parts = base.split(".")
    for i in range(len(parts), 0, -1):
        cand = ".".join(parts[:i])
        if cand in graph.nodes and graph.nodes[cand].kind == NodeKind.MODULE:
            return cand
    return base if base in graph.nodes else None

def find_matching_module(graph: ProgramGraph, module_name: str) -> Optional[str]:
    """Finds a matching internal module ID in graph.nodes.
    Matches exact ID, or suffix match (e.g. 'ieeg_pickme.training.metrics' matches 'src.ieeg_pickme.training.metrics').
    """
    if module_name in graph.nodes and graph.nodes[module_name].kind == NodeKind.MODULE:
        return module_name
    suffix = "." + module_name
    for nid, node in graph.nodes.items():
        if node.kind == NodeKind.MODULE and (nid.endswith(suffix) or nid == module_name):
            return nid
    return None

def find_matching_symbol(graph: ProgramGraph, symbol_id: str) -> Optional[str]:
    """Finds a matching symbol node in graph.nodes.
    Matches exact ID, or suffix match if symbol_id contains dots or class separators.
    """
    if symbol_id in graph.nodes:
        return symbol_id
    if "." in symbol_id or "::" in symbol_id:
        suffix = "." + symbol_id
        for nid in graph.nodes:
            if nid.endswith(suffix):
                return nid
    return None
