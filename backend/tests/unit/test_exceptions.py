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
