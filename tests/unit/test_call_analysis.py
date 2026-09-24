import os
import tempfile
from setool.graph.graph import ProgramGraph
from setool.discovery.symbols import analyze_file
from setool.analysis.types.analyzer import run_type_analysis
from setool.analysis.calls.discovery import discover_calls
from setool.analysis.calls.resolver import resolve_calls
from setool.graph.nodes import NodeKind
from setool.graph.edges import EdgeKind

def test_call_discovery_and_resolution():
    source = """
class A:
    def process(self):
        pass

class B:
    def process(self):
        pass

def do_work(a: A):
    a.process()

def do_ambiguous(obj):
    obj.process()

def standalone():
    do_work(None)
"""
    with tempfile.TemporaryDirectory() as d:
        filepath = os.path.join(d, "test_calls.py")
        with open(filepath, "w") as f:
            f.write(source)

        graph = ProgramGraph()
        analyze_file(filepath, d, graph)
        run_type_analysis(graph) # Establish local types
        discover_calls(graph)
        resolve_calls(graph)

        # Check call sites
        call_sites = [n for n in graph.nodes.values() if n.kind == NodeKind.CALL_SITE]
        assert len(call_sites) == 3

        # Check CALLS edges
        calls_edges = [e for e in graph.edges if e.kind == EdgeKind.CALLS]

        # 1. do_work -> A.process (Resolved via type info)
        resolved_edge = next(e for e in calls_edges if e.source == "test_calls.do_work" and e.target == "test_calls::A.process")
        assert resolved_edge.properties["status"] == "resolved"

        # 2. standalone -> do_work (Direct function call)
        direct_edge = next(e for e in calls_edges if e.source == "test_calls.standalone" and e.target == "test_calls.do_work")
        assert direct_edge.properties["status"] == "resolved"

        # 3. do_ambiguous -> A.process OR B.process (Ambiguous)
        ambig_edges = [e for e in calls_edges if e.source == "test_calls.do_ambiguous"]
        assert len(ambig_edges) == 2
        assert any(e.target == "test_calls::A.process" for e in ambig_edges)
        assert any(e.target == "test_calls::B.process" for e in ambig_edges)
        assert ambig_edges[0].properties["status"] == "possible"
