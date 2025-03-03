from pathlib import Path

TEST_CONFIG = {
    "SCYLLA_HOSTS": ["localhost"],
    "SCYLLA_PORT": 9042,
    "LOG_LEVEL": "INFO",
    "MODEL_DIR": str(Path(__file__).parent / "test_models"),
    "DB_KEYSPACE": "grok_meetu_test",
    "ENVIRONMENT": "test"
} 