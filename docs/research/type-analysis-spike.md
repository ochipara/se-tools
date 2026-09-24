# Extended Type Analysis Spike

This document summarizes findings from investigating mature Python type analysis engines (`pyright`, `jedi`, and `mypy`) to obtain fully inferred programmatic type information, in order to meet the requirement of tracking types for local variables and receiver expressions at call sites.

## 1. Pyright / Pylance Language Server (LSP)

We implemented an experimental JSON-RPC client (`scripts/pyright_lsp_spike.py`) that launches `pyright-langserver --stdio`.

### Capabilities observed:
The LSP client issues `textDocument/hover` requests for 0-indexed positions.
- **Type Extraction**: When correctly aligned by column index, Pyright LSP hover provides excellent contextual type information formatted as Markdown text blocks. For example, hovering over the method name `zero_grad` gives the full docstring and signature.
- **Limitations**: The hover text is highly sensitive to exact source-position offsets. Minor mismatches in character indexing often result in `No hover info` or returning the type of a neighboring token. For example, during testing, hovering the `(` in `model(x)` incorrectly returned the type of `features: Tensor` from a nearby token.

**Pros**:
- Very powerful type extraction and docstring extraction.
- Completely supports Unions, Generics, and PyTorch typings.

**Cons**:
- The API is text-based (Markdown strings like `(variable) x: Tensor`), meaning we have to write a custom regex/string parser to extract the actual fully qualified type names from the hover string.
- Requires orchestrating an asynchronous LSP process, sending `didOpen`, `initialized`, and maintaining a stateful connection for every file.
- We should not make the correctness of the core Program Graph depend on parsing hover text.

## 2. Pyright Internals / Programmatic Integration

Pyright is written in TypeScript. It operates by walking an AST and executing an internal type evaluator.
**Feasibility**: Using Pyright's internals directly requires bridging Python to Node.js (e.g., via IPC or native bindings) and heavily coupling to undocumented, internal TypeScript classes (`TypeEvaluator`, `TypePrinter`). There is no stable C API or Python API.
**Recommendation**: Not viable for a stable Python tool.

## 3. Alternative Mature Type Analyzers: Jedi

We implemented a spike using `jedi` (`scripts/jedi_spike.py`), a mature Python auto-completion and static analysis library built explicitly for programmatic querying.

### Capabilities observed:
Using `jedi.Script(text).infer(line, column)`, we retrieved:
- `batch`: `tests.fixtures.type_spike_fixture.Batch`
- `batch.features`: `torch._tensor.Tensor`
- `x`: `torch._tensor.Tensor`
- `model`: `tests.fixtures.type_spike_fixture.Encoder`
- `model(x)`: `tests.fixtures.type_spike_fixture.Encoder` (Jedi struggled with `nn.Module.__call__` inference, returning the class rather than the return type `Tensor`).
- `optimizer`: `torch.optim.optimizer.Optimizer`
- `optimizer.step`: `torch.optim.optimizer.step`

**Pros**:
- Written in Python. Can be imported directly.
- Provides fully-qualified names natively (e.g., `torch._tensor.Tensor`).
- Solves Symbol Resolution and Call Resolution elegantly (provides the module name and the definition name).
- Low implementation complexity.

**Cons**:
- Less accurate than Pyright on deeply nested generics or dynamic framework magic (e.g. `nn.Module` dynamic `__call__` routing to `forward`).

## 4. Alternative Mature Type Analyzers: Mypy

We attempted to use `mypy` programmatically via `mypy.build.build`.
**Pros**: Excellent type checking.
**Cons**: Its programmatic API is unstable, mostly undocumented, and designed around generating error reports rather than serving as a queryable AST database. Retrieving types for arbitrary local expressions requires walking internal `mypy.nodes` representations which map back to custom ASTs, making it extremely difficult to integrate with a standard Python AST.

## Comparison Table

