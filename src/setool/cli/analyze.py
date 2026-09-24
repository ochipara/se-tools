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
    if not files:
        typer.secho(
            f"Warning: No Python files found for project at '{config.project_root}'. "
            f"Check your include patterns ({config.include or ['**/*.py']}) and exclude patterns.",
            fg=typer.colors.YELLOW,
        )

    for f in files:
        analyze_file(f, config.project_root, graph)

    run_analysis_pipeline(graph)

    resolve_calls(graph)
    aggregate_internal_dependencies(graph)
    extract_external_dependencies(graph, config.project_root)

    total_discovered_nodes = len(graph.nodes)
    total_discovered_edges = len(graph.edges)

    targets = []
    if entry_point:
        targets = [ep.target for ep in config.entry_points if ep.name == entry_point]
        if not targets:
            typer.secho(
                f"Warning: Entry point '{entry_point}' not found in configuration.",
                fg=typer.colors.YELLOW,
            )
    elif config.entry_points:
        targets = [ep.target for ep in config.entry_points]

    if targets:
        graph = traverse_from_entry_points(graph, targets, max_depth)
        if len(graph.nodes) == 0 and total_discovered_nodes > 0:
            typer.secho(
                f"Warning: Graph traversal from entry point(s) {targets} yielded 0 nodes (out of {total_discovered_nodes} discovered nodes). "
                "Verify that the entry point target functions or methods exist in the codebase.",
                fg=typer.colors.YELLOW,
            )

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

    num_nodes = len(graph.nodes)
    num_edges = len(graph.edges)

    print(f"Extracted graph: {num_nodes} nodes, {num_edges} edges (from {len(files)} files).")

    if num_nodes == 0:
        typer.secho(
            "Warning: The extracted graph is empty (0 nodes, 0 edges)!\n"
            "Possible causes:\n"
            f"  1. project_root ('{config.project_root}') has no matching files for include patterns: {config.include or ['**/*.py']}\n"
            f"  2. Entry point targets ({targets or [ep.target for ep in config.entry_points]}) did not match any symbol in the codebase.",
            fg=typer.colors.RED,
        )

    print(f"Analysis complete. Generated {graph_path}")
