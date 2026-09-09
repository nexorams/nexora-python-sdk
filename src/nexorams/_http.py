"""Internal HTTP Transport for Nexora Developer API.

Handles base URL normalization, Bearer authentication, connection pooling,
JSON serialization, query encoding, timeout aborts, idempotency headers,
and consistent response/error normalization.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Optional, Union

import httpx

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

DEFAULT_BASE_URL = "https://api.nexoragms.com/developer/v1"
DEFAULT_TIMEOUT_SECONDS = 30.0
USER_AGENT = "nexorams-python/1.0.0"


def _clean_params(params: Optional[Mapping[str, Any]]) -> dict[str, str]:
    """Filter out None values and stringify parameter values."""
    if not params:
        return {}
    cleaned: dict[str, str] = {}
    for k, v in params.items():
        if v is not None:
            if isinstance(v, bool):
                cleaned[k] = "true" if v else "false"
            else:
                cleaned[k] = str(v)
    return cleaned


class HttpClient:
    """Reusable synchronous HTTP client for Nexora Platform API."""

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._api_key = api_key.strip()
        raw_base = base_url or DEFAULT_BASE_URL
        self._base_url = raw_base.rstrip("/")
        self._default_timeout = float(timeout)

        self._session = httpx.Client(
            base_url=self._base_url,
            timeout=httpx.Timeout(self._default_timeout),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def default_timeout(self) -> float:
        return self._default_timeout

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json_data: Any = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """Executes an HTTP request and unpacks the response."""
        clean_path = path if path.startswith("/") else f"/{path}"
        query_params = _clean_params(params)

        req_headers: dict[str, str] = {}
        if headers:
            for k, v in headers.items():
                if k.lower() != "authorization":
                    req_headers[k] = str(v)

        if idempotency_key:
            req_headers["Idempotency-Key"] = idempotency_key.strip()

        req_timeout = (
            httpx.Timeout(float(timeout)) if timeout is not None else httpx.Timeout(self._default_timeout)
        )

        try:
            response = self._session.request(
                method=method,
                url=clean_path,
                params=query_params if query_params else None,
                json=json_data,
                headers=req_headers if req_headers else None,
                timeout=req_timeout,
            )
        except httpx.TimeoutException as exc:
            effective_timeout = timeout if timeout is not None else self._default_timeout
            raise APITimeoutError(
                message=f"Request timed out after {effective_timeout} seconds",
                code="REQUEST_TIMEOUT",
                status_code=408,
            ) from exc
        except httpx.RequestError as exc:
            # Network / connection error
            raise APIConnectionError(
                message=f"Network connection failed: {exc}",
                code="NETWORK_ERROR",
                status_code=0,
                details={"error_type": type(exc).__name__},
            ) from exc

        # Extract request correlation ID
        request_id = (
            response.headers.get("x-request-id")
            or response.headers.get("request-id")
            or None
        )

        # Parse body
        content_type = response.headers.get("content-type", "")
        response_data: Any = None
        if "application/json" in content_type:
            try:
                response_data = response.json()
            except Exception:
                response_data = None
        else:
            text = response.text
            response_data = {"message": text} if text else None

        # Handle errors
        if not response.is_success:
            self._handle_error(response, response_data, request_id)

        # If paginated response ({ data: [...], pagination: {...} }), return envelope
        if (
            isinstance(response_data, dict)
            and "data" in response_data
            and "pagination" in response_data
        ):
            return response_data

        # If wrapped in { success: true, data: ... } or { data: ... }, unwrap data
        if (
            isinstance(response_data, dict)
            and "data" in response_data
            and "pagination" not in response_data
        ):
            return response_data["data"]

        return response_data

    def _handle_error(
        self,
        response: httpx.Response,
        response_data: Any,
        request_id: Optional[str],
    ) -> None:
        """Parses error envelope and raises appropriate NexoraError subclass."""
        err_payload = {}
        if isinstance(response_data, dict):
            if isinstance(response_data.get("error"), dict):
                err_payload = response_data["error"]
            else:
                err_payload = response_data

        message = (
            err_payload.get("message")
            or (isinstance(response_data, dict) and response_data.get("message"))
            or f"Request failed with status {response.status_code}"
        )
        code = (
            err_payload.get("code")
            or (isinstance(response_data, dict) and response_data.get("code"))
            or f"HTTP_{response.status_code}"
        )
        resolved_req_id = (
            request_id
            or err_payload.get("requestId")
            or (isinstance(response_data, dict) and response_data.get("requestId"))
        )
        details = err_payload.get("details") or response_data

        status = response.status_code

        if status == 401:
            raise AuthenticationError(
                message=message,
                code=code,
                status_code=status,
                request_id=resolved_req_id,
                details=details,
            )
        if status == 403:
            raise PermissionDeniedError(
                message=message,
                code=code,
                status_code=status,
                request_id=resolved_req_id,
                details=details,
            )
        if status == 404:
            raise NotFoundError(
                message=message,
                code=code,
                status_code=status,
                request_id=resolved_req_id,
                details=details,
            )
        if status == 409:
            raise ConflictError(
                message=message,
                code=code,
                status_code=status,
                request_id=resolved_req_id,
                details=details,
            )
        if status in (400, 422):
            raise ValidationError(
                message=message,
                code=code,
                status_code=status,
                request_id=resolved_req_id,
                details=details,
            )
        if status == 429:
            retry_after_str = response.headers.get("retry-after")
            retry_after = int(retry_after_str) if retry_after_str and retry_after_str.isdigit() else None
            raise RateLimitError(
                message=message,
                code=code,
                status_code=status,
                request_id=resolved_req_id,
                details=details,
                retry_after=retry_after,
            )

        raise NexoraError(
            message=message,
            code=code,
            status_code=status,
            request_id=resolved_req_id,
            details=details,
        )

    def get(
        self,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        return self.request("GET", path, params=params, headers=headers, timeout=timeout)

    def post(
        self,
        path: str,
        *,
        json_data: Any = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        return self.request(
            "POST",
            path,
            params=params,
            json_data=json_data,
            headers=headers,
            timeout=timeout,
            idempotency_key=idempotency_key,
        )

    def patch(
        self,
        path: str,
        *,
        json_data: Any = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        return self.request(
            "PATCH",
            path,
            params=params,
            json_data=json_data,
            headers=headers,
            timeout=timeout,
            idempotency_key=idempotency_key,
        )

    def put(
        self,
        path: str,
        *,
        json_data: Any = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        return self.request(
            "PUT",
            path,
            params=params,
            json_data=json_data,
            headers=headers,
            timeout=timeout,
        )

    def delete(
        self,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        return self.request("DELETE", path, params=params, headers=headers, timeout=timeout)

    def close(self) -> None:
        """Close underlying httpx session."""
        self._session.close()

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        # Strictly mask API credentials
        return f"HttpClient(base_url={self._base_url!r}, timeout={self._default_timeout!r})"
