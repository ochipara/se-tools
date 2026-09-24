# Reading the Report

The `setool` interactive UI is powered by Cytoscape.js.

Because ML repositories map cleanly to property graphs, the tool translates Python semantics directly into visual relationships.

## Node Types

* **Package (Orange Hexagon)**: E.g., `src.training`.
* **Module (Yellow Square)**: E.g., `src.training.train`.
* **Distribution (Pink Diamond)**: External dependencies (like `torch` or `requests`).
* **Class (Green Rectangle)**: Standard Python classes.
* **PyTorch Module (Purple Rectangle)**: Classes that inherit from `nn.Module`.
* **Function / Method (Teal Rectangle)**: Callables.
* **Value (Grey Ellipse)**: Local variables (`x`), parameters (`args`), or implicit values (`self`).
* **Call Site (Small Black Triangle)**: Specifically denotes the exact line/col location of an invocation `a.b()`.

## Edge Types

* **CONTAINS (Grey Curve)**: Denotes hierarchical ownership (Package `CONTAINS` Module, Module `CONTAINS` Function). In the PyTorch view, a Module `CONTAINS` a SubModule.
* **CALLS (Red Curve)**: Indicates execution flow. Source is the calling method, target is the invoked method.
* **PASSES_VALUE (Grey Curve)**: Local data flow via assignment (`y = x`).
* **RETURNS (Grey Curve)**: Data flow from a function exiting (`return x`).
* **DEPENDS_ON (Pink Curve)**: Module-to-Module Imports or Module-to-Distribution usage.
* **INHERITS**: A Class inheritance constraint.

## What Static Analysis Misses

If a call edge says "Resolution: Unresolved", it means `setool` could not statically deduce the object's type without running the code. The tool errs on the side of safety: it will display `UNKNOWN` data or unresolved nodes rather than falsely attributing a target.

Similarly, if multiple classes define `.process()`, and the variable type is unknown, the dispatch resolution will be `possible` for *all* candidates instead of strictly resolving.
