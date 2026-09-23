# Program Graph

The **Program Graph** is the central artifact of `setool`. It is a typed property graph that represents the software architecture of a Python machine learning project.

## Node Types

Nodes represent entities in the code such as:
- Packages
- Modules
- Classes
- Functions and Methods
- PyTorch Modules
- Call Sites
- Values
- External APIs

## Edge Types

Edges represent relationships such as:
- `CONTAINS`: e.g., Module contains Class.
- `IMPORTS`: e.g., Module A imports Module B.
- `INHERITS`: e.g., Class A inherits from Class B.
- `CALLS`: e.g., Function A calls Function B.

## Provenance

Every significant inferred relationship carries provenance, describing *how* it was determined (e.g., from Python AST, inferred by Pyright, defined in pyproject.toml).
