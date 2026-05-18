import pytest
from domain.repositories.base import BaseRepository


def test_base_repository_is_abstract():
    with pytest.raises(TypeError):
        BaseRepository()  # type: ignore[abstract]


def test_concrete_repository_must_implement_all_methods():
    class Incomplete(BaseRepository[object, int]):
        async def get_by_id(self, id): ...

    with pytest.raises(TypeError):
        Incomplete()
