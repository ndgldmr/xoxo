"""
Custom application exceptions.
"""


class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str = "An error occurred", status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundException(AppException):
    """Raised when a resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message=message, status_code=404)


class AlreadyExistsException(AppException):
    """Raised when attempting to create a resource that already exists."""

    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message=message, status_code=409)


class ValidationException(AppException):
    """Raised when validation fails."""

    def __init__(self, message: str = "Validation failed"):
        super().__init__(message=message, status_code=422)


class UnauthorizedException(AppException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message=message, status_code=401)


class ForbiddenException(AppException):
    """Raised when user lacks permissions."""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(message=message, status_code=403)
