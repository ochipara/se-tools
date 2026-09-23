from pydantic import BaseModel, Field
from typing import List, Dict
from .nodes import Node
from .edges import Edge

class ProgramGraph(BaseModel):
    schema_version: str = "1.0.0"
    nodes: Dict[str, Node] = Field(default_factory=dict)
    edges: List[Edge] = Field(default_factory=list)
