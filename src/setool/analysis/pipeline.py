import ast
from typing import Dict
from ..graph.graph import ProgramGraph
from .types.analyzer import ASTTypePropagator
from .calls.discovery import CallVisitor
from .dataflow.analyzer import DataFlowVisitor
from .pytorch.modules import PyTorchVisitor

def build_ast_cache(graph: ProgramGraph) -> Dict[str, ast.AST]:
    cache = {}
    from ..graph.nodes import NodeKind
    for node_id, node in graph.nodes.items():
        if node.kind == NodeKind.MODULE and node.location:
            try:
                with open(node.location.file, "r", encoding="utf-8") as f:
                    source = f.read()
                cache[node_id] = ast.parse(source)
            except Exception:
                pass
    return cache

def run_analysis_pipeline(graph: ProgramGraph):
    ast_cache = build_ast_cache(graph)

    for node_id, tree in ast_cache.items():
        v = PyTorchVisitor(graph, node_id)
        v.visit(tree)

    for node_id, tree in ast_cache.items():
        propagator = ASTTypePropagator(graph, node_id)
        propagator.visit(tree)
        node = graph.nodes[node_id]
        if "local_types" not in node.properties:
            node.properties["local_types"] = {}
        for scope, typedict in propagator.local_types.items():
            node.properties["local_types"][scope] = {k: v[0].name for k, v in typedict.items()}

    for node_id, tree in ast_cache.items():
        v = CallVisitor(graph, node_id, graph.nodes[node_id].location.file)
        v.visit(tree)

    for node_id, tree in ast_cache.items():
        v = DataFlowVisitor(graph, node_id)
        v.visit(tree)
