import inspect

import pytest
from domain.repositories.subscription_repository import SubscriptionRepository


def test_list_paginated_is_abstract():
    assert "list_paginated" in {
        name
        for name, _ in inspect.getmembers(SubscriptionRepository)
        if getattr(getattr(SubscriptionRepository, name, None), "__isabstractmethod__", False)
    }


def test_cannot_instantiate_directly():
    with pytest.raises(TypeError):
        SubscriptionRepository()  # type: ignore[abstract]


def test_inherits_base_repository_methods():
    abstract_methods = {
        name
        for name, _ in inspect.getmembers(SubscriptionRepository)
        if getattr(getattr(SubscriptionRepository, name, None), "__isabstractmethod__", False)
    }
    assert "get_by_id" in abstract_methods
    assert "save" in abstract_methods
    assert "delete" in abstract_methods
