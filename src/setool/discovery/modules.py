import os
from typing import Optional, List, Tuple

def filepath_to_module(filepath: str, project_root: str) -> str:
    """Converts an absolute filepath to a Python module name."""
    rel_path = os.path.relpath(filepath, project_root)
    if rel_path.endswith(".py"):
        rel_path = rel_path[:-3]
    parts = rel_path.split(os.sep)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)

def get_package_hierarchy(module_name: str) -> List[Tuple[str, str]]:
    """Returns a list of (package_id, name) tuples for the hierarchy of the module."""
    parts = module_name.split(".")
    packages = []

    # If the module is a root module without a package, this will not produce packages
    if len(parts) > 1:
        for i in range(1, len(parts)):
            pkg_id = ".".join(parts[:i])
            packages.append((pkg_id, parts[i-1]))
    return packages
