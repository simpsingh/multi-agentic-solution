"""
DDL Generation Pydantic Schemas
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DDLGenerationRequest(BaseModel):
    """Request schema for DDL generation"""

    metadata_id: str
    user_prompt: str
    thread_id: Optional[str] = None


class DDLGenerationResponse(BaseModel):
    """Response schema for DDL generation"""

    id: int
    metadata_id: int
    thread_id: str
    ddl_statement: str
    ddl_file_path: Optional[str]
    validation_score: Optional[float]
    accuracy_score: Optional[float]
    validation_details: Optional[dict]
    feedback_iteration: int
    user_feedback: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ValidationScores(BaseModel):
    """Validation scores schema"""

    field_coverage: float
    data_type_match: float
    length_match: float
    nullability_match: float
    overall_accuracy: float
