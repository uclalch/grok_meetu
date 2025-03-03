from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import pytest
import os
from pathlib import Path

# Check if running from correct directory
if Path.cwd().name != "grok_meetu":
    raise RuntimeError(
        "\n❌ Tests must be run from the grok_meetu directory!"
        "\n   Current directory: {}"
        "\n   Please run: cd grok_meetu && python -m pytest tests/test_api.py"
        .format(Path.cwd())
    )

from .test_config import TEST_CONFIG

# Mock Cassandra cluster and session
mock_session = Mock()
mock_cluster = Mock()
mock_cluster.connect.return_value = mock_session

@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock all external dependencies"""
    with patch('cassandra.cluster.Cluster', return_value=mock_cluster), \
         patch('backend.core.config.load_config', return_value=TEST_CONFIG):
        yield

@pytest.fixture
def test_app():
    """Create test app with mocked dependencies"""
    from ..backend.app import app
    return app

@pytest.fixture
def client(test_app):
    """Create test client"""
    return TestClient(test_app)

@pytest.fixture
def rec_sys(test_app):
    """Get recommendation system instance with mocked methods"""
    from ..backend.app import rec_sys
    # Mock the validate user method
    rec_sys._validate_user = Mock()
    return rec_sys

def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Grok MeetU Recommendation API"}

def test_create_recommendations_no_model(client, rec_sys):
    """Test creating recommendations when no model is trained"""
    # Ensure no model is loaded
    rec_sys.model = None
    rec_sys._validate_user.return_value = True
    
    response = client.post(
        "/recommendations",
        json={"user_id": "U2"}
    )
    assert response.status_code == 400
    assert "No trained model available" in response.json()["detail"]
    assert "curl -X POST 'http://localhost:8001/train'" in response.json()["detail"]

def test_create_recommendations_invalid_user(client, rec_sys):
    """Test creating recommendations for non-existent user"""
    rec_sys._validate_user.return_value = False
    
    response = client.post(
        "/recommendations",
        json={"user_id": "INVALID_USER"}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_create_recommendations_with_filters(client, rec_sys):
    """Test creating recommendations with filters"""
    rec_sys.model = None
    rec_sys._validate_user.return_value = True
    
    response = client.post(
        "/recommendations",
        json={
            "user_id": "U2",
            "filters": {
                "top_k": 3,
                "min_score": 0.8,
                "topics": ["tech", "gaming"],
                "min_vibe_score": 4
            }
        }
    )
    assert response.status_code == 400
    assert "No trained model available" in response.json()["detail"]

def test_delete_recommendations(client, rec_sys):
    """Test deleting recommendations"""
    rec_sys._validate_user.return_value = True
    rec_sys._recommendation_cache = {}
    
    response = client.delete("/recommendations/U2")
    assert response.status_code == 404  # Should fail if no recommendations exist 