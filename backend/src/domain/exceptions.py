class DomainException(Exception):
    pass


class NotAuthenticatedException(DomainException):
    pass


class ForbiddenException(DomainException):
    pass


class NotFoundException(DomainException):
    pass
