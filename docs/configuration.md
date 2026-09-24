# Configuration Reference

`setool` is driven by a `setool.json` file.

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `project_root` | `str` | `"."` | The root filepath to execute discovery inside. |
| `entry_points` | `List[EntryPoint]` | `[]` | A list of entrypoints. Format is `{"name": "...", "target": "module_path::symbol"}`. Providing targets subsets the graph traversal, throwing out isolated codebase elements. |
| `include` | `List[str]` | `["**/*.py"]` | Glob patterns of files to explicitly parse. |
| `exclude` | `List[str]` | `["tests/**", ".venv/**", "**/__pycache__/**"]` | Glob patterns to ignore during discovery. |
| `max_call_depth` | `int` | `15` | Limit for `CALLS` edge recursion traversals. |

Example:
```json
{
  "project_root": ".",
  "entry_points": [
    {
      "name": "training",
      "target": "src/train.py::main"
    }
  ],
  "include": ["src/**"],
  "exclude": ["tests/**", ".venv/**", "**/__pycache__/**"],
  "max_call_depth": 15
}
```
