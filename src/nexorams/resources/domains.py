"""Nexora Custom Domains Resource.

Manages custom white-label hostnames and automated DNS verification for tenant organizations.
Authoritative DNS verification is performed server-side by the Nexora DomainService.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .._http import HttpClient


class DomainsResource:
    """Resource for managing custom white-label domains."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, organization_id: str) -> list[dict[str, Any]]:
        """List custom domains configured for an organization.

        Args:
            organization_id: Target organization ID.

        Returns:
            List of domain objects with verification status and DNS records.
        """
        return self._http.get(f"/organizations/{organization_id}/domains")

    def create(
        self,
        organization_id: str,
        hostname: Optional[str] = None,
        domain: Optional[str] = None,
        is_primary: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Connect a custom domain to an organization.

        Returns required DNS verification records (TXT and CNAME).

        Args:
            organization_id: Target organization ID.
            hostname: Fully-qualified domain name (e.g. 'portal.example.com').
            domain: Alias for hostname.
            is_primary: Whether this is the primary vanity domain for the organization.

        Returns:
            Dictionary with domain ID, status, and required DNS verification records.
        """
        resolved_host = hostname or domain
        if not resolved_host:
            raise ValueError("Either 'hostname' or 'domain' must be provided.")

        payload: dict[str, Any] = {
            "hostname": resolved_host,
            "isPrimary": is_primary,
        }
        payload.update(kwargs)

        return self._http.post(
            f"/organizations/{organization_id}/domains",
            json_data=payload,
        )

    def verify(self, organization_id: str, domain_id: str) -> dict[str, Any]:
        """Trigger authoritative DNS verification for an organization's custom domain.

        Args:
            organization_id: Target organization ID.
            domain_id: Domain record ID to verify.

        Returns:
            Dictionary with verification outcome, status, and diagnostic messages.
        """
        return self._http.post(
            f"/organizations/{organization_id}/domains/{domain_id}/verify",
            json_data={},
        )
