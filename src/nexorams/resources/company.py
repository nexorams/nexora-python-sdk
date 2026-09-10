"""Nexora Company/Enterprise Sector Resource.

Provides programmatic access to company/enterprise-specific endpoints:
employees, attendance, payroll, and related operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from .._http import HttpClient


class _Employees:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, page: int = 1, limit: int = 20, search: Optional[str] = None,
             status: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if search: params["search"] = search
        if status: params["status"] = status
        params.update(kwargs)
        return self._http.get("/company/employees", params=params)

    def create(self, data: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        return self._http.post("/company/employees", json_data=data, **kwargs)


class _CompanyAttendance:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, page: int = 1, limit: int = 20,
             employee_id: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if employee_id: params["employeeId"] = employee_id
        params.update(kwargs)
        return self._http.get("/company/attendance", params=params)

    def record(self, data: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        return self._http.post("/company/attendance", json_data=data, **kwargs)


class _Payroll:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, **kwargs: Any) -> Dict[str, Any]:
        return self._http.get("/company/payroll", **kwargs)


class CompanyResource:
    """Resource for interacting with company/enterprise sector endpoints via the Developer API."""

    def __init__(self, http: HttpClient) -> None:
        self.employees = _Employees(http)
        self.attendance = _CompanyAttendance(http)
        self.payroll = _Payroll(http)
