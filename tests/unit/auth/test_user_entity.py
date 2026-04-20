from src.domain.entities.user import User


def test_user_defaults():
    user = User(
        email="alice@gilliontec.com.tw",
        display_name="Alice",
        hashed_password="hashed",
        role="user",
        can_create=False,
        can_update=False,
        can_delete=False,
    )
    assert user.is_active is True
    assert user.id is None
    assert user.created_at is None
    assert user.last_login_at is None


def test_admin_has_all_permissions():
    user = User(
        email="admin@gilliontec.com.tw",
        display_name="Admin",
        hashed_password="hashed",
        role="admin",
        can_create=True,
        can_update=True,
        can_delete=True,
    )
    assert user.role == "admin"
    assert user.can_create is True
    assert user.can_update is True
    assert user.can_delete is True
