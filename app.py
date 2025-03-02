# app.py - User-facing API for recommendations
from fastapi import FastAPI, HTTPException
import logging
from api.api_models import RecommendRequest, RecommendResponse
from recommendation.recommend import RecommendationSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Grok MeetU Recommendation API")

# Initialize system
rec_sys = RecommendationSystem()

@app.get("/")
async def read_root():
    return {"message": "Welcome to Grok MeetU Recommendation API"}

@app.post("/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest):
    """Get chatroom recommendations for a user"""
    try:
        # Always check for latest model
        current_path = rec_sys._get_latest_model_path()
        if current_path.exists():
            latest_version = rec_sys._load_version_info(current_path).get('timestamp')
            current_version = rec_sys.last_loaded_version
            
            logger.info(f"Latest model version: {latest_version}")
            logger.info(f"Currently loaded version: {current_version}")
            
            if current_version != latest_version:
                logger.info(f"Model versions differ ({current_version} vs {latest_version})")
                logger.info("Reloading latest model...")
                rec_sys.load_model()
        
        recommendations = rec_sys.get_recommendations(
            request.user_id,
            motivation_threshold=0.1,
            pressure_threshold=0.5,
            required_credit_level="partial"
        )
        
        return {
            "recommendations": recommendations,
            "model_info": rec_sys._load_version_info(current_path)
        }

    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/model-info")
async def get_model_info():
    """Get current model information"""
    try:
        model_path = rec_sys._get_latest_model_path()
        version_info = rec_sys._load_version_info(model_path)
        return {
            "status": "active",
            "version": version_info['timestamp'],
            "parameters": version_info['parameters']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
