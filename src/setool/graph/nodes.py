from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from .types import PythonType

class NodeKind(str, Enum):
    PACKAGE = "package"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    PYTORCH_MODULE = "pytorch_module"
    CALL_SITE = "call_site"
    VALUE = "value"
    EXTERNAL_API = "external_api"
    DISTRIBUTION = "distribution"

class Location(BaseModel):
    file: str
    line_start: int
    line_end: int
    col_start: Optional[int] = None
    col_end: Optional[int] = None

class Node(BaseModel):
    id: str
    kind: NodeKind
    name: str
    location: Optional[Location] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    python_type: Optional[PythonType] = None
