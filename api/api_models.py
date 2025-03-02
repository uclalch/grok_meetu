from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Base recommendation models
class RecommendationItem(BaseModel):
    """Individual recommendation"""
    chatroom_id: str
    predicted_score: float
    motivation_match: float
    pressure_compatibility: float
    credit_level: str
    timestamp: datetime = Field(default_factory=datetime.now)

class RecommendationFilter(BaseModel):
    """Filters for recommendation retrieval"""
    top_k: Optional[int] = Field(5, description="Number of recommendations to return")
    min_score: Optional[float] = Field(0.0, description="Minimum prediction score")
    topics: Optional[List[str]] = Field(None, description="Filter by topics")
    min_vibe_score: Optional[int] = Field(None, description="Minimum chatroom vibe score")
    max_pressure: Optional[int] = Field(None, description="Maximum pressure level")

# Request models
class CreateRecommendationRequest(BaseModel):
    """Request for creating recommendations"""
    user_id: str
    filters: Optional[RecommendationFilter] = None
    thresholds: Optional[dict] = Field(
        default={
            "motivation": 0.1,
            "pressure": 0.5,
            "credit_level": "partial"
        },
        description="Customizable thresholds for recommendation generation"
    )

class BatchRecommendationRequest(BaseModel):
    """Request for batch recommendations"""
    user_ids: List[str]
    filters: Optional[RecommendationFilter] = None

# Response models
class RecommendationResponse(BaseModel):
    """Standard recommendation response"""
    user_id: str
    recommendations: List[RecommendationItem]
    filters_applied: Optional[RecommendationFilter] = None
    model_info: dict
    cache_info: Optional[dict] = None  # Cache status, timestamp, etc.

class BatchRecommendationResponse(BaseModel):
    """Response for batch recommendations"""
    results: List[RecommendationResponse]
    failed_users: Optional[List[dict]] = None  # Track any failures

class DeleteResponse(BaseModel):
    """Response for DELETE operations"""
    user_id: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)

# Model info models (moved from admin models)
class ModelInfo(BaseModel):
    """Model metadata"""
    version: str
    timestamp: datetime
    parameters: dict
    metrics: Optional[dict] = None
    status: str = "active"

class UpdateRecommendationRequest(BaseModel):
    """Request for updating recommendations"""
    filters: Optional[RecommendationFilter] = None
    thresholds: Optional[dict] = Field(
        default=None,
        description="Customizable thresholds for recommendation generation"
    )

