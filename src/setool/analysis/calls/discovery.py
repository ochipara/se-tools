import ast
from typing import Optional, List
from ...graph.graph import ProgramGraph
from ...graph.nodes import Node, NodeKind, Location
from ...graph.edges import Edge, EdgeKind
from ...graph.provenance import Provenance

class CallVisitor(ast.NodeVisitor):
    def __init__(self, graph: ProgramGraph, module_id: str, filepath: str):
        self.graph = graph
        self.module_id = module_id
        self.filepath = filepath
        self.current_scope = [module_id]
        self.call_count = 0

    def _get_location(self, node: ast.AST) -> Location:
        return Location(
            file=self.filepath,
            line_start=node.lineno,
            line_end=getattr(node, 'end_lineno', node.lineno),
            col_start=node.col_offset,
            col_end=getattr(node, 'end_col_offset', node.col_offset)
        )

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

    def visit_Call(self, node: ast.Call):
        self.call_count += 1
        parent_id = self.current_scope[-1]
        call_id = f"{parent_id}::call_{self.call_count}"

        try:
            expr_text = ast.unparse(node)
        except Exception:
            expr_text = "<complex_call>"

        call_node = Node(
            id=call_id,
            kind=NodeKind.CALL_SITE,
            name=f"call_{self.call_count}",
            location=self._get_location(node),
            properties={
                "source_expression": expr_text,
                "resolution_status": "unresolved"
            }
        )
        self.graph.nodes[call_id] = call_node

        self.graph.edges.append(Edge(
            source=parent_id,
            target=call_id,
            kind=EdgeKind.CONTAINS,
            provenance=[Provenance.SOURCE_AST]
        ))

        call_node.properties["ast_func"] = node.func

        self.generic_visit(node)

def discover_calls(graph: ProgramGraph):
    for node_id, node in list(graph.nodes.items()):
        if node.kind == NodeKind.MODULE and node.location:
            try:
                with open(node.location.file, "r", encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source)
                visitor = CallVisitor(graph, node_id, node.location.file)
                visitor.visit(tree)
            except Exception:
                pass
