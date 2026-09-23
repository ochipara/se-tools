# Program Graph Schema

The Program Graph schema is strictly defined using Pydantic models in `src/setool/graph/`.

## Core Models

- `ProgramGraph`: The root container for the graph.
- `Node`: Represents an entity, with an `id`, `kind`, and `properties`.
- `Edge`: Represents a relationship between two nodes.
- `PythonType`: Represents type information attached to values or functions.
- `Location`: Source location (file, line, column).
- `Provenance`: Enum detailing the source of evidence.

Serialization to JSON schema can be generated using `scripts/generate_schemas.py`.
