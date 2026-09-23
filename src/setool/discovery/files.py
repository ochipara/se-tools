import os
import glob
from typing import List
from ..config.models import SetoolConfig

def discover_files(config: SetoolConfig) -> List[str]:
    root = os.path.abspath(config.project_root)
    discovered = []

    includes = config.include if config.include else ["**/*.py"]

    for pattern in includes:
        search_pattern = os.path.join(root, pattern)
        for filepath in glob.glob(search_pattern, recursive=True):
            if os.path.isfile(filepath) and filepath.endswith(".py"):
                # Basic exclusion logic
                excluded = False
                for ex_pattern in config.exclude:
                    if ex_pattern.strip("*") in filepath:
                        excluded = True
                        break
                if not excluded:
                    discovered.append(filepath)

    return list(set(discovered))
