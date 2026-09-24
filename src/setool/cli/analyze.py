import typer
import os
import json
import shutil
from pathlib import Path
from ..config.loader import load_config
from ..discovery.files import discover_files
from ..discovery.symbols import analyze_file
from ..analysis.pipeline import run_analysis_pipeline
from ..analysis.calls.resolver import resolve_calls
from ..analysis.dependencies.internal import aggregate_internal_dependencies
from ..analysis.dependencies.cycles import detect_dependency_cycles
from ..analysis.dependencies.external import extract_external_dependencies
from ..graph.graph import ProgramGraph
from ..graph.traversal import traverse_from_entry_points
from ..serialization.json import serialize_graph

app = typer.Typer()

@app.command()
def analyze(
    config_path: Path = typer.Argument(..., help="Path to setool.json configuration"),
    output: Path = typer.Option(Path("report/"), "--output", help="Output directory for report files"),
    entry_point: str = typer.Option(None, "--entry-point", help="Optional specific entry point to analyze"),
    max_depth: int = typer.Option(15, "--max-depth", help="Maximum call depth"),
    no_ui: bool = typer.Option(False, "--no-ui", help="Skip generating UI assets"),
    verbose: bool = typer.Option(False, "--verbose", help="Print verbose output"),
):
    """Analyze a project based on configuration."""
    try:
        config = load_config(str(config_path))
    except Exception as e:
        print(f"Error loading config: {e}")
        raise typer.Exit(code=2)

    if verbose:
        print(f"Analyzing project at {config.project_root}")

    graph = ProgramGraph()
    files = discover_files(config)

    for f in files:
        analyze_file(f, config.project_root, graph)

    run_analysis_pipeline(graph)

    resolve_calls(graph)
    aggregate_internal_dependencies(graph)
    extract_external_dependencies(graph, config.project_root)

    if entry_point:
        targets = [ep.target for ep in config.entry_points if ep.name == entry_point]
        if targets:
            graph = traverse_from_entry_points(graph, targets, max_depth)
    elif config.entry_points:
        targets = [ep.target for ep in config.entry_points]
        graph = traverse_from_entry_points(graph, targets, max_depth)

    os.makedirs(output, exist_ok=True)
    graph_path = os.path.join(output, "graph.json")
    serialize_graph(graph, graph_path)

    cycles = detect_dependency_cycles(graph)
    dep_path = os.path.join(output, "dependencies.json")
    with open(dep_path, "w") as f:
        json.dump({"cycles": cycles}, f, indent=2)

    if not no_ui:
        ui_source = os.path.join(os.path.dirname(__file__), "..", "report", "assets")
        if os.path.exists(ui_source):
            shutil.copytree(ui_source, output, dirs_exist_ok=True)

    print(f"Analysis complete. Generated {graph_path}")
