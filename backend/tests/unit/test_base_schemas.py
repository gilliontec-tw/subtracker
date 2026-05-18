from api.v1.schemas.base import ApiResponse


def test_success_response():
    r = ApiResponse(success=True, data={"id": 1}, message="ok")
    assert r.success is True
    assert r.data == {"id": 1}
    assert r.meta is None


def test_error_response():
    r = ApiResponse(success=False, data=None, message="error")
    assert r.success is False
