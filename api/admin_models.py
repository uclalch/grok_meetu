from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class TrainRequest(BaseModel):
    """Request for model training"""
    force: bool = False
    test_size: float = 0.2
    parameters: Optional[dict] = None

class TrainResponse(BaseModel):
    """Response for model training"""
    message: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ModelListResponse(BaseModel):
    """Response for listing models"""
    models: List[dict]  # List of model versions and metadata
    total_count: int
    active_version: str

class ModelActivateRequest(BaseModel):
    """Request to activate a specific model version"""
    version: str
    reason: Optional[str] = None

class ModelActivateResponse(BaseModel):
    """Response for model activation"""
    message: str
    activated_version: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ModelDeleteResponse(BaseModel):
    """Response for model deletion"""
    message: str
    deleted_version: str
    timestamp: datetime = Field(default_factory=datetime.now) 