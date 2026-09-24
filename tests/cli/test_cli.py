from typer.testing import CliRunner
from setool.cli.app import app
import os
import tempfile
import json
import traceback

runner = CliRunner()

def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "setool 0.1.0" in result.stdout

def test_validate_valid():
    with tempfile.TemporaryDirectory() as d:
        config_path = os.path.join(d, "setool.json")
        with open(config_path, "w") as f:
            json.dump({"project_root": "."}, f)

        result = runner.invoke(app, ["validate", config_path, "--json"])
        if result.exit_code != 0:
            print("Validate Exception:", result.exception)
        assert result.exit_code == 0
        assert "ok" in result.stdout

def test_analyze():
    with tempfile.TemporaryDirectory() as d:
        config_path = os.path.join(d, "setool.json")
        with open(config_path, "w") as f:
            json.dump({"project_root": d}, f)

        source = "def foo(): pass"
        with open(os.path.join(d, "main.py"), "w") as f:
            f.write(source)

        report_dir = os.path.join(d, "report")
        result = runner.invoke(app, ["analyze", config_path, "--output", report_dir])
        assert result.exit_code == 0
        assert os.path.exists(os.path.join(report_dir, "graph.json"))
        assert os.path.exists(os.path.join(report_dir, "dependencies.json"))

def test_inspect():
    with tempfile.TemporaryDirectory() as d:
        config_path = os.path.join(d, "setool.json")
        with open(config_path, "w") as f:
            json.dump({"project_root": d}, f)

        source = "def foo(): pass"
        with open(os.path.join(d, "main.py"), "w") as f:
            f.write(source)

        report_dir = os.path.join(d, "report")
        runner.invoke(app, ["analyze", config_path, "--output", report_dir])

        result = runner.invoke(app, ["inspect", report_dir, "symbol", "main.foo", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["id"] == "main.foo"
        assert data["kind"] == "function"
