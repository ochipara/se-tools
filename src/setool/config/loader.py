import json
import os
from .models import SetoolConfig

def load_config(filepath: str) -> SetoolConfig:
    if not os.path.exists(filepath):
        if filepath == ".":
            return SetoolConfig()
        raise FileNotFoundError(f"Configuration file not found: {filepath}")

    if os.path.isdir(filepath):
        filepath = os.path.join(filepath, "setool.json")
        if not os.path.exists(filepath):
            return SetoolConfig(project_root=os.path.dirname(filepath))

    with open(filepath, "r") as f:
        data = json.load(f)

    return SetoolConfig(**data)
