# Getting Started

Welcome to `setool`.

`setool` helps developers understand Python machine-learning codebases. By parsing Python ASTs, traversing dependencies, and building bounded type inferences, `setool` translates a codebase into an interactive Program Graph.

## Installation

Install directly via `pip`:

```bash
# Clone the repository and install
git clone https://github.com/your-username/setool.git
cd setool
pip install .
```

Verify the installation:
```bash
setool --version
# Expected: setool 0.1.0
```

## Basic Flow

Let's walk through analyzing a simple repository.

### 1. Select a Project
Navigate into any Python project you wish to explore. Let's assume you have a `src/train.py` script containing a function called `main`.

### 2. Define an Entry Point
Create a configuration file named `setool.json` in the root of the project:

```json
{
  "project_root": ".",
  "entry_points": [
    {
      "name": "training",
      "target": "src/train.py::main"
    }
  ],
  "include": ["src/**/*.py"],
  "max_call_depth": 15
}
```
This tells `setool` to start at `main` and recursively traverse the call graph and imports to build its visual architecture.

### 3. Validate Configuration
To ensure your configuration is syntactically sound:
```bash
setool validate setool.json
```

### 4. Analyze
Run the analysis pipeline. This will trace PyTorch module initializations, construct basic data flows, and bundle a UI directory.
```bash
setool analyze setool.json --output report/
```

### 5. Explore the Report
Spin up the interactive Web server:
```bash
setool serve report/
```

You can now open `http://127.0.0.1:8000` in your web browser.

You'll see a graph with colored nodes:
* `Packages` (Orange Hexagons)
* `Modules` (Yellow)
* `Classes` (Green)
* `Functions/Methods` (Teal)
* `PyTorch Modules` (Purple)

Use the top navigation bar to filter down to **Calls**, **Types**, or **Dependencies**. Click on any node to view detailed insights in the right-hand panel, including the Python types of variables and functions.
