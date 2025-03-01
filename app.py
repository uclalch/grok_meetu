from fastapi import FastAPI, HTTPException, BackgroundTasks
import logging
from api.api_models import RecommendRequest, RecommendResponse, TrainResponse
from recommendation.recommend import RecommendationSystem   
import pandas as pd
import os
import datetime
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Define a simple endpoint
@app.get("/")
def read_root():
    return {"message": "Hello, welcome to the Recommendation API!"}

# Initialize system with ScyllaDB connection
rec_sys = RecommendationSystem()  # Uses default localhost:9042

# Define the /recommend endpoint
@app.post("/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest):
    try:
        # Always check for latest model
        current_path = rec_sys._get_latest_model_path()
        if current_path.exists():
            latest_version = rec_sys._load_version_info(current_path).get('timestamp')
            current_version = rec_sys.last_loaded_version
            
            logger.info(f"Latest model version: {latest_version}")
            logger.info(f"Currently loaded version: {current_version}")
            
            # Force reload if versions don't match or no model loaded
            if current_version != latest_version:
                logger.info(f"Model versions differ ({current_version} vs {latest_version})")
                logger.info("Reloading latest model...")
                rec_sys.load_model()
            else:
                logger.info("Using current model (versions match)")
        else:
            logger.warning("No model found, training new one...")
            rec_sys.train_model(force=True)
        
        user_id = request.user_id
        if not user_id:
            logger.warning("Missing user_id in request")
            raise HTTPException(status_code=400, detail="Missing user_id")

        # Use less strict thresholds
        recommendations = rec_sys.get_recommendations(
            user_id,
            motivation_threshold=0.1,  # Lower this if needed
            pressure_threshold=0.5,    # Lower this if needed
            required_credit_level="partial"  # Or change to match user's level
        )
        if not recommendations:
            logger.info(f"No recommendations found for user_id: {user_id}")
            return {
                "recommendations": [],
                "model_info": rec_sys._load_version_info(rec_sys._get_latest_model_path())
            }

        # Get current model info
        model_path = rec_sys._get_latest_model_path()
        model_info = rec_sys._load_version_info(model_path)
        current_time = datetime.datetime.now().isoformat()

        # Format the response with all required fields
        response = {
            "recommendations": [
                {
                    "chatroom_id": chatroom_id,
                    "predicted_score": round(float(score), 2),
                    "model_version": model_info['timestamp'],
                    "prediction_timestamp": current_time
                }
                for chatroom_id, score in recommendations
            ],
            "model_info": model_info
        }
        
        logger.info(f"Returning {len(recommendations)} recommendations for user_id: {user_id}")
        return response

    except ValueError as ve:
        logger.error(f"Error generating recommendations: {ve}")
        raise HTTPException(status_code=500, detail=str(ve))
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/train", response_model=TrainResponse)
async def train_model(background_tasks: BackgroundTasks, force: bool = False):
    """Admin endpoint to train a new model"""
    try:
        # Train in background to not block the API
        background_tasks.add_task(rec_sys.train_model, force=force)
        return {"message": "Model training started in background"}
    except ValueError as ve:
        # This is the warning about existing model
        return {"message": str(ve)}
    except Exception as e:
        logger.error(f"Error training model: {e}")
        raise HTTPException(status_code=500, detail="Training error")

@app.get("/model-info")
async def get_model_info():
    """Get current model information"""
    try:
        model_path = rec_sys._get_latest_model_path()
        if not model_path.exists():
            return {"status": "No model found"}
        
        version_info = rec_sys._load_version_info(model_path)
        return {
            "status": "active",
            "version": version_info['timestamp'],
            "path": str(model_path),
            "parameters": version_info['parameters']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update-model")
async def update_model():
    """Force model version update and reload"""
    try:
        if rec_sys._update_model_version():
            return {"message": "Model version updated and reloaded", 
                   "version": rec_sys._get_model_version()}
        else:
            raise HTTPException(status_code=404, detail="No model found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Run the app (this is just for reference; you'll use Uvicorn to run it)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
