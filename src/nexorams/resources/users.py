"""Nexora Users Resource.

Provisions and lists safe tenant user accounts (doctors, teachers, employees,
receptionists) within an organization. Platform administration roles are forbidden.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .._http import HttpClient


class UsersResource:
    """Resource for interacting with organization users."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def create(
        self,
        organization_id: str,
        first_name: str,
        last_name: str,
        email: str,
        role: str,
        phone: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Provision a staff member, practitioner, or client user inside an organization.

        Generates an invitation token for password setup. Note that platform administration
        roles are forbidden via the Developer API.

        Args:
            organization_id: Target organization ID.
            first_name: User first name.
            last_name: User last name.
            email: User corporate or personal email address.
            role: Sector role (e.g. 'teacher', 'doctor', 'staff', 'nurse').
            phone: Optional contact phone number.

        Returns:
            Dictionary with provisioned user details, activation token, and expiration timestamp.
        """
        payload: dict[str, Any] = {
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "role": role,
        }
        if phone is not None:
            payload["phone"] = phone
        payload.update(kwargs)

        return self._http.post(
            f"/organizations/{organization_id}/users",
            json_data=payload,
        )

    def list(
        self,
        organization_id: str,
        role: Optional[str] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """List safe user memberships in a tenant organization.

        Args:
            organization_id: Target organization ID.
            role: Filter by user role.
            page: Pagination page offset.
            limit: Maximum records to return.

        Returns:
            List of tenant users in the organization.
        """
        params: dict[str, Any] = {}
        if role is not None:
            params["role"] = role
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit
        params.update(kwargs)

        return self._http.get(
            f"/organizations/{organization_id}/users",
            params=params,
        )
