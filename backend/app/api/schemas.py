from pydantic import BaseModel
from typing import List, Optional

class SourceCitation(BaseModel):
    source: str
    page: Optional[str] = None
    chunk_text: str
    relevance_score: float

class QueryResponse(BaseModel):
    answer: str
    citations: List[SourceCitation]

class DocumentResponse(BaseModel):
    id: str
    filename: str
    status: str

class MessageBase(BaseModel):
    role: str
    content: str
    citations: Optional[List[SourceCitation]] = None

class ConversationResponse(BaseModel):
    id: str
    messages: List[MessageBase]
