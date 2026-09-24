import os
import tempfile
from setool.graph.graph import ProgramGraph
from setool.graph.nodes import Node, NodeKind
from setool.graph.edges import Edge, EdgeKind
from setool.analysis.dependencies.internal import aggregate_internal_dependencies
from setool.analysis.dependencies.cycles import detect_dependency_cycles
from setool.analysis.dependencies.external import extract_external_dependencies
from setool.discovery.symbols import analyze_file

def test_internal_dependencies_and_cycles():
    graph = ProgramGraph()
    # Mock packages and modules
    graph.nodes["pkg_a"] = Node(id="pkg_a", kind=NodeKind.PACKAGE, name="pkg_a")
    graph.nodes["pkg_b"] = Node(id="pkg_b", kind=NodeKind.PACKAGE, name="pkg_b")
    graph.nodes["pkg_a.mod1"] = Node(id="pkg_a.mod1", kind=NodeKind.MODULE, name="mod1")
    graph.nodes["pkg_b.mod2"] = Node(id="pkg_b.mod2", kind=NodeKind.MODULE, name="mod2")

    # Contains edges
    graph.edges.append(Edge(source="pkg_a", target="pkg_a.mod1", kind=EdgeKind.CONTAINS))
    graph.edges.append(Edge(source="pkg_b", target="pkg_b.mod2", kind=EdgeKind.CONTAINS))

    # Imports
    graph.edges.append(Edge(source="pkg_a.mod1", target="pkg_b.mod2", kind=EdgeKind.IMPORTS))
    graph.edges.append(Edge(source="pkg_b.mod2", target="pkg_a.mod1", kind=EdgeKind.IMPORTS))

    aggregate_internal_dependencies(graph)

    depends_edges = [e for e in graph.edges if e.kind == EdgeKind.DEPENDS_ON]
    assert len(depends_edges) == 2
    assert any(e.source == "pkg_a" and e.target == "pkg_b" for e in depends_edges)
    assert any(e.source == "pkg_b" and e.target == "pkg_a" for e in depends_edges)

    cycles = detect_dependency_cycles(graph)
    assert len(cycles) == 1
    assert set(cycles[0]) == {"pkg_a", "pkg_b"}

def test_external_dependencies():
    source = "import requests"
    with tempfile.TemporaryDirectory() as d:
        filepath = os.path.join(d, "main.py")
        with open(filepath, "w") as f:
            f.write(source)

        toml_path = os.path.join(d, "pyproject.toml")
        with open(toml_path, "w") as f:
            f.write('[project]\ndependencies = ["requests>=2.0", "pydantic"]\n')

        graph = ProgramGraph()
        analyze_file(filepath, d, graph)
        extract_external_dependencies(graph, d)

        req_node = graph.nodes["dist::requests"]
        assert req_node.kind == NodeKind.DISTRIBUTION
        assert req_node.properties["declared"] is True
        assert req_node.properties["observed"] is True

        pyd_node = graph.nodes["dist::pydantic"]
        assert pyd_node.kind == NodeKind.DISTRIBUTION
        assert pyd_node.properties["declared"] is True
        assert pyd_node.properties.get("observed") is None
