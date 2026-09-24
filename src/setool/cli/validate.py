import typer
from pathlib import Path
from ..config.loader import load_config

app = typer.Typer()

@app.command()
def validate(
    config_path: Path = typer.Argument(..., help="Path to setool.json"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON results"),
):
    """Validate a setool configuration file."""
    try:
        config = load_config(str(config_path))
        if json_output:
            print('{"status": "ok"}')
        else:
            print(f"Configuration valid.")
    except Exception as e:
        if json_output:
            import json
            print(json.dumps({"status": "error", "message": str(e)}))
        else:
            print(f"Validation failed: {e}")
        raise typer.Exit(code=2)
