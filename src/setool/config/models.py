from typing import List, Optional
from pydantic import BaseModel, Field

class EntryPoint(BaseModel):
    name: str
    target: str

class SetoolConfig(BaseModel):
    project_root: str = "."
    entry_points: List[EntryPoint] = Field(default_factory=list)
    include: List[str] = Field(default_factory=list)
    exclude: List[str] = Field(default_factory=lambda: ["tests/**", ".venv/**", "**/__pycache__/**"])
    max_call_depth: int = 15
