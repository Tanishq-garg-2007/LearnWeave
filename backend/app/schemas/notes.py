from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class NoteChunkResponse(BaseModel):
    id: str
    chunk_index: int
    text_content: str
    page_number: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NoteResponse(BaseModel):
    id: str
    title: str
    subject: str
    tags: List[str] = Field(default_factory=list)
    file_type: str
    file_size: int
    visibility: str
    processing_status: str
    chunk_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NoteDetailResponse(BaseModel):
    id: str
    title: str
    subject: str
    tags: List[str] = Field(default_factory=list)
    file_type: str
    file_size: int
    visibility: str
    processing_status: str
    raw_content: Optional[str] = None
    chunks: List[NoteChunkResponse] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NoteUploadResponse(BaseModel):
    id: str
    title: str
    subject: str
    chunks_created: int
    processing_status: str
    message: str
