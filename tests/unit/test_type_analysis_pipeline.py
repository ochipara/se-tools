import os
import tempfile
from setool.graph.graph import ProgramGraph
from setool.discovery.symbols import analyze_file
from setool.analysis.types.analyzer import run_type_analysis
from setool.analysis.types.models import SourcePosition, TypeResult, SymbolResult, SemanticProvider

def test_semantic_provider_protocol():
    class DummyProvider(SemanticProvider):
        def type_at(self, loc):
            return TypeResult(type_name="str", provenance="dummy")
        def symbol_at(self, loc):
            return SymbolResult(symbol_id="dummy", provenance="dummy")

    p = DummyProvider()
    loc = SourcePosition(filepath="test.py", line=1, column=1)
    assert p.type_at(loc).type_name == "str"