| Expression | Desired information | Pyright LSP (Hover String) | Jedi Inference |
| :--- | :--- | :--- | :--- |
| `batch` | `Batch` | `(parameter) batch: Batch` | `Batch` |
| `batch.features` | `torch.Tensor` | `(variable) features: Tensor` | `torch._tensor.Tensor` |
| `x` | `torch.Tensor` | `(variable) x: Tensor` | `torch._tensor.Tensor` |
| `model` | `Encoder` | `(parameter) model: Encoder` | `Encoder` |
| `model(x)` | `torch.Tensor` | *Inconclusive / Position-Sensitive* | `Encoder` (misses `__call__`) |
| `logits` | `torch.Tensor` | `(variable) logits: Tensor` | `Unknown` |
| `logits.sum()` | `torch.Tensor` | `(variable) loss: Tensor` | `Unknown` |
| `loss` | `torch.Tensor` | `(variable) loss: Tensor` | `Unknown` |
| `optimizer` | `torch.optim.Optimizer` | `(parameter) optimizer: Optimizer` | `Optimizer` |
| `optimizer.zero_grad` | `resolved method/symbol` | *Full Signature & Docstring* | `typing.Callable` |
| `optimizer.step` | `resolved method/symbol` | *Full Signature & Docstring* | `torch.optim.optimizer.step` |

*(Note: Pyright LSP hover strings are approximate representations since LSP requires exact column placement and returns Markdown text rather than typed AST nodes. Mismatches during testing often returned types of neighboring symbols.)*

## Capabilities Distinctions

**A. Type Extraction (`x -> torch.Tensor`)**:
- Pyright LSP provides excellent type extraction but outputs raw text.
- Jedi provides good type extraction as typed Python objects, but fails on complex PyTorch semantics (like `nn.Module.__call__`).

**B. Symbol Resolution vs Callable Type**:
- *Type of Callable*: `typing.Callable[[...], Tensor]`.
- *Definition/Identity of Callable*: `torch.optim.Optimizer.step`.
- Pyright LSP provides hover signatures (callable type).
- Jedi provides exact module and function names (symbol definition/identity).

**C. Call Resolution (`optimizer.step() -> torch.optim.Optimizer.step(...)`)**:
- Neither natively outputs a clean "Call Graph edge" from a query. Jedi provides the target definition which is exactly what we need for resolving the call.

## Final Recommendation

The spike demonstrates that Pyright provides excellent semantic information, but the available integration surface (`textDocument/hover`) is primarily an editor/presentation API. It requires exact source-position queries and returns formatted Markdown/text rather than a stable structured semantic representation. We should not make the correctness of the core Program Graph depend on parsing hover text.

For v1, we will adopt the following architecture:

1. **Python AST is the Primary Representation:** The standard Python `ast` module will remain the authoritative source for code structure, annotations, imports, classes, functions, assignments, calls, and basic data-flow.
2. **Bounded Type Propagation Engine:** We will implement an explicit, bounded semantic propagation engine within `setool`. This engine will propagate types through assignments (`y = x`), parameter/return annotations, constructor calls (`Foo()`), and straightforward attribute lookups. Unsupported semantics will remain `UNKNOWN`.
3. **PyTorch Semantic Rules:** We will embed PyTorch-aware rules. For instance, when `setool` encounters an invocation of an `nn.Module` subclass (`model(x)`), it will explicitly route the call semantics to `Encoder.forward` rather than relying on a generic type analyzer to understand `__call__` magic.
4. **Pluggable Semantic Providers:** The architecture will use an internal `SemanticProvider` Protocol. Our AST engine will be the baseline.
5. **Jedi as Optional Fallback:** Jedi will be treated as an optional assistant for definition lookup and imported-symbol resolution, not as the primary engine.
6. **Pyright Enrichment:** Pyright will be treated as optional, future enrichment. We will not implement a production Pyright LSP client in Stage 4. If added later, its inferences will be explicitly marked with `PYRIGHT_INFERENCE` provenance.
