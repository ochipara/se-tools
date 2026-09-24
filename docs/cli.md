# CLI Reference

`setool` is built with `typer`. Below are the primary commands.

## `setool analyze`
Generates the Program Graph JSON, extracts internal and external dependencies, runs type/PyTorch analysis, and copies the interactive React UI into an output folder.

```bash
setool analyze setool.json --output report/
```
**Options**:
* `--output`: Output directory. (Default: `report/`)
* `--entry-point`: Subset the traversal to a single configured entry point name.
* `--max-depth`: Caps call graph traversal depth.
* `--no-ui`: Disables copying UI HTML/JS assets to the report directory.
* `--verbose`: Logs execution progression.

## `setool serve`
A lightweight `uvicorn` and `fastapi` server to host the exported `report/` folder as a static site.

```bash
setool serve report/ --port 8080 --host 0.0.0.0
```

## `setool validate`
Validates the syntax and structure of the `setool.json` configuration file without running analysis.

```bash
setool validate setool.json --json
```

## `setool inspect`
Reads a generated `graph.json` headlessly, outputting specific metrics or node boundaries, making it highly useful for CI/CD integrations or shell scripts.

```bash
# Print a specific node's JSON serialization
setool inspect report/ symbol "src.main::main"

# Print all nodes that failed to resolve during static analysis
setool inspect report/ unresolved

# Print all external distributions required by the codebase
setool inspect report/ dependencies
```

## `setool completion`
Prints shell auto-completion instructions to standard out.

```bash
setool completion bash
```
