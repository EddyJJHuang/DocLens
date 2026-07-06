from pydantic import BaseModel
from typing import Any, Dict, List, Optional

class SourceCitation(BaseModel):
    source: str
    page: Optional[str] = None
    chunk_text: str
    relevance_score: float

class DocumentResponse(BaseModel):
    id: str
    filename: str
    status: str

class SqlPayload(BaseModel):
    sql: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    repaired: bool = False

class MessageBase(BaseModel):
    role: str
    content: str
    citations: Optional[List[SourceCitation]] = None
    route: Optional[str] = None            # structured | unstructured | hybrid
    sql: Optional[SqlPayload] = None

class SqlQueryResponse(BaseModel):
    answer: str
    sql: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    repaired: bool = False
    error: Optional[str] = None
