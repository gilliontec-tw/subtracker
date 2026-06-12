from domain.entities.user import User


def test_user_defaults_have_none_id():
    user = User(
        email="test@example.com",
        display_name="Test User",
        password_hash="hash",
        role="user",
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
        is_active=True,
    )
    assert user.role == "admin"
    assert user.is_active is True


def test_user_role_is_stored():
    user = User(
        email="user@example.com",
        display_name="Regular User",
        password_hash="hash",
        role="user",
        is_active=True,
    )
    assert user.role == "user"
    assert user.email == "user@example.com"
    assert user.display_name == "Regular User"
