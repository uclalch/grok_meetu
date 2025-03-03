from pathlib import Path
import pytest

def pytest_configure(config):
    """Validate test environment before running tests"""
    if Path.cwd().name != "grok_meetu":
        pytest.exit(
            "\n❌ Tests must be run from the grok_meetu directory!"
            "\n   Current directory: {}"
            "\n   Please run: cd grok_meetu && python -m pytest tests/test_api.py"
            .format(Path.cwd())
        ) 