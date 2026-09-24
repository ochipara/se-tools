# setool

`setool` is a Python/PyTorch Architecture Explorer. It uses static analysis to generate an interactive Program Graph of ML codebases.

It parses your project's AST to boundedly infer variable types, traces function call graphs, captures component data-flows, and resolves internal and external dependencies (including PyTorch `nn.Module` forward pass logic).

## Installation

```bash
pip install .
```

## Quick Start

1. Define a configuration file `setool.json` in your repository:
```json
{
  "project_root": ".",
  "entry_points": [
    {
      "name": "training",
      "target": "train.py::main"
    }
  ],
  "include": ["*.py"]
}
```

2. **Analyze** your codebase:
```bash
setool analyze setool.json --output report/
```

3. **Serve** the interactive Cytoscape web UI:
```bash
setool serve report/
```
Then navigate to `http://127.0.0.1:8000` to interact with your graph!

## Advanced

* **Validate**: `setool validate setool.json`
* **Inspect**: `setool inspect report/ calls "src.main.foo"`
* **Completion**: `source <(setool completion bash)`

For detailed guides, please see the `docs/` folder!
