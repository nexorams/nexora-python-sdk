"""Nexora SDK Exceptions.

Defines the error hierarchy for the Nexora Developer Platform Python client.
Ensures sensitive credentials, API keys, and authorization headers are never
exposed in error strings, logs, or representations.
"""

from __future__ import annotations

from typing import Any, Optional


class NexoraError(Exception):
    """Base exception for all Nexora SDK errors.

    Attributes:
        message: Human-readable error description.
        code: Machine-readable error code returned by API or SDK (e.g. 'RATE_LIMIT_EXCEEDED').
        status_code: HTTP status code, or 0 for network/transport failures.
        request_id: Unique correlation request ID (e.g. 'req_12345') for diagnostics.
        details: Optional supplementary details or payload from the server response.
    """

    def __init__(
        self,
        message: str,
        code: str = "API_ERROR",
        status_code: int = 500,
        request_id: Optional[str] = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.request_id = request_id
        self.details = details

    def __str__(self) -> str:
        req_str = f" [request_id: {self.request_id}]" if self.request_id else ""
        return f"{self.code} (status {self.status_code}): {self.message}{req_str}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"code={self.code!r}, "
            f"status_code={self.status_code!r}, "
            f"request_id={self.request_id!r})"
        )

    def to_dict(self) -> dict[str, Any]:
        """Safe dictionary representation for structured logging."""
        return {
            "name": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "status_code": self.status_code,
            "request_id": self.request_id,
            "details": self.details,
        }


class AuthenticationError(NexoraError):
    """Raised on HTTP 401 Unauthorized or missing/invalid API key credentials."""

    def __init__(
        self,
        message: str = "Invalid or missing API key credentials.",
        code: str = "INVALID_API_KEY",
        status_code: int = 401,
        request_id: Optional[str] = None,
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            request_id=request_id,
            details=details,
        )


class PermissionDeniedError(NexoraError):
    """Raised on HTTP 403 Forbidden (e.g. missing required API scope, project suspended)."""

    def __init__(
        self,
        message: str = "Access denied or insufficient scope.",
        code: str = "INSUFFICIENT_SCOPE",
        status_code: int = 403,
        request_id: Optional[str] = None,
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            request_id=request_id,
            details=details,
        )


class NotFoundError(NexoraError):
    """Raised on HTTP 404 Not Found."""

    def __init__(
        self,
        message: str = "Requested resource not found.",
        code: str = "NOT_FOUND",
        status_code: int = 404,
        request_id: Optional[str] = None,
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            request_id=request_id,
            details=details,
        )


class ConflictError(NexoraError):
    """Raised on HTTP 409 Conflict (e.g. duplicate user, idempotency payload mismatch)."""

    def __init__(
        self,
        message: str = "Resource conflict or idempotency mismatch.",
        code: str = "CONFLICT",
        status_code: int = 409,
        request_id: Optional[str] = None,
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            request_id=request_id,
            details=details,
        )


class ValidationError(NexoraError):
    """Raised on HTTP 400 Bad Request or HTTP 422 Unprocessable Entity."""

    def __init__(
        self,
        message: str = "Invalid request parameters.",
        code: str = "VALIDATION_ERROR",
        status_code: int = 400,
        request_id: Optional[str] = None,
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            request_id=request_id,
            details=details,
        )


class RateLimitError(NexoraError):
    """Raised on HTTP 429 Too Many Requests (rate limit or monthly quota exceeded)."""

    def __init__(
        self,
        message: str = "Rate limit or monthly quota exceeded.",
        code: str = "RATE_LIMIT_EXCEEDED",
        status_code: int = 429,
        request_id: Optional[str] = None,
        details: Any = None,
        retry_after: Optional[int] = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            request_id=request_id,
            details=details,
        )
        self.retry_after = retry_after


class APITimeoutError(NexoraError):
    """Raised when an HTTP request times out."""

    def __init__(
        self,
        message: str = "Request timed out.",
        code: str = "REQUEST_TIMEOUT",
        status_code: int = 408,
        request_id: Optional[str] = None,
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            request_id=request_id,
            details=details,
        )


class APIConnectionError(NexoraError):
    """Raised when a network transport failure occurs (e.g. DNS failure, connection refused)."""

    def __init__(
        self,
        message: str = "Network connection failed.",
        code: str = "NETWORK_ERROR",
        status_code: int = 0,
        request_id: Optional[str] = None,
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            request_id=request_id,
            details=details,
        )


__all__ = [
    "NexoraError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "RateLimitError",
    "APITimeoutError",
    "APIConnectionError",
]
