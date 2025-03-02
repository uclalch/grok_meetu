from dotenv import load_dotenv
import os
from pathlib import Path

def load_config():
    """Load configuration from environment variables"""
    load_dotenv()  # Load .env file if it exists
    
    # Get the project root directory
    root_dir = Path(__file__).parent.parent.parent
    
    return {
        "SCYLLA_HOSTS": os.getenv("SCYLLA_HOSTS", "localhost").split(","),
        "SCYLLA_PORT": int(os.getenv("SCYLLA_PORT", 9042)),
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "MODEL_DIR": os.getenv("MODEL_DIR", str(root_dir / "backend/recommendation/models")),
        "DB_KEYSPACE": os.getenv("DB_KEYSPACE", "grok_meetu"),
        "ENVIRONMENT": os.getenv("ENVIRONMENT", "development")
    }

# Default configuration
default_config = {
    "SCYLLA_HOSTS": ["localhost"],
    "SCYLLA_PORT": 9042,
    "LOG_LEVEL": "INFO",
    "MODEL_DIR": str(Path(__file__).parent.parent / "recommendation/models"),
    "DB_KEYSPACE": "grok_meetu",
    "ENVIRONMENT": "development"
}

# Load configuration once at module level
config = load_config() 