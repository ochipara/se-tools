# Type Analysis Spike

This document summarizes findings from investigating Python type analysis using Python's `ast` module and `pyright`.

## Methodology
A small spike script (`scripts/type_analysis_spike.py`) was written to parse a simple Python script containing fully typed functions and classes. The goal was to extract type information and evaluate Pyright's capabilities compared to AST-based extraction.

## Findings

1. **Python `ast`**:
    - The `ast` module successfully parses declared type annotations (e.g., arguments and return types). Using `ast.unparse()`, we can get the string representation of these annotations.
    - **Limitations**: AST alone cannot resolve imported types to their fully qualified names (e.g., it only sees `Classifier` rather than `mypackage.Classifier`). It also cannot infer types for local variables (e.g., `x = batch.features`).

2. **Pyright via CLI (`--outputjson`)**:
    - Pyright's standard CLI outputs diagnostics (errors/warnings) but does **not** provide a direct machine-readable API for extracting types of arbitrary expressions or variables on demand.
    - While `pyright --verifytypes` exists, it is focused on library completeness rather than arbitrary graph extraction.
    - **Language Server Protocol (LSP)**: To get the actual inferred types (like hovering over `x = batch.features`), one would typically need to interact with Pyright via LSP (Language Server Protocol) using requests like `textDocument/hover`. This introduces significant complexity and process orchestration overhead for static analysis.

## Conclusion and Recommendations
For Stage 4 (Type Analysis), we should proceed with a layered approach:
- **Baseline**: Use `ast` for all declared annotations (function arguments, returns, class attributes). This will provide immediate value with `PROVENANCE = DECLARED_ANNOTATION`.
- **Inferred Types**: Since invoking Pyright via CLI does not yield a dump of all inferred types natively, we will need to either parse its LSP responses or rely heavily on `ast` and simple heuristics for the baseline. If true static inference is required, writing a small LSP client or evaluating another tool (like `mypy`'s AST or `pytype`) may be necessary. For v1, building a custom full-blown inference engine is out of scope per the spec, so we will document this limitation and use AST annotations heavily.
