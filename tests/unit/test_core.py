import pytest
from app.core.config import GENERATED_DIR, LOGS_DIR

@pytest.mark.unit
def test_directories_exist():
    """Test that required directories are created."""
    assert GENERATED_DIR.exists()
    assert LOGS_DIR.exists() 