"""Nexora Hospital Sector Resource.

Provides programmatic access to hospital-specific endpoints:
patients, appointments, vitals, and related operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from .._http import HttpClient


class _Patients:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, page: int = 1, limit: int = 20, search: Optional[str] = None,
             gender: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if search: params["search"] = search
        if gender: params["gender"] = gender
        params.update(kwargs)
        return self._http.get("/hospital/patients", params=params)

    def create(self, data: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        return self._http.post("/hospital/patients", json_data=data, **kwargs)


class _Appointments:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, page: int = 1, limit: int = 20, status: Optional[str] = None,
             patient_id: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if status: params["status"] = status
        if patient_id: params["patientId"] = patient_id
        params.update(kwargs)
        return self._http.get("/hospital/appointments", params=params)

    def create(self, data: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        return self._http.post("/hospital/appointments", json_data=data, **kwargs)


class _Vitals:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, page: int = 1, limit: int = 20,
             patient_id: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if patient_id: params["patientId"] = patient_id
        params.update(kwargs)
        return self._http.get("/hospital/vitals", params=params)

    def record(self, data: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        return self._http.post("/hospital/vitals", json_data=data, **kwargs)


class HospitalResource:
    """Resource for interacting with hospital sector endpoints via the Developer API."""

    def __init__(self, http: HttpClient) -> None:
        self.patients = _Patients(http)
        self.appointments = _Appointments(http)
        self.vitals = _Vitals(http)
