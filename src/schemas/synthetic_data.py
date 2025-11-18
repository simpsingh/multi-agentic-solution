"""
Synthetic Data Generation Pydantic Schemas
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class SyntheticDataRequest(BaseModel):
    """Request schema for synthetic data generation"""

    metadata_id: str
    ddl_id: Optional[int] = None
    user_prompt: str
    thread_id: Optional[str] = None
    num_rows: int = 10
    data_type: Optional[str] = "happy_path"  # 'edge', 'boundary', 'happy_path', 'negative'


class SyntheticDataResponse(BaseModel):
    """Response schema for synthetic data generation"""

    id: int
    metadata_id: int
    ddl_id: Optional[int]
    thread_id: str
    file_path: Optional[str]
    synthetic_json: dict
    row_count: Optional[int]
    data_type: Optional[str]
    validation_score: Optional[float]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalRequest(BaseModel):
    """Request schema for approval"""

    generation_id: int
    generation_type: str  # 'ddl' or 'synthetic_data'
    approved: bool
    feedback: Optional[str] = None
