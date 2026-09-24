import json
import os
from .models import SetoolConfig

def load_config(filepath: str) -> SetoolConfig:
    if not os.path.exists(filepath):
        if filepath == ".":
            return SetoolConfig()
        raise FileNotFoundError(f"Configuration file not found: {filepath}")

    config_file = filepath
    if os.path.isdir(filepath):
        for candidate in ["setool.json", "config.json"]:
            candidate_path = os.path.join(filepath, candidate)
            if os.path.exists(candidate_path):
                config_file = candidate_path
                break
        else:
            if filepath == ".":
                return SetoolConfig()
            raise FileNotFoundError(
                f"No configuration file ('setool.json' or 'config.json') found in directory: {filepath}"
            )

    with open(config_file, "r") as f:
        data = json.load(f)

    config = SetoolConfig(**data)
    if not os.path.isabs(config.project_root):
        config_dir = os.path.dirname(os.path.abspath(config_file))
        config.project_root = os.path.normpath(os.path.join(config_dir, config.project_root))

    return config
