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

# Initialize the recommendation system (do this once when the app starts)
users = pd.DataFrame({
    "user_id": ["U1", "U2", "U3"],
    "interests": [["travel", "tech"], ["art", "relax", "gaming"], ["gaming", "music"]],
    "level_of_pressure": [2, 1, 3],
    "platform_credit_score": [92, 68, 85]
})

chatrooms = pd.DataFrame({
    "chatroom_id": ["C1", "C2", "C3"],
    "name": ["AI Travel Planners", "Artistic Chill Zone", "Indie Game Devs"],
    "topics": [["AI", "travel"], ["art", "relax"], ["gaming", "coding"]],
    "vibe_score": [4, 5, 4]
})

interactions = pd.DataFrame({
    "user_id": ["U1", "U2", "U3"],
    "chatroom_id": ["C1", "C2", "C3"],
    "satisfaction_score": [5, 4, 5]
})

# Initialize system with data
rec_sys = RecommendationSystem(users=users, chatrooms=chatrooms, interactions=interactions)

# Define the /recommend endpoint
@app.post("/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest):
    try:
        # Load model if not loaded
        if rec_sys.model is None:
            rec_sys.load_model()
            
        user_id = request.user_id
        if not user_id:
            logger.warning("Missing user_id in request")
            raise HTTPException(status_code=400, detail="Missing user_id")

        # Get recommendations from your system
        recommendations = rec_sys.get_recommendations(user_id)
        if not recommendations:
            logger.info(f"No recommendations found for user_id: {user_id}")
            raise HTTPException(status_code=404, detail="No recommendations found")

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

# Run the app (this is just for reference; you'll use Uvicorn to run it)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
