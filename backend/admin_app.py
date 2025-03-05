# admin_app.py - Admin API for model management
from fastapi import FastAPI, HTTPException
import logging
from .api.api_models import (
    TrainRequest, TrainResponse,
    ModelListResponse, ModelActivateResponse,
    ModelActivateRequest, ModelDeleteResponse
)
from backend.recommendation.recommend import get_rec_sys
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

admin_app = FastAPI(title="Grok MeetU Admin API")

# Initialize system
rec_sys = get_rec_sys()

class TrainModelRequest(BaseModel):
    test_size: float = 0.2
    force: bool = False

class ModelStatusResponse(BaseModel):
    status: str
    current_version: Optional[str] = None
    last_trained: Optional[str] = None
    metrics: Optional[dict] = None

@admin_app.get("/")
async def read_root():
    return {"message": "Welcome to Grok MeetU Admin API"}

@admin_app.post("/train")
async def train_model(request: TrainModelRequest):
    """Train a new model with optional parameters"""
    try:
        # Direct synchronous call instead of background task
        predictions = rec_sys.train_model(
            test_size=request.test_size,
            force=request.force
        )
        
        # Get the latest model info
        model_path = rec_sys._get_latest_model_path()
        version_info = rec_sys._load_version_info(model_path)
        
        return {
            "status": "success",
            "message": "Model trained successfully",
            "predictions": len(predictions),
            "version_info": version_info
        }
    except ValueError as e:
        # Model exists error
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Training error: {str(e)}")
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

@admin_app.get("/model/status", response_model=ModelStatusResponse)
async def get_model_status():
    """Get current model status"""
    try:
        model_path = rec_sys._get_latest_model_path()
        if not model_path.exists():
            return ModelStatusResponse(
                status="not_trained",
                message="No trained model found"
            )
        
        version_info = rec_sys._load_version_info(model_path)
        return ModelStatusResponse(
            status="ready",
            current_version=version_info.get('timestamp'),
            last_trained=version_info.get('timestamp'),
            metrics=version_info.get('metrics')
        )
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 