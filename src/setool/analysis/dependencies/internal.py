from ...graph.graph import ProgramGraph
from ...graph.nodes import NodeKind, Node
from ...graph.edges import Edge, EdgeKind
from ...graph.provenance import Provenance

def aggregate_internal_dependencies(graph: ProgramGraph):
    # Track module to package relationships
    module_to_pkg = {}
    for edge in graph.edges:
        if edge.kind == EdgeKind.CONTAINS:
            if edge.source in graph.nodes and graph.nodes[edge.source].kind == NodeKind.PACKAGE:
                if edge.target in graph.nodes and graph.nodes[edge.target].kind == NodeKind.MODULE:
                    module_to_pkg[edge.target] = edge.source

    # For every IMPORTS edge between two internal modules, add a DEPENDS_ON edge between their packages
    internal_imports = []
    for edge in graph.edges:
        if edge.kind == EdgeKind.IMPORTS:
            source_mod = edge.source
            target_mod = edge.target
            # Is target_mod an internal module?
            if target_mod in graph.nodes and graph.nodes[target_mod].kind == NodeKind.MODULE:
                internal_imports.append((source_mod, target_mod))

    existing_deps = set()
    for src, tgt in internal_imports:
        src_pkg = module_to_pkg.get(src, src)
        tgt_pkg = module_to_pkg.get(tgt, tgt)

        if src_pkg != tgt_pkg:
            dep_key = (src_pkg, tgt_pkg)
            if dep_key not in existing_deps:
                existing_deps.add(dep_key)
                graph.edges.append(Edge(
                    source=src_pkg,
                    target=tgt_pkg,
                    kind=EdgeKind.DEPENDS_ON,
                    provenance=[Provenance.IMPORT_RESOLUTION]
                ))
