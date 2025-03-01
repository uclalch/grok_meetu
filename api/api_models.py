from pydantic import BaseModel

# Define request and response models
class RecommendRequest(BaseModel):
    user_id: str

class RecommendationItem(BaseModel):
    chatroom_id: str
    predicted_score: float
    model_version: str
    prediction_timestamp: str

class RecommendResponse(BaseModel):
    recommendations: list[RecommendationItem]
    model_info: dict

class TrainResponse(BaseModel):
    message: str

