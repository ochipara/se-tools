import subprocess
import json
import ast
import tempfile
import os

sample_code = """
import typing
from typing import List, Optional

class Classifier:
    def __init__(self):
        pass

class TrainingBatch:
    def __init__(self, features: List[float]):
        self.features = features

def train_step(model: Classifier, batch: TrainingBatch) -> float:
    x = batch.features
    return 1.0
"""

def extract_ast_types(source: str):
    tree = ast.parse(source)
    types = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for arg in node.args.args:
                if arg.annotation:
                    types[f"{node.name}.{arg.arg}"] = ast.unparse(arg.annotation)
            if node.returns:
                types[f"{node.name}.return"] = ast.unparse(node.returns)
    return types

def extract_pyright_types(source: str):
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        f.write(source.encode("utf-8"))
        filepath = f.name

    try:
        # Run Pyright on the file
        # Pyright has an internal hover mechanism, but programmatic type extraction is tricky.
        # We can try using --outputjson to get diagnostics, but not arbitrary types.
        # Another approach is to generate a pyrightconfig.json, or use `pyright --verifytypes`
        result = subprocess.run(
            ["pyright", filepath, "--outputjson"],
            capture_output=True,
            text=True
        )
        data = json.loads(result.stdout)
        return data
    finally:
        os.remove(filepath)

if __name__ == "__main__":
    print("--- AST Types ---")
    ast_types = extract_ast_types(sample_code)
    for k, v in ast_types.items():
        print(f"{k}: {v}")

    print("\n--- Pyright Diagnostics ---")
    pyright_data = extract_pyright_types(sample_code)
    print(json.dumps(pyright_data.get("generalDiagnostics", []), indent=2))
