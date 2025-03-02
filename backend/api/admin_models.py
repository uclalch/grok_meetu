# admin_app.py - Admin API for model management
from fastapi import FastAPI, HTTPException, BackgroundTasks
import logging
from .api_models import (
    TrainRequest, TrainResponse,
    ModelListResponse, ModelActivateResponse,
    ModelActivateRequest, ModelDeleteResponse
)
from ..recommendation.recommend import RecommendationSystem
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

admin_app = FastAPI(title="Grok MeetU Admin API")

# Initialize system
rec_sys = RecommendationSystem()

@admin_app.get("/")
async def read_root():
    return {"message": "Welcome to Grok MeetU Admin API"}

@admin_app.post("/train", response_model=TrainResponse)
async def train_model(request: TrainRequest, background_tasks: BackgroundTasks):
    """Train a new recommendation model"""
    try:
        background_tasks.add_task(
            rec_sys.train_model,
            force=request.force,
            test_size=request.test_size
        )
        return TrainResponse(
            message="Model training started in background",
            version=datetime.now().strftime("%Y%m%d"),
        )
    except Exception as e:
        logger.error(f"Error training model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_app.get("/models", response_model=ModelListResponse)
async def list_models():
    """List all available models"""
    try:
        models = rec_sys.list_models()  # You'll need to implement this
        return ModelListResponse(
            models=models,
            total_count=len(models),
            active_version=rec_sys.last_loaded_version or "none"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@admin_app.post("/models/{version}/activate", response_model=ModelActivateResponse)
async def activate_model(version: str, request: ModelActivateRequest):
    """Activate a specific model version"""
    try:
        rec_sys.activate_model(version)  # You'll need to implement this
        return ModelActivateResponse(
            message=f"Model version {version} activated",
            activated_version=version
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@admin_app.delete("/models/{version}", response_model=ModelDeleteResponse)
async def delete_model(version: str):
    """Delete a specific model version"""
    try:
        rec_sys.delete_model(version)  # You'll need to implement this
        return ModelDeleteResponse(
            message=f"Model version {version} deleted",
            deleted_version=version
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 