import ast
from typing import List
from ...graph.graph import ProgramGraph
from ...graph.nodes import Node, NodeKind, Location
from ...graph.edges import Edge, EdgeKind
from ...graph.provenance import Provenance
from ...graph.types import PythonType

class DataFlowVisitor(ast.NodeVisitor):
    def __init__(self, graph: ProgramGraph, module_id: str):
        self.graph = graph
        self.module_id = module_id
        self.current_scope = [module_id]

    def _ensure_value_node(self, val_name: str, scope_id: str):
        val_id = f"{scope_id}::val_{val_name}"
        if val_id not in self.graph.nodes:
            self.graph.nodes[val_id] = Node(
                id=val_id,
                kind=NodeKind.VALUE,
                name=val_name
            )
            mod_node = self.graph.nodes.get(self.module_id)
            if mod_node and "local_types" in mod_node.properties:
                if scope_id in mod_node.properties["local_types"]:
                    t_name = mod_node.properties["local_types"][scope_id].get(val_name)
                    if t_name:
                        self.graph.nodes[val_id].python_type = PythonType(name=t_name)

            self.graph.edges.append(Edge(
                source=scope_id,
                target=val_id,
                kind=EdgeKind.CONTAINS,
                provenance=[Provenance.SOURCE_AST]
            ))

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

    def visit_Return(self, node: ast.Return):
        func_id = self.current_scope[-1]
        if node.value and isinstance(node.value, ast.Name):
            self._ensure_value_node(node.value.id, func_id)
            self.graph.edges.append(Edge(
                source=func_id,
                target=f"{func_id}::val_{node.value.id}",
                kind=EdgeKind.RETURNS,
                provenance=[Provenance.SOURCE_AST]
            ))
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        scope_id = self.current_scope[-1]
        if isinstance(node.value, ast.Name):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self._ensure_value_node(node.value.id, scope_id)
                    self._ensure_value_node(target.id, scope_id)
                    self.graph.edges.append(Edge(
                        source=f"{scope_id}::val_{node.value.id}",
                        target=f"{scope_id}::val_{target.id}",
                        kind=EdgeKind.PASSES_VALUE,
                        provenance=[Provenance.ASSIGNMENT_PROPAGATION]
                    ))

        elif isinstance(node.value, ast.Call):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self._ensure_value_node(target.id, scope_id)

        self.generic_visit(node)

def run_dataflow_analysis(graph: ProgramGraph):
    for node_id, node in list(graph.nodes.items()):
        if node.kind == NodeKind.MODULE and node.location:
            try:
                with open(node.location.file, "r", encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source)
                visitor = DataFlowVisitor(graph, node_id)
                visitor.visit(tree)
            except Exception:
                pass
