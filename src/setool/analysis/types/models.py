from typing import Optional, Any
from pydantic import BaseModel
from ...graph.nodes import Location

class SourcePosition(BaseModel):
    filepath: str
    line: int
    column: int

class TypeResult(BaseModel):
    type_name: str
    provenance: str

class SymbolResult(BaseModel):
    symbol_id: str
    provenance: str

class SemanticProvider:
    """Protocol for semantic providers (AST, Jedi, Pyright)."""
    def type_at(self, location: SourcePosition) -> Optional[TypeResult]:
        raise NotImplementedError
    def symbol_at(self, location: SourcePosition) -> Optional[SymbolResult]:
        raise NotImplementedError
