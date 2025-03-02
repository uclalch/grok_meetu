from pydantic import BaseModel
from typing import List, Optional

# Define request and response models
class RecommendRequest(BaseModel):
    user_id: str

class RecommendationItem(BaseModel):
    chatroom_id: str
    predicted_score: float
    model_version: str
    prediction_timestamp: str

class RecommendResponse(BaseModel):
    recommendations: List[RecommendationItem]
    model_info: dict

class TrainResponse(BaseModel):
    message: str

class ModelInfo(BaseModel):
    status: str
    version: str
    parameters: dict
    metrics: Optional[dict] = None

class ModelListResponse(BaseModel):
    models: List[ModelInfo]

class ModelActivateResponse(BaseModel):
    message: str
    activated_version: str

