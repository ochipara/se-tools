from pydantic import BaseModel, Field
from typing import Dict, Any, List
from enum import Enum
from .provenance import Provenance

class EdgeKind(str, Enum):
    CONTAINS = "CONTAINS"
    IMPORTS = "IMPORTS"
    INHERITS = "INHERITS"
    CALLS = "CALLS"
    INSTANTIATES = "INSTANTIATES"
    PASSES_VALUE = "PASSES_VALUE"
    RETURNS = "RETURNS"
    READS = "READS"
    WRITES = "WRITES"
    USES_API = "USES_API"
    DEPENDS_ON = "DEPENDS_ON"
    PROVIDED_BY = "PROVIDED_BY"
    DECLARES_DEPENDENCY = "DECLARES_DEPENDENCY"

class Edge(BaseModel):
    source: str
    target: str
    kind: EdgeKind
    provenance: List[Provenance] = Field(default_factory=list)
    properties: Dict[str, Any] = Field(default_factory=dict)
