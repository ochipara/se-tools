import ast
from typing import List, Optional
from ...graph.graph import ProgramGraph
from ...graph.nodes import NodeKind, Node
from ...graph.edges import Edge, EdgeKind
from ...graph.provenance import Provenance

def resolve_calls(graph: ProgramGraph):
    for call_id, call_node in list(graph.nodes.items()):
        if call_node.kind != NodeKind.CALL_SITE:
            continue

        func_ast = call_node.properties.get("ast_func")
        if not func_ast:
            continue

        parent_id = None
        for edge in graph.edges:
            if edge.target == call_id and edge.kind == EdgeKind.CONTAINS:
                parent_id = edge.source
                break

        if not parent_id:
            continue

        target_ids = []
        resolution_evidence = None
        status = "unresolved"

        if isinstance(func_ast, ast.Name):
            func_name = func_ast.id
            module_id = parent_id.split("::")[0].split(".")[0] if "::" in parent_id else parent_id.split(".")[0]
            possible_target = f"{module_id}.{func_name}"
            if possible_target in graph.nodes:
                target_ids.append(possible_target)
                resolution_evidence = Provenance.SOURCE_AST
                status = "resolved"
            else:
                for edge in graph.edges:
                    if edge.source == module_id and edge.kind == EdgeKind.IMPORTS:
                        target_mod = edge.target
                        possible_imported = f"{target_mod}.{func_name}"
                        if possible_imported in graph.nodes:
                            target_ids.append(possible_imported)
                            resolution_evidence = Provenance.IMPORT_RESOLUTION
                            status = "resolved"

        elif isinstance(func_ast, ast.Attribute):
            attr_name = func_ast.attr
            if isinstance(func_ast.value, ast.Name):
                obj_name = func_ast.value.id

                module_node = None
                for n_id, n in graph.nodes.items():
                    if n.kind == NodeKind.MODULE and parent_id.startswith(n_id):
                        module_node = n
                        break

                if module_node and "local_types" in module_node.properties:
                    scope_types = module_node.properties["local_types"].get(parent_id, {})
                    if obj_name in scope_types:
                        obj_type_name = scope_types[obj_name]

                        class_id = None
                        for nid, n in graph.nodes.items():
                            if n.kind in (NodeKind.CLASS, NodeKind.PYTORCH_MODULE) and n.name == obj_type_name:
                                class_id = nid
                                break

                        if class_id:
                            method_target = f"{class_id}.{attr_name}"
                            if method_target in graph.nodes:
                                target_ids.append(method_target)
                                resolution_evidence = Provenance.RECEIVER_TYPE_RESOLUTION
                                status = "resolved"
                            else:
                                bases = graph.nodes[class_id].properties.get("bases", [])
                                for base in bases:
                                    base_id = None
                                    for nid, n in graph.nodes.items():
                                        if n.kind in (NodeKind.CLASS, NodeKind.PYTORCH_MODULE) and n.name == base:
                                            base_id = nid
                                            break
                                    if base_id:
                                        base_method = f"{base_id}.{attr_name}"
                                        if base_method in graph.nodes:
                                            target_ids.append(base_method)
                                            resolution_evidence = Provenance.INHERITANCE_RESOLUTION
                                            status = "resolved"

            if status == "unresolved":
                possibles = []
                for nid, n in graph.nodes.items():
                    if n.kind == NodeKind.METHOD and n.name == attr_name:
                        possibles.append(nid)
                if len(possibles) > 0:
                    status = "possible"
                    target_ids.extend(possibles)
                    resolution_evidence = Provenance.SOURCE_AST

        call_node.properties["resolution_status"] = status
        call_node.properties["possible_targets"] = target_ids

        del call_node.properties["ast_func"]

        for target in target_ids:
            graph.edges.append(Edge(
                source=parent_id,
                target=target,
                kind=EdgeKind.CALLS,
                provenance=[resolution_evidence] if resolution_evidence else [],
                properties={"call_site_id": call_id, "status": status}
            ))
