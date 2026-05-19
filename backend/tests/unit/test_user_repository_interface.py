import pytest
from domain.repositories.user_repository import UserRepository


def test_user_repository_is_abstract():
    with pytest.raises(TypeError):
        UserRepository()  # type: ignore[abstract]


def test_concrete_must_implement_get_by_email():
    class Incomplete(UserRepository):
        async def get_by_id(self, id): ...

        async def list_all(self): ...

        async def save(self, entity): ...

        async def delete(self, id): ...

        # missing get_by_email and get_by_invite_token

    with pytest.raises(TypeError):
        Incomplete()
