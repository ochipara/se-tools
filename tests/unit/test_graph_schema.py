from setool.graph.graph import ProgramGraph
from setool.graph.nodes import Node, NodeKind, Location
from setool.graph.edges import Edge, EdgeKind
from setool.graph.provenance import Provenance

def test_program_graph_creation():
    graph = ProgramGraph()
    assert graph.schema_version == "1.0.0"

    node1 = Node(id="pkg", kind=NodeKind.PACKAGE, name="pkg")
    node2 = Node(id="pkg.mod", kind=NodeKind.MODULE, name="mod", location=Location(file="pkg/mod.py", line_start=1, line_end=10))

    graph.nodes[node1.id] = node1
    graph.nodes[node2.id] = node2

    edge = Edge(
        source=node1.id,
        target=node2.id,
        kind=EdgeKind.CONTAINS,
        provenance=[Provenance.SOURCE_AST]
    )
    graph.edges.append(edge)

    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.edges[0].kind == EdgeKind.CONTAINS
