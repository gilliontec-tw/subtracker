class DomainException(Exception):
    pass


class NotAuthenticatedException(DomainException):
    pass


class ForbiddenException(DomainException):
    pass


class NotFoundException(DomainException):
    pass


class DuplicateEmailException(DomainException):
    pass


class LastAdminException(DomainException):
    pass
