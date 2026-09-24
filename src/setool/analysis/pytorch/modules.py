from ...graph.graph import ProgramGraph
from ...graph.nodes import NodeKind
from ...graph.edges import Edge, EdgeKind
from ...graph.provenance import Provenance
import ast

class PyTorchVisitor(ast.NodeVisitor):
    def __init__(self, graph: ProgramGraph, module_id: str):
        self.graph = graph
        self.module_id = module_id
        self.current_scope = [module_id]

    def visit_ClassDef(self, node: ast.ClassDef):
        class_id = f"{self.current_scope[-1]}::{node.name}"
        self.current_scope.append(class_id)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        func_id = f"{self.current_scope[-1]}.{node.name}"
        self.current_scope.append(func_id)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_Assign(self, node: ast.Assign):
        # Look for self.submodule = SubModule() in __init__
        if self.current_scope[-1].endswith(".__init__"):
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                class_id = self.current_scope[-1].split(".")[0]
                target_type_name = node.value.func.id

                # Verify if target_type is a known nn.Module in graph
                is_module = False
                for nid, n in self.graph.nodes.items():
                    if n.kind == NodeKind.PYTORCH_MODULE and n.name == target_type_name:
                        is_module = True
                        break

                if is_module:
                    for target in node.targets:
                        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                            self.graph.edges.append(Edge(
                                source=class_id,
                                target=target_type_name,
                                kind=EdgeKind.CONTAINS,
                                provenance=[Provenance.PYTORCH_SEMANTICS]
                            ))
        self.generic_visit(node)

def run_pytorch_analysis(graph: ProgramGraph):
    for node_id, node in list(graph.nodes.items()):
        if node.kind == NodeKind.MODULE and node.location:
            try:
                with open(node.location.file, "r", encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source)
                visitor = PyTorchVisitor(graph, node_id)
                visitor.visit(tree)
            except Exception:
                pass
