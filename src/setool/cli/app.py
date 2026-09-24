import typer
from typing import Optional
from pathlib import Path

from .analyze import analyze
from .serve import serve
from .validate import validate
from .inspect import inspect

app = typer.Typer(help="setool - Python/PyTorch Architecture Explorer")

app.command(name="analyze")(analyze)
app.command(name="serve")(serve)
app.command(name="validate")(validate)
app.command(name="inspect")(inspect)

@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(False, "--version", help="Show version and exit."),
):
    if version:
        print("setool 0.1.0")
        raise typer.Exit()

@app.command()
def completion(shell: str = typer.Argument(..., help="The shell to generate completion for.")):
    """Generate shell completion script."""
    import subprocess
    import os
    try:
        subprocess.run(["setool", "--show-completion", shell], check=True)
    except Exception as e:
        print(f"Error generating completion: {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
