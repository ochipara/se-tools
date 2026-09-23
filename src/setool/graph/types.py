from pydantic import BaseModel, Field
from typing import List, Optional

class PythonType(BaseModel):
    name: str
    fully_qualified_name: Optional[str] = None
    kind: str = "Any"
    generic_arguments: List['PythonType'] = Field(default_factory=list)
    union_members: List['PythonType'] = Field(default_factory=list)
    provenance: Optional[str] = None
