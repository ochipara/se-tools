import typer
import uvicorn
from pathlib import Path

app = typer.Typer()

@app.command()
def serve(
    report_dir: Path = typer.Argument(..., help="Path to report directory"),
    port: int = typer.Option(8000, "--port", help="Port to serve on"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
):
    """Serve the interactive report locally."""
    import shutil
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    report_dir = Path(report_dir).resolve()
    if not report_dir.exists():
        typer.secho(f"Error: Report directory '{report_dir}' does not exist.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    ui_source = Path(__file__).resolve().parent.parent / "report" / "assets"
    if not (report_dir / "index.html").exists() and ui_source.exists():
        print(f"Populating UI assets into {report_dir}...")
        shutil.copytree(ui_source, report_dir, dirs_exist_ok=True)

    server = FastAPI(title="setool Architecture Explorer")
    server.mount("/", StaticFiles(directory=str(report_dir), html=True), name="static")
    print(f"Serving report from {report_dir} at http://{host}:{port}")
    uvicorn.run(server, host=host, port=port)
