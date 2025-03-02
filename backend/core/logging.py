import logging
from core.config import load_config

def setup_logging():
    config = load_config()
    logging.basicConfig(
        level=config.get("LOG_LEVEL", "INFO"),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__) 