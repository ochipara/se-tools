import ast
from typing import List, Dict, Optional
from ..graph.graph import ProgramGraph
from ..graph.nodes import Node, NodeKind, Location
from ..graph.edges import Edge, EdgeKind
from ..graph.provenance import Provenance
from .modules import filepath_to_module, get_package_hierarchy

class SymbolVisitor(ast.NodeVisitor):
    def __init__(self, graph: ProgramGraph, module_id: str, filepath: str):
        self.graph = graph
        self.module_id = module_id
        self.filepath = filepath
        self.current_scope = [module_id]

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
        class_node = Node(
            id=class_id,
            kind=NodeKind.CLASS,
            name=node.name,
            location=self._get_location(node)
        )
        self.graph.nodes[class_id] = class_node

        # CONTAINS edge from parent scope
        self.graph.edges.append(Edge(
            source=self.current_scope[-1],
            target=class_id,
            kind=EdgeKind.CONTAINS,
            provenance=[Provenance.SOURCE_AST]
        ))

        # INHERITS edges
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_name = base.id
                # Attempt to guess base ID (this is rudimentary for discovery)
                self.graph.edges.append(Edge(
                    source=class_id,
                    target=base_name,
                    kind=EdgeKind.INHERITS,
                    provenance=[Provenance.SOURCE_AST]
                ))

        self.current_scope.append(class_id)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        parent_id = self.current_scope[-1]
        kind = NodeKind.METHOD if "::" in parent_id else NodeKind.FUNCTION
        func_id = f"{parent_id}.{node.name}"

        func_node = Node(
            id=func_id,
            kind=kind,
            name=node.name,
            location=self._get_location(node)
        )
        self.graph.nodes[func_id] = func_node

        self.graph.edges.append(Edge(
            source=parent_id,
            target=func_id,
            kind=EdgeKind.CONTAINS,
            provenance=[Provenance.SOURCE_AST]
        ))

        self.current_scope.append(func_id)
        self.generic_visit(node)
        self.current_scope.pop()

    def _resolve_relative_module(self, node: ast.ImportFrom) -> Optional[str]:
        if not node.level or node.level == 0:
            return node.module

        module_parts = self.module_id.split(".")
        if self.filepath.endswith("__init__.py"):
            pkg_parts = module_parts
        else:
            pkg_parts = module_parts[:-1]

        cut = node.level - 1
        if cut > len(pkg_parts):
            base_parts = []
        elif cut > 0:
            base_parts = pkg_parts[:-cut]
        else:
            base_parts = pkg_parts

        if node.module:
            if base_parts:
                return ".".join(base_parts) + "." + node.module
            return node.module
        else:
            return ".".join(base_parts) if base_parts else None

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            target_mod = alias.name
            props = {}
            if alias.asname:
                props["alias"] = alias.asname
            self.graph.edges.append(Edge(
                source=self.current_scope[-1],
                target=target_mod,
                kind=EdgeKind.IMPORTS,
                provenance=[Provenance.SOURCE_AST],
                properties=props
            ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        resolved_module = self._resolve_relative_module(node)
        if resolved_module:
            imported_names = [alias.name for alias in node.names]
            aliases = {alias.asname: alias.name for alias in node.names if alias.asname}
            props = {"imported_names": imported_names}
            if aliases:
                props["aliases"] = aliases
            self.graph.edges.append(Edge(
                source=self.current_scope[-1],
                target=resolved_module,
                kind=EdgeKind.IMPORTS,
                provenance=[Provenance.SOURCE_AST],
                properties=props
            ))
        self.generic_visit(node)

def analyze_file(filepath: str, project_root: str, graph: ProgramGraph):
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return

    module_name = filepath_to_module(filepath, project_root)

    # Add packages if they don't exist
    packages = get_package_hierarchy(module_name)
    parent_pkg_id = None
    for pkg_id, pkg_name in packages:
        if pkg_id not in graph.nodes:
            pkg_node = Node(
                id=pkg_id,
                kind=NodeKind.PACKAGE,
                name=pkg_name
            )
            graph.nodes[pkg_id] = pkg_node

            # Link to parent package if exists
            if parent_pkg_id:
                graph.edges.append(Edge(
                    source=parent_pkg_id,
                    target=pkg_id,
                    kind=EdgeKind.CONTAINS,
                    provenance=[Provenance.SOURCE_AST]
                ))
        parent_pkg_id = pkg_id

    # Add module node
    module_node = Node(
        id=module_name,
        kind=NodeKind.MODULE,
        name=module_name.split(".")[-1],
        location=Location(file=filepath, line_start=1, line_end=len(source.splitlines()))
    )
    graph.nodes[module_name] = module_node

    # Link module to its parent package
    if parent_pkg_id:
        graph.edges.append(Edge(
            source=parent_pkg_id,
            target=module_name,
            kind=EdgeKind.CONTAINS,
            provenance=[Provenance.SOURCE_AST]
        ))

    visitor = SymbolVisitor(graph, module_name, filepath)
    visitor.visit(tree)
