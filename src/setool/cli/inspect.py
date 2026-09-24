import typer
import json
from pathlib import Path
from ..serialization.json import deserialize_graph

app = typer.Typer()

@app.command()
def inspect(
    report_dir: Path = typer.Argument(..., help="Path to report directory"),
    kind: str = typer.Argument(..., help="What to inspect: symbol, calls, types, dependencies, unresolved"),
    target: str = typer.Argument(None, help="Target ID (e.g. symbol name)"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON results")
):
    """Inspect the Program Graph from the command line."""
    graph_path = report_dir / "graph.json"
    if not graph_path.exists():
        print(f"Error: {graph_path} not found.")
        raise typer.Exit(code=1)

    try:
        graph = deserialize_graph(str(graph_path))
    except Exception as e:
        print(f"Error loading graph: {e}")
        raise typer.Exit(code=1)

    result = {}

    if kind == "symbol" and target:
        if target in graph.nodes:
            result = graph.nodes[target].model_dump()
        else:
            print(f"Symbol {target} not found.")
            raise typer.Exit(code=1)

    elif kind == "dependencies":
        deps = [e.model_dump() for e in graph.edges if e.kind == "DEPENDS_ON"]
        if target:
            deps = [d for d in deps if d["target"] == target or target in d["target"]]
        result = {"dependencies": deps}

    elif kind == "unresolved":
        unresolved = [n.model_dump() for n in graph.nodes.values() if n.kind == "call_site" and n.properties.get("resolution_status") == "unresolved"]
        result = {"unresolved_calls": unresolved}

    else:
        print(f"Unsupported inspection kind: {kind}")
        raise typer.Exit(code=1)

    if json_output:
        print(json.dumps(result, indent=2))
    else:
        import pprint
        pprint.pprint(result)
