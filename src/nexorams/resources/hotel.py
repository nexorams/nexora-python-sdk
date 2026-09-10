"""Nexora Hotel Sector Resource.

Provides programmatic access to hotel-specific endpoints:
rooms, reservations, guests, and related operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from .._http import HttpClient


class _Rooms:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, page: int = 1, limit: int = 20,
             status: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if status: params["status"] = status
        params.update(kwargs)
        return self._http.get("/hotel/rooms", params=params)


class _Reservations:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, page: int = 1, limit: int = 20,
             status: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if status: params["status"] = status
        params.update(kwargs)
        return self._http.get("/hotel/reservations", params=params)

    def create(self, data: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        return self._http.post("/hotel/reservations", json_data=data, **kwargs)


class _Guests:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, **kwargs: Any) -> Dict[str, Any]:
        return self._http.get("/hotel/guests", **kwargs)


class HotelResource:
    """Resource for interacting with hotel sector endpoints via the Developer API."""

    def __init__(self, http: HttpClient) -> None:
        self.rooms = _Rooms(http)
        self.reservations = _Reservations(http)
        self.guests = _Guests(http)
