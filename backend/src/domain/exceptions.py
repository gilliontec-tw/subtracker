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


class BadRequestException(DomainException):
    def __init__(self, message: str = "請求無效") -> None:
        self.message = message
        super().__init__(message)


class ConflictException(DomainException):
    def __init__(self, message: str = "資源衝突") -> None:
        self.message = message
        super().__init__(message)
