import networkx as nx
from typing import List, Dict
from ...graph.graph import ProgramGraph
from ...graph.edges import EdgeKind

def detect_dependency_cycles(graph: ProgramGraph) -> List[List[str]]:
    nx_graph = nx.DiGraph()
    for edge in graph.edges:
        if edge.kind == EdgeKind.DEPENDS_ON:
            nx_graph.add_edge(edge.source, edge.target)

    # Find strongly connected components
    sccs = list(nx.strongly_connected_components(nx_graph))
    cycles = [list(scc) for scc in sccs if len(scc) > 1]
    return cycles
