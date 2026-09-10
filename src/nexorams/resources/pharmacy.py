"""Nexora Pharmacy Sector Resource.

Provides programmatic access to pharmacy-specific endpoints:
products, prescriptions, sales, and related operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from .._http import HttpClient


class _Products:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, page: int = 1, limit: int = 20,
             search: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if search: params["search"] = search
        params.update(kwargs)
        return self._http.get("/pharmacy/products", params=params)

    def create(self, data: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        return self._http.post("/pharmacy/products", json_data=data, **kwargs)


class _Prescriptions:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, **kwargs: Any) -> Dict[str, Any]:
        return self._http.get("/pharmacy/prescriptions", **kwargs)


class _Sales:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, **kwargs: Any) -> Dict[str, Any]:
        return self._http.get("/pharmacy/sales", **kwargs)


class PharmacyResource:
    """Resource for interacting with pharmacy sector endpoints via the Developer API."""

    def __init__(self, http: HttpClient) -> None:
        self.products = _Products(http)
        self.prescriptions = _Prescriptions(http)
        self.sales = _Sales(http)
