"""Typed API errors raised from services and mapped by the exception handler."""


class AppAPIError(Exception):
    """Structured API error with a catalog code, HTTP status, and details."""

    def __init__(
        self,
        code: str,
        status_code: int = 400,
        details: dict | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(code)
