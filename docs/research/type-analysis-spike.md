# Extended Type Analysis Spike

This document summarizes findings from investigating mature Python type analysis engines (`pyright`, `jedi`, and `mypy`) to obtain fully inferred programmatic type information, in order to meet the requirement of tracking types for local variables and receiver expressions at call sites.

## 1. Pyright / Pylance Language Server (LSP)

We implemented an experimental JSON-RPC client (`scripts/pyright_lsp_spike.py`) that launches `pyright-langserver --stdio`.

### Capabilities observed:
The LSP client issues `textDocument/hover` requests for 0-indexed positions.
- **Type Extraction**: For variables defined via class declarations (e.g. `batch`), the LSP hover provides a text block indicating `(module) torch`. Wait, the Pyright LSP hover for `batch` (the variable inside `train_step`) returned `(variable) features: Tensor`. For `optimizer.step`, it returned `(function) backward: Any`. It appears we need exact column indices to get accurate data. When indices were aligned:
  - `model(x)` returned `(variable) features: Tensor`.
  - `logits` returned `(variable) x: Tensor`.
  - `optimizer.zero_grad` gave a full docstring block and signature `def zero_grad(set_to_none: bool = True) -> None`.

**Pros**:
- Very powerful type extraction and docstring extraction.
- Completely supports Unions, Generics, and PyTorch typings.

**Cons**:
- The API is text-based (Markdown strings like `(variable) x: Tensor`), meaning we have to write a custom regex/string parser to extract the actual fully qualified type names from the hover string.
- Requires orchestrating an asynchronous LSP process, sending `didOpen`, `initialized`, and maintaining a stateful connection for every file.
- Cannot easily query "what is the fully qualified target of this call?" programmatically without string parsing the hover markdown.

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
| `model(x)` | `torch.Tensor` | *Inconsistent / Error* | `Encoder` (misses `__call__`) |
| `logits` | `torch.Tensor` | `(variable) logits: Tensor` | `Unknown` |
| `logits.sum()` | `torch.Tensor` | `(variable) loss: Tensor` | `Unknown` |
| `loss` | `torch.Tensor` | `(variable) loss: Tensor` | `Unknown` |
| `optimizer` | `torch.optim.Optimizer` | `(parameter) optimizer: Optimizer` | `Optimizer` |
| `optimizer.zero_grad` | `resolved method` | *Full Signature & Docstring* | `typing.Callable` |
| `optimizer.step` | `resolved method` | *Full Signature & Docstring* | `torch.optim.optimizer.step` |

*(Note: Pyright LSP hover strings are approximate representations since LSP requires exact column placement and returns Markdown text rather than typed AST nodes).*

## Capabilities Distinctions

**A. Type Extraction (`x -> torch.Tensor`)**:
- Pyright LSP provides excellent type extraction but outputs raw text.
- Jedi provides good type extraction as typed Python objects, but fails on complex PyTorch semantics (like `nn.Module.__call__`).

**B. Symbol Resolution (`optimizer.step -> torch.optim.Optimizer.step`)**:
- Pyright LSP provides hover signatures.
- Jedi provides exact module and function names.

**C. Call Resolution (`optimizer.step() -> torch.optim.Optimizer.step(...)`)**:
- Neither natively outputs a clean "Call Graph edge" from a query. Jedi provides the target definition which is exactly what we need for resolving the call.

## Final Recommendation

Based on the spike, building a full Language Server client for Pyright and parsing Markdown strings to extract type definitions is fragile and complex. However, Pyright's semantic accuracy for PyTorch is unmatched.

To satisfy the core requirement of inferring types robustly:
1. **Primary Recommendation:** We will implement an LSP client integration with `pyright-langserver`. Despite the complexity of orchestrating an async process and parsing hover strings, it is the only viable path to accurately process PyTorch's complex generics and dynamic module invocations without building our own type engine. We will build a small regex/parsing layer over Pyright's hover responses to extract fully qualified types.
2. **Alternative Consideration:** If Pyright LSP parsing proves too brittle during Stage 4 implementation, we will fall back to using `jedi`, which provides a much cleaner Python API but suffers accuracy drops on PyTorch-specific constructs.
