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


def test_serve_app():
    import asyncio
    from pathlib import Path
    from setool.cli.serve import create_serve_app

    async def asgi_get(asgi_app, path: str):
        messages = []
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": [],
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        await asgi_app(scope, receive, send)
        status = next(m["status"] for m in messages if m["type"] == "http.response.start")
        body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
        return status, body

    with tempfile.TemporaryDirectory() as d:
        report_dir = Path(d)
        graph_data = {"nodes": {}, "edges": []}
        with open(report_dir / "graph.json", "w") as f:
            json.dump(graph_data, f)

        server = create_serve_app(report_dir)

        # 1. UI assets served from package
        status, body = asyncio.run(asgi_get(server, "/"))
        assert status == 200
        assert b"<html" in body.lower()

        status, body = asyncio.run(asgi_get(server, "/app.js"))
        assert status == 200

        # 2. Graph data served from report_dir
        status, body = asyncio.run(asgi_get(server, "/graph.json"))
        assert status == 200
        assert json.loads(body.decode("utf-8")) == graph_data

        # 3. Dependencies served from report_dir (default empty)
        status, body = asyncio.run(asgi_get(server, "/dependencies.json"))
        assert status == 200
        assert json.loads(body.decode("utf-8")) == {"cycles": []}


