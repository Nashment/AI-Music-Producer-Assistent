"""
Tests for UserService
"""

import pytest
from app.services.user_service import UserService
from app.data.queries import UserQueries


class TestUserService:
    """Tests for user management service"""

    def test_create_user(self, test_db_session, test_user_data):
        """Test user creation"""
        # TODO: Implement test
        # should verify user is created with correct data
        # should hash password
        # should validate email uniqueness
        pass

    def test_get_user_by_email(self, test_db_session, test_user_data):
        """Test retrieving user by email"""
        # TODO: Implement test
        pass

    def test_authenticate_user_success(self, test_db_session, test_user_data):
        """Test successful user authentication"""
        # TODO: Implement test
        # should verify password matching
        pass

    def test_authenticate_user_invalid_password(self, test_db_session, test_user_data):
        """Test authentication with invalid password"""
        # TODO: Implement test
        # should reject invalid password
        pass

    def test_update_user_profile(self, test_db_session):
        """Test updating user profile"""
        # TODO: Implement test
        pass

    def test_delete_user(self, test_db_session):
        """Test user deletion"""
        # TODO: Implement test
        pass


class TestUserQueries:
    """Tests for user database queries"""

    def test_create_user_query(self, test_db_session, test_user_data):
        """Test raw user creation query"""
        user = UserQueries.create_user(
            test_db_session,
            test_user_data["email"],
            test_user_data["username"],
            "hashed_password"
        )
        assert user.email == test_user_data["email"]
        assert user.username == test_user_data["username"]

    def test_get_user_by_email_query(self, test_db_session, test_user_data):
        """Test retrieving user by email query"""
        # Create user first
        UserQueries.create_user(
            test_db_session,
            test_user_data["email"],
            test_user_data["username"],
            "hashed_password"
        )
        
        # Retrieve user
        user = UserQueries.get_user_by_email(test_db_session, test_user_data["email"])
        assert user is not None
        assert user.email == test_user_data["email"]

    def test_get_user_by_id_query(self, test_db_session, test_user_data):
        """Test retrieving user by ID query"""
        user = UserQueries.create_user(
            test_db_session,
            test_user_data["email"],
            test_user_data["username"],
            "hashed_password"
        )
        
        retrieved_user = UserQueries.get_user_by_id(test_db_session, user.id)
        assert retrieved_user is not None
        assert retrieved_user.id == user.id
