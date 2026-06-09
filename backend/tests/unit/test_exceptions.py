from domain.exceptions import (
    DomainException,
    ForbiddenException,
    NotAuthenticatedException,
    NotFoundException,
)


def test_not_authenticated_is_domain_exception():
    ex = NotAuthenticatedException()
    assert isinstance(ex, DomainException)
    assert isinstance(ex, Exception)


def test_forbidden_is_domain_exception():
    ex = ForbiddenException()
    assert isinstance(ex, DomainException)


def test_not_found_is_domain_exception():
    ex = NotFoundException()
    assert isinstance(ex, DomainException)


def test_conflict_exception_is_domain_exception():
    from domain.exceptions import ConflictException, DomainException

    ex = ConflictException()
    assert isinstance(ex, DomainException)
    assert ex.message == "資源衝突"


def test_conflict_exception_custom_message():
    from domain.exceptions import ConflictException

    ex = ConflictException("此名稱已存在")
    assert ex.message == "此名稱已存在"
