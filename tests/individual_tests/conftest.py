# tests/individual_tests/conftest.py
"""
Configuration for individual component tests
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture(scope="session")
def project_root_path():
    """Provide the project root path to tests"""
    return project_root

@pytest.fixture
def db_session():
    """Provide a database session for tests"""
    from app.database.connection import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def test_project():
    """Create a test project for testing"""
    from app.database.models.project import Project
    return Project.create_new(
        client_name="Test Client",
        description="Test project for unit testing",
        configuration={
            "brand_voice": "professional and friendly",
            "target_audience": "business professionals",
            "content_types": ["blog", "email", "social_media"]
        }
    )
