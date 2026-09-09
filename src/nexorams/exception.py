"""Alias for nexorams.exceptions for backward compatibility."""

from .exceptions import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    ConflictError,
    NexoraError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ValidationError,
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
