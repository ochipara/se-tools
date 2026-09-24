import os
import sys
from typing import Dict, List
from ...graph.graph import ProgramGraph
from ...graph.nodes import Node, NodeKind
from ...graph.edges import Edge, EdgeKind
from ...graph.provenance import Provenance

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError:
        import toml as tomllib  # type: ignore

def parse_pyproject(filepath: str) -> List[str]:
    try:
        if hasattr(tomllib, "load"):
            try:
                with open(filepath, "rb") as f:
                    data = tomllib.load(f)
            except TypeError:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = tomllib.load(f)
        elif hasattr(tomllib, "loads"):
            with open(filepath, "r", encoding="utf-8") as f:
                data = tomllib.loads(f.read())
        else:
            return []
        deps = data.get("project", {}).get("dependencies", [])
        return deps
    except Exception:
        return []

def extract_external_dependencies(graph: ProgramGraph, project_root: str):
    # Try parsing pyproject.toml
    pyproject_path = os.path.join(project_root, "pyproject.toml")
    declared_deps = []
    if os.path.exists(pyproject_path):
        declared_deps = parse_pyproject(pyproject_path)

    for dep in declared_deps:
        # Strip versions (naive)
        dep_name = dep.split(">")[0].split("=")[0].split("<")[0].strip()
        dep_id = f"dist::{dep_name}"
        if dep_id not in graph.nodes:
            graph.nodes[dep_id] = Node(
                id=dep_id,
                kind=NodeKind.DISTRIBUTION,
                name=dep_name,
                properties={"declared": True}
            )

    # Convert external imports to USES_API and DECLARES_DEPENDENCY
    for edge in graph.edges:
        if edge.kind == EdgeKind.IMPORTS:
            target_mod = edge.target
            # If it's not an internal module, it's external
            if target_mod not in graph.nodes or graph.nodes[target_mod].kind != NodeKind.MODULE:
                dist_name = target_mod.split(".")[0]
                dist_id = f"dist::{dist_name}"

                if dist_id not in graph.nodes:
                    graph.nodes[dist_id] = Node(
                        id=dist_id,
                        kind=NodeKind.DISTRIBUTION,
                        name=dist_name,
                        properties={"declared": False, "observed": True}
                    )
                else:
                    graph.nodes[dist_id].properties["observed"] = True

                # Link the module that imported it to the distribution
                graph.edges.append(Edge(
                    source=edge.source,
                    target=dist_id,
                    kind=EdgeKind.DEPENDS_ON,
                    provenance=[Provenance.IMPORT_RESOLUTION]
                ))
