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

def test_call_resolution_in_packages_and_imports():
    metrics_code = """
def evaluate_predictions():
    return 1

def evaluate_classifier_predictions():
    return evaluate_predictions()
"""
    model_code = """
from mypkg.metrics import evaluate_predictions

def train_and_eval():
    return evaluate_predictions()
"""
    rel_model_code = """
from .metrics import evaluate_predictions

def rel_eval():
    return evaluate_predictions()
"""
    attr_model_code = """
from mypkg import metrics

def attr_eval():
    return metrics.evaluate_predictions()
"""
    with tempfile.TemporaryDirectory() as d:
        pkg_dir = os.path.join(d, "src", "mypkg")
        os.makedirs(pkg_dir)
        metrics_file = os.path.join(pkg_dir, "metrics.py")
        model_file = os.path.join(pkg_dir, "model.py")
        rel_model_file = os.path.join(pkg_dir, "rel_model.py")
        attr_model_file = os.path.join(pkg_dir, "attr_model.py")

        with open(metrics_file, "w") as f:
            f.write(metrics_code)
        with open(model_file, "w") as f:
            f.write(model_code)
        with open(rel_model_file, "w") as f:
            f.write(rel_model_code)
        with open(attr_model_file, "w") as f:
            f.write(attr_model_code)

        graph = ProgramGraph()
        analyze_file(metrics_file, d, graph)
        analyze_file(model_file, d, graph)
        analyze_file(rel_model_file, d, graph)
        analyze_file(attr_model_file, d, graph)

        run_type_analysis(graph)
        discover_calls(graph)
        resolve_calls(graph)

        calls_edges = [e for e in graph.edges if e.kind == EdgeKind.CALLS]

        # 1. evaluate_classifier_predictions -> evaluate_predictions (same module in nested package)
        same_mod_edge = next((e for e in calls_edges if e.source == "src.mypkg.metrics.evaluate_classifier_predictions"), None)
        assert same_mod_edge is not None
        assert same_mod_edge.target == "src.mypkg.metrics.evaluate_predictions"
        assert same_mod_edge.properties["status"] == "resolved"

        # 2. train_and_eval -> evaluate_predictions (cross-module imported with src. prefix discrepancy)
        cross_mod_edge = next((e for e in calls_edges if e.source == "src.mypkg.model.train_and_eval"), None)
        assert cross_mod_edge is not None
        assert cross_mod_edge.target == "src.mypkg.metrics.evaluate_predictions"
        assert cross_mod_edge.properties["status"] == "resolved"

        # 3. rel_eval -> evaluate_predictions (relative import from .metrics)
        rel_edge = next((e for e in calls_edges if e.source == "src.mypkg.rel_model.rel_eval"), None)
        assert rel_edge is not None
        assert rel_edge.target == "src.mypkg.metrics.evaluate_predictions"
        assert rel_edge.properties["status"] == "resolved"

        # 4. attr_eval -> evaluate_predictions (module attribute call metrics.evaluate_predictions)
        attr_edge = next((e for e in calls_edges if e.source == "src.mypkg.attr_model.attr_eval"), None)
        assert attr_edge is not None
        assert attr_edge.target == "src.mypkg.metrics.evaluate_predictions"
        assert attr_edge.properties["status"] == "resolved"

