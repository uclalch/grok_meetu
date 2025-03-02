# admin_app.py - Admin API for model management
from fastapi import FastAPI, HTTPException, BackgroundTasks
import logging
from api.api_models import TrainResponse, ModelInfo, ModelListResponse, ModelActivateResponse
from recommendation.recommend import RecommendationSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

admin_app = FastAPI(title="Grok MeetU Admin API")

# Initialize system
rec_sys = RecommendationSystem()

@admin_app.get("/")
async def read_root():
    return {"message": "Welcome to Grok MeetU Admin API"}

@admin_app.post("/train", response_model=TrainResponse)
async def train_model(background_tasks: BackgroundTasks, force: bool = False):
    """Train a new recommendation model"""
    try:
        background_tasks.add_task(rec_sys.train_model, force=force)
        return {"message": "Model training started in background"}
    except Exception as e:
        logger.error(f"Error training model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_app.post("/models/{version}/activate")
async def activate_model(version: str):
    """Activate a specific model version"""
    try:
        # TODO: Implement model version activation
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@admin_app.get("/models")
async def list_models():
    """List all available models"""
    try:
        # TODO: Implement model listing
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@admin_app.delete("/models/{version}")
async def delete_model(version: str):
    """Delete a specific model version"""
    try:
        # TODO: Implement model deletion
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 