import os
import tempfile
from setool.graph.graph import ProgramGraph
from setool.discovery.symbols import analyze_file
from setool.analysis.types.analyzer import run_type_analysis
from setool.analysis.pytorch.modules import run_pytorch_analysis
from setool.analysis.dataflow.analyzer import run_dataflow_analysis
from setool.graph.edges import EdgeKind

def test_pytorch_and_dataflow():
    source = """
import torch
from torch import nn

class SubModule(nn.Module):
    pass

class Encoder(nn.Module):
    def __init__(self):
        self.sub = SubModule()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = x
        return y
"""
    with tempfile.TemporaryDirectory() as d:
        filepath = os.path.join(d, "pytorch_data.py")
        with open(filepath, "w") as f:
            f.write(source)

        graph = ProgramGraph()
        analyze_file(filepath, d, graph)
        run_type_analysis(graph)
        run_pytorch_analysis(graph)
        run_dataflow_analysis(graph)

        # Test PyTorch Contains
        pytorch_contains = [e for e in graph.edges if e.kind == EdgeKind.CONTAINS and e.source == "pytorch_data::Encoder" and e.target == "SubModule"]
        assert len(pytorch_contains) == 1

        # Test Data Flow Passes Value
        passes = [e for e in graph.edges if e.kind == EdgeKind.PASSES_VALUE]
        assert len(passes) == 1
        assert passes[0].source == "pytorch_data::Encoder.forward::val_x"
        assert passes[0].target == "pytorch_data::Encoder.forward::val_y"

        # Test Data Flow Returns
        returns = [e for e in graph.edges if e.kind == EdgeKind.RETURNS]
        assert len(returns) == 1
        assert returns[0].source == "pytorch_data::Encoder.forward"
        assert returns[0].target == "pytorch_data::Encoder.forward::val_y"
