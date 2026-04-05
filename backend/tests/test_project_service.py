"""
Tests for ProjectService
"""

import pytest
from backend.app.services.project_service import ProjectService
from backend.app.data.queries import ProjectQueries, UserQueries


class TestProjectService:
    """Tests for project management service"""

    def test_create_project(self, test_db_session, test_user_data, test_project_data):
        """Test project creation"""
        # TODO: Implement test
        # should create project with correct data
        # should link to user
        # should validate required fields
        pass

    def test_get_project(self, test_db_session, test_project_data):
        """Test retrieving project"""
        # TODO: Implement test
        pass

    def test_list_user_projects(self, test_db_session):
        """Test listing user projects"""
        # TODO: Implement test
        # should return only user's projects
        # should be ordered by creation date
        pass

    def test_update_project(self, test_db_session, test_project_data):
        """Test updating project"""
        # TODO: Implement test
        pass

    def test_delete_project(self, test_db_session):
        """Test project deletion"""
        # TODO: Implement test
        # should verify user authorization
        # should cascade delete related data
        pass

    def test_add_audio_to_project(self, test_db_session):
        """Test adding audio file to project"""
        # TODO: Implement test
        pass


class TestProjectQueries:
    """Tests for project database queries"""

    def test_create_project_query(self, test_db_session, test_user_data, test_project_data):
        """Test raw project creation query"""
        # Create user first
        user = UserQueries.create_user(
            test_db_session,
            test_user_data["email"],
            test_user_data["username"],
            "hashed_password"
        )
        
        # Create project
        project = ProjectQueries.create_project(
            test_db_session,
            user.id,
            test_project_data["title"],
            test_project_data["description"],
            test_project_data["tempo"]
        )
        
        assert project.user_id == user.id
        assert project.title == test_project_data["title"]
        assert project.tempo == test_project_data["tempo"]

    def test_get_user_projects_query(self, test_db_session, test_user_data, test_project_data):
        """Test retrieving user projects query"""
        user = UserQueries.create_user(
            test_db_session,
            test_user_data["email"],
            test_user_data["username"],
            "hashed_password"
        )
        
        # Create multiple projects
        for i in range(3):
            ProjectQueries.create_project(
                test_db_session,
                user.id,
                f"Project {i}",
                f"Description {i}",
                120
            )
        
        projects = ProjectQueries.get_user_projects(test_db_session, user.id)
        assert len(projects) == 3
