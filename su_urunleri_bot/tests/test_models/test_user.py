"""
Tests for User model.
"""

import pytest
from bot.models.user import User, UserSession


class TestUser:
    """Test User model."""

    def test_user_creation(self):
        """Test user creation."""
        user = User(user_id=123, username='testuser', first_name='Test')
        assert user.user_id == 123
        assert user.username == 'testuser'
        assert user.first_name == 'Test'

    def test_user_full_name(self):
        """Test full name property."""
        user = User(user_id=1, first_name='John', last_name='Doe')
        assert user.full_name == 'John Doe'

        user2 = User(user_id=2, first_name='Jane')
        assert user2.full_name == 'Jane'

    def test_display_name(self):
        """Test display name."""
        user = User(user_id=1, custom_name='Admin')
        assert user.display_name == 'Admin'

        user2 = User(user_id=2, first_name='John')
        assert user2.display_name == 'John'

        user3 = User(user_id=3, username='testuser')
        assert user3.display_name == '@testuser'

    def test_is_admin(self, mock_config):
        """Test admin check."""
        # Setup: admin_ids = {123456789}
        user_admin = User(user_id=123456789)
        assert user_admin.is_admin

        user_regular = User(user_id=999)
        assert not user_regular.is_admin

    def test_is_allowed(self, mock_config):
        """Test allowed user check."""
        user_admin = User(user_id=123456789)
        assert user_admin.is_allowed

        user_regular = User(user_id=999)
        assert not user_regular.is_allowed

    def test_permissions(self):
        """Test permission management."""
        user = User(user_id=1)
        assert not user.has_permission('admin')

        user.grant_permission('admin')
        assert user.has_permission('admin')

        user.revoke_permission('admin')
        assert not user.has_permission('admin')

    def test_user_to_dict(self):
        """Test user to dictionary."""
        user = User(user_id=1, username='test', first_name='Test')
        data = user.to_dict()

        assert data['user_id'] == 1
        assert data['username'] == 'test'
        assert data['first_name'] == 'Test'


class TestUserSession:
    """Test UserSession model."""

    def test_session_creation(self):
        """Test session creation."""
        user = User(user_id=1, first_name='Test')
        session = UserSession(user=user)

        assert session.user == user
        assert len(session.context_data) == 0
        assert session.last_action is None

    def test_session_state(self):
        """Test session state management."""
        user = User(user_id=1)
        session = UserSession(user=user)

        session.set_state('key1', 'value1')
        assert session.get_state('key1') == 'value1'

        session.set_state('key2', {'nested': 'value'})
        assert session.get_state('key2')['nested'] == 'value'

        # Default value
        assert session.get_state('nonexistent', 'default') == 'default'

    def test_session_clear_state(self):
        """Test clearing session state."""
        user = User(user_id=1)
        session = UserSession(user=user)

        session.set_state('key', 'value')
        assert len(session.conversation_state) > 0

        session.clear_state()
        assert len(session.conversation_state) == 0

    def test_session_update_action(self):
        """Test updating last action."""
        user = User(user_id=1)
        session = UserSession(user=user)

        assert session.last_action is None

        session.update_action('search')
        assert session.last_action == 'search'
        assert session.last_action_time is not None

    def test_session_to_dict(self):
        """Test session to dictionary."""
        user = User(user_id=1, first_name='Test')
        session = UserSession(user=user)
        session.set_state('key', 'value')

        data = session.to_dict()
        assert data['user']['user_id'] == 1
        assert data['conversation_state']['key'] == 'value'
