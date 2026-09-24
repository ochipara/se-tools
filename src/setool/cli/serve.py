import typer
import uvicorn
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = typer.Typer()


def create_serve_app(report_dir: Path) -> FastAPI:
    """Create and configure FastAPI application for serving reports."""
    report_dir = Path(report_dir).resolve()
    if not report_dir.exists():
        raise FileNotFoundError(f"Report directory '{report_dir}' does not exist.")

    graph_file = report_dir / "graph.json"
    server = FastAPI(title="setool Architecture Explorer")

    @server.get("/graph.json")
    def get_graph():
        if not graph_file.exists():
            raise HTTPException(status_code=404, detail=f"'{graph_file.name}' not found")
        return FileResponse(graph_file, media_type="application/json")

    @server.get("/dependencies.json")
    def get_dependencies():
        dep_file = report_dir / "dependencies.json"
        if dep_file.exists():
            return FileResponse(dep_file, media_type="application/json")
        return JSONResponse({"cycles": []})

    ui_source = Path(__file__).resolve().parent.parent / "report" / "assets"
    static_dir = ui_source if ui_source.exists() else report_dir
    server.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    return server


@app.command()
def serve(
    report_dir: Path = typer.Argument(..., help="Path to report directory"),
    port: int = typer.Option(8000, "--port", help="Port to serve on"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
):
    """Serve the interactive report locally."""
    report_dir = Path(report_dir).resolve()
    if not report_dir.exists():
        typer.secho(f"Error: Report directory '{report_dir}' does not exist.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    graph_file = report_dir / "graph.json"
    if not graph_file.exists():
        typer.secho(f"Warning: '{graph_file}' not found in report directory.", fg=typer.colors.YELLOW)

    server = create_serve_app(report_dir)
    print(f"Serving report from {report_dir} at http://{host}:{port}")
    uvicorn.run(server, host=host, port=port)


