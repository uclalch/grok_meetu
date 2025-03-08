# app.py - User-facing API for recommendations
from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
import logging
import sys
import os
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.recommendation.recommend import get_rec_sys

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.api.api_models import (
    CreateRecommendationRequest,
    RecommendationResponse,
    RecommendationFilter,
    BatchRecommendationRequest,
    BatchRecommendationResponse,
    UpdateRecommendationRequest
)
from backend.core.config import load_config
from datetime import datetime

# Configure logging at the top of the file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Grok MeetU Recommendation API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React app origin
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize system
rec_sys = get_rec_sys()

@app.get("/")
async def read_root():
    return {"message": "Welcome to Grok MeetU Recommendation API"}

# curl -X POST 'http://localhost:8000/recommendations' -H 'Content-Type: application/json' -d '{"user_id": "U2","filters":{"top_k":3,"min_score":0.8,"topics":["tech","gaming"], "min_vibe_score":4}}'

@app.post("/recommendations", response_model=RecommendationResponse)
async def create_recommendations(request: CreateRecommendationRequest):
    """Create recommendations for a user with optional filters"""
    logger.info(f"Received recommendation request for user: {request.user_id}")
    try:
        # Validate user exists
        if not rec_sys._validate_user(request.user_id):
            logger.error(f"User {request.user_id} not found")
            raise HTTPException(
                status_code=404,
                detail=f"User {request.user_id} not found"
            )
        
        # Check if model exists and is trained
        logger.info("Checking model status...")
        if rec_sys.model is None:
            logger.error("No model loaded")
            try:
                logger.info("Attempting to load model...")
                rec_sys.load_model()
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                raise HTTPException(
                    status_code=400,
                    detail="No trained model available. Please train a model first using the admin API: curl -X POST 'http://localhost:8001/train' -H 'Content-Type: application/json' -d '{""test_size"": 0.2, ""force"": true}''"
                )
        
        # Check model version and reload if needed
        current_path = rec_sys._get_latest_model_path()
        if current_path.exists():
            latest_version = rec_sys._load_version_info(current_path).get('timestamp')
            current_version = rec_sys.last_loaded_version
            
            if current_version != latest_version:
                logger.info(f"Model versions differ ({current_version} vs {latest_version})")
                logger.info("Reloading latest model...")
                rec_sys.load_model()
        
        # Check if recommendations already exist
        if request.user_id in rec_sys._recommendation_cache:
            raise HTTPException(
                status_code=409,
                detail=f"Recommendations already exist for user {request.user_id}. Use PUT to update."
            )
        
        # Generate new recommendations
        try:
            recommendations = rec_sys.get_recommendations(
                request.user_id,
                filters=request.filters,
                thresholds=request.thresholds
            )
        except ValueError as e:
            # Convert ValueError to HTTPException
            raise HTTPException(status_code=400, detail=str(e))
        
        # Store in cache
        rec_sys._recommendation_cache[request.user_id] = recommendations
        
        model_info = rec_sys._load_version_info(current_path)
        
        return RecommendationResponse(
            user_id=request.user_id,
            recommendations=recommendations,
            filters_applied=request.filters,
            model_info=model_info,
            cache_info={
                "source": "new",
                "timestamp": datetime.now()
            }
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error generating recommendations: {e}")
        # Convert to HTTPException with original error message
        if "No trained model available" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        elif "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail=str(e))

# curl 'http://localhost:8000/recommendations/U2'

@app.get("/recommendations/{user_id}", response_model=RecommendationResponse)
async def get_recommendations(
    user_id: str,
    filters: Optional[RecommendationFilter] = None
):
    """Get existing recommendations for a user"""
    try:
        # Only get from cache, don't generate new
        if user_id not in rec_sys._recommendation_cache:
            raise HTTPException(
                status_code=404,
                detail=f"No recommendations found for user {user_id}. Create them first using POST."
            )
        
        cached = rec_sys.get_cached_recommendations(user_id, filters=filters)
        if not cached:
            raise HTTPException(
                status_code=404,
                detail=f"No recommendations match the filters for user {user_id}"
            )
            
        model_info = rec_sys._load_version_info(rec_sys._get_latest_model_path())
        return RecommendationResponse(
            user_id=user_id,
            recommendations=cached,
            filters_applied=filters,
            model_info=model_info,
            cache_info={"source": "cache", "timestamp": datetime.now()}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# curl -X DELETE 'http://localhost:8000/recommendations/U2'

@app.delete("/recommendations/{user_id}")
async def delete_recommendations(user_id: str):
    """Delete recommendations for a user"""
    try:
        # Validate user exists
        if not rec_sys._validate_user(user_id):
            raise HTTPException(
                status_code=404,
                detail=f"User {user_id} not found"
            )
        
        # Check cache
        if user_id not in rec_sys._recommendation_cache:
            raise HTTPException(
                status_code=404,
                detail=f"No recommendations found for user {user_id}"
            )
        
        # Clear from cache
        rec_sys.clear_recommendations(user_id)
        
        return {"message": f"Recommendations cleared for user {user_id}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# curl -X POST 'http://localhost:8000/recommendations/batch' -H 'Content-Type: application/json' -d '{"user_ids":["U2","U3"]}'

@app.post("/recommendations/batch", response_model=BatchRecommendationResponse)
async def batch_recommend(request: BatchRecommendationRequest):
    """Create recommendations for multiple users"""
    try:
        responses = []
        for user_id in request.user_ids:
            recommendations = await create_recommendations(
                CreateRecommendationRequest(user_id=user_id)
            )
            responses.append(recommendations)
        return BatchRecommendationResponse(
            results=responses,
            failed_users=[]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# curl 'http://localhost:8000/model-info'

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
# curl -X PUT 'http://localhost:8000/recommendations/U2' -H 'Content-Type: application/json' -d '{"user_id": "U2","thresholds": {"motivation": 0.2,"pressure": 0.6,"credit_level": "partial"}}'

@app.put("/recommendations/{user_id}", response_model=RecommendationResponse)
async def update_recommendations(
    user_id: str,
    request: UpdateRecommendationRequest
):
    """Update recommendations for a user"""
    try:
        # Validate user exists
        if not rec_sys._validate_user(user_id):
            raise HTTPException(
                status_code=404,
                detail=f"User {user_id} not found"
            )
        
        # Check if recommendations exist
        if user_id not in rec_sys._recommendation_cache:
            raise HTTPException(
                status_code=404,
                detail=f"No recommendations found for user {user_id}. Create them first using POST."
            )
        
        # Generate new recommendations
        recommendations = rec_sys.get_recommendations(
            user_id,
            filters=request.filters,
            thresholds=request.thresholds
        )
        
        # Update cache
        rec_sys._recommendation_cache[user_id] = recommendations
        
        # Get model info
        model_path = rec_sys._get_latest_model_path()
        model_info = rec_sys._load_version_info(model_path)
        
        return RecommendationResponse(
            user_id=user_id,
            recommendations=recommendations,
            filters_applied=request.filters,
            model_info=model_info,
            cache_info={
                "source": "updated",
                "timestamp": datetime.now()
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
