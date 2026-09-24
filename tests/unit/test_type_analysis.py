import os
import tempfile
from setool.graph.graph import ProgramGraph
from setool.discovery.symbols import analyze_file
from setool.analysis.types.analyzer import run_type_analysis
from setool.graph.nodes import NodeKind

def test_bounded_type_propagation():
    source = """
class Foo:
    pass

def helper() -> int:
    return 1

def my_func(a: Foo) -> str:
    b = a
    c = Foo()
    d = helper()
    return "hello"
"""
    with tempfile.TemporaryDirectory() as d:
        filepath = os.path.join(d, "test_mod.py")
        with open(filepath, "w") as f:
            f.write(source)

        graph = ProgramGraph()
        analyze_file(filepath, d, graph)
        run_type_analysis(graph)

        # Check function return type
        func_node = graph.nodes["test_mod.my_func"]
        assert func_node.python_type is not None
        assert func_node.python_type.name == "str"
        assert func_node.python_type.provenance == "return_annotation"

        # Check local types
        mod_node = graph.nodes["test_mod"]
        local_types = mod_node.properties["local_types"]["test_mod.my_func"]
        assert local_types["a"] == "Foo"
        assert local_types["b"] == "Foo" # Assignment propagation
        assert local_types["c"] == "Foo" # Constructor propagation
        assert local_types["d"] == "int" # Function return propagation

def test_pytorch_semantics():
    source = """
import torch
from torch import nn

class Encoder(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x

def train(model: Encoder, x: torch.Tensor):
    logits = model(x)
"""
    with tempfile.TemporaryDirectory() as d:
        filepath = os.path.join(d, "pytorch_mod.py")
        with open(filepath, "w") as f:
            f.write(source)

        graph = ProgramGraph()
        analyze_file(filepath, d, graph)
        run_type_analysis(graph)

        # Check PyTorch Module tagging
        encoder_node = graph.nodes["pytorch_mod::Encoder"]
        assert encoder_node.kind == NodeKind.PYTORCH_MODULE

        # Check PyTorch Semantics propagation on `model(x)`
        mod_node = graph.nodes["pytorch_mod"]
        local_types = mod_node.properties["local_types"]["pytorch_mod.train"]
        assert local_types["model"] == "Encoder"
        assert local_types["logits"] == "torch.Tensor"

def test_unions_and_generics():
    source = """
from typing import Union, List

def process(items: List[str]) -> Union[int, None]:
    pass

def process_new(item: str | int) -> None:
    pass
"""
    with tempfile.TemporaryDirectory() as d:
        filepath = os.path.join(d, "union_mod.py")
        with open(filepath, "w") as f:
            f.write(source)

        graph = ProgramGraph()
        analyze_file(filepath, d, graph)
        run_type_analysis(graph)

        # Check generics
        func_node = graph.nodes["union_mod.process"]
        ret_type = func_node.python_type
        assert ret_type.name == "Union"
        assert ret_type.kind == "Union"
        assert len(ret_type.union_members) == 2
        assert ret_type.union_members[0].name == "int"
        assert ret_type.union_members[1].name == "None"

        val_id = "union_mod.process::param_items"
        param_type = graph.nodes[val_id].python_type
        assert param_type.name == "List"
        assert len(param_type.generic_arguments) == 1
        assert param_type.generic_arguments[0].name == "str"

        # Check 3.10 syntax
        func_node2 = graph.nodes["union_mod.process_new"]
        val_id2 = "union_mod.process_new::param_item"
        param_type2 = graph.nodes[val_id2].python_type
        assert param_type2.name == "Union"
        assert param_type2.kind == "Union"
        assert len(param_type2.union_members) == 2
        assert param_type2.union_members[0].name == "str"
        assert param_type2.union_members[1].name == "int"

def test_attribute_and_method_lookups():
    source = """
class Data:
    def __init__(self):
        self.value: int = 10

    def get_val(self) -> int:
        return self.value

def do_work():
    d = Data()
    x = d.value
    y = d.get_val()
"""
    with tempfile.TemporaryDirectory() as d:
        filepath = os.path.join(d, "attr_mod.py")
        with open(filepath, "w") as f:
            f.write(source)

        graph = ProgramGraph()
        analyze_file(filepath, d, graph)
        run_type_analysis(graph)

        mod_node = graph.nodes["attr_mod"]

        # Check method self typing
        method_types = mod_node.properties["local_types"]["attr_mod::Data.get_val"]
        assert method_types["self"] == "Data"

        init_types = mod_node.properties["local_types"]["attr_mod::Data.__init__"]
        assert init_types["self.value"] == "int"

        local_types = mod_node.properties["local_types"]["attr_mod.do_work"]
        assert local_types["d"] == "Data"
        assert local_types["y"] == "int" # Method return propagation
