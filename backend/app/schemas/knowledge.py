from typing import Annotated, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_serializer, model_validator
from app.services.preview_limits import MAX_FILES, check_chunk_settings

PROCESSING_FAILURE = "Document processing failed; check the file and try again."

class KnowledgeBaseBase(BaseModel):
    name: str
    description: Optional[str] = None

class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass

class KnowledgeBaseUpdate(KnowledgeBaseBase):
    pass

class DocumentBase(BaseModel):
    file_name: str
    file_path: str
    file_hash: str
    file_size: int
    content_type: str

class DocumentCreate(DocumentBase):
    knowledge_base_id: int

class DocumentUploadBase(BaseModel):
    file_name: str
    file_hash: str
    file_size: int
    content_type: str
    temp_path: str
    status: str = "pending"
    error_message: Optional[str] = None

class DocumentUploadCreate(DocumentUploadBase):
    knowledge_base_id: int

class DocumentUploadResponse(DocumentUploadBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ProcessingTaskBase(BaseModel):
    status: str
    error_message: Optional[str] = None

    @field_serializer("error_message")
    def safe_error_message(self, value):
        # Historical task records may contain raw storage/parser/provider errors.
        return PROCESSING_FAILURE if value else None

class ProcessingTaskCreate(ProcessingTaskBase):
    document_id: int
    knowledge_base_id: int

class ProcessingTask(ProcessingTaskBase):
    id: int
    document_id: int
    knowledge_base_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DocumentResponse(DocumentBase):
    id: int
    knowledge_base_id: int
    created_at: datetime
    updated_at: datetime
    processing_tasks: List[ProcessingTask] = []

    class Config:
        from_attributes = True

class KnowledgeBaseResponse(KnowledgeBaseBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    documents: List[DocumentResponse] = []

    class Config:
        from_attributes = True

class PreviewRequest(BaseModel):
    document_ids: List[Annotated[int, Field(strict=True, gt=0)]] = Field(min_length=1, max_length=MAX_FILES)
    chunk_size: int = Field(default=1000, strict=True, ge=256, le=4000)
    chunk_overlap: int = Field(default=200, strict=True, ge=0)

    @model_validator(mode="after")
    def bounded_preview(self):
        if len(self.document_ids) != len(set(self.document_ids)):
            raise ValueError("Select distinct documents")
        check_chunk_settings(self.chunk_size, self.chunk_overlap)
        return self
