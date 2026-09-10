"""Nexora School Sector Resource.

Provides programmatic access to school-specific endpoints:
students, classes, attendance, and related operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from .._http import HttpClient


class _Students:
    """Sub-resource for /school/students endpoints."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(
        self,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        class_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List students with optional filters."""
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if search:
            params["search"] = search
        if status:
            params["status"] = status
        if class_id:
            params["classId"] = class_id
        params.update(kwargs)
        return self._http.get("/school/students", params=params)

    def create(self, data: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        """Create a new student record."""
        return self._http.post("/school/students", json_data=data, **kwargs)


class _Attendance:
    """Sub-resource for /school/attendance endpoints."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(
        self,
        page: int = 1,
        limit: int = 20,
        class_id: Optional[str] = None,
        date: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List attendance records."""
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if class_id:
            params["classId"] = class_id
        if date:
            params["date"] = date
        params.update(kwargs)
        return self._http.get("/school/attendance", params=params)

    def record(self, data: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        """Record attendance."""
        return self._http.post("/school/attendance", json_data=data, **kwargs)


class _Classes:
    """Sub-resource for /school/classes endpoints."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, **kwargs: Any) -> Dict[str, Any]:
        """List school classes."""
        return self._http.get("/school/classes", **kwargs)

    def create(self, data: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        """Create a new class."""
        return self._http.post("/school/classes", json_data=data, **kwargs)


class SchoolResource:
    """Resource for interacting with school sector endpoints via the Developer API."""

    def __init__(self, http: HttpClient) -> None:
        self.students = _Students(http)
        self.attendance = _Attendance(http)
        self.classes = _Classes(http)
