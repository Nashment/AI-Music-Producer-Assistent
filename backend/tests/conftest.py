"""
Pytest configuration and fixtures
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.data.database import Database
from app.data.models import Base


@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine"""
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Session:
    """Get test database session"""
    TestingSessionLocal = sessionmaker(bind=test_db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_user_data():
    """Test user data"""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "test_password_123"
    }


@pytest.fixture
def test_project_data():
    """Test project data"""
    return {
        "title": "Test Music Project",
        "description": "A test music project",
        "tempo": 120
    }


@pytest.fixture
def test_generation_params():
    """Test generation parameters"""
    return {
        "prompt": "Create a piano solo section",
        "instrument": "piano",
        "genre": "classical",
        "duration": 30
    }
