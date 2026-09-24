import jedi
import os

filepath = os.path.abspath("tests/fixtures/type_spike_fixture.py")
with open(filepath, "r") as f:
    text = f.read()

script = jedi.Script(text, path=filepath)

positions = [
    ("batch", 19, 9),
    ("batch.features", 19, 15),
    ("x", 19, 4),
    ("model", 20, 14),
    ("model(x)", 20, 18),
    ("logits", 20, 4),
    ("logits.sum", 21, 14),
    ("loss", 21, 4),
    ("optimizer", 23, 5),
    ("optimizer.zero_grad", 23, 15),
    ("optimizer.step", 25, 15),
]

print("--- Jedi Infer Results ---")
for name, line, char in positions:
    try:
        inferences = script.infer(line, char)
        if inferences:
            types = ", ".join([f"{i.module_name}.{i.name}" if i.module_name else i.name for i in inferences])
            print(f"{name}: {types}")
        else:
            print(f"{name}: Unknown")
    except Exception as e:
        print(f"{name}: Error - {e}")
