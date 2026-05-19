from domain.entities.user import User


def test_user_defaults_have_none_id():
    user = User(
        email="test@example.com",
        display_name="Test User",
        password_hash="hash",
        role="user",
        can_create=False,
        can_update=False,
        can_delete=False,
        is_active=True,
    )
    assert user.id is None
    assert user.invite_token is None
    assert user.invite_token_expires_at is None


def test_user_with_admin_role():
    user = User(
        email="admin@example.com",
        display_name="Admin",
        password_hash="hash",
        role="admin",
        can_create=True,
        can_update=True,
        can_delete=True,
        is_active=True,
    )
    assert user.role == "admin"
    assert user.can_create is True
