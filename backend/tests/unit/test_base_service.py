from application.services.base import BaseService


def test_base_service_is_instantiable():
    svc = BaseService()
    assert isinstance(svc, BaseService)
