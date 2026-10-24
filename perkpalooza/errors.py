"""Domain errors suitable for mapping to API responses."""


class DomainError(Exception):
    code = "domain_error"
    http_status = 400

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        if code:
            self.code = code


class NotFound(DomainError):
    code = "not_found"
    http_status = 404


class Conflict(DomainError):
    code = "conflict"
    http_status = 409


class Forbidden(DomainError):
    code = "forbidden"
    http_status = 403


class Unavailable(DomainError):
    code = "unavailable"
    http_status = 503
