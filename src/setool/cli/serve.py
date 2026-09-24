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
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    server = FastAPI()
    server.mount("/", StaticFiles(directory=str(report_dir), html=True), name="static")
    print(f"Serving report from {report_dir} at http://{host}:{port}")
    uvicorn.run(server, host=host, port=port)
