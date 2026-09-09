"""Nexora Organizations Resource.

Provides programmatic provisioning, listing, retrieval, and configuration
of tenant management systems across sectors (School, Hospital, Hotel, Pharmacy, Enterprise).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping, Optional, Sequence

if TYPE_CHECKING:
    from .._http import HttpClient


class OrganizationsResource:
    """Resource for interacting with /developer/v1/organizations endpoints."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def create(
        self,
        name: str,
        type: str,
        owner: Mapping[str, Any],
        country: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        address: Optional[str] = None,
        timezone: Optional[str] = None,
        currency: Optional[str] = None,
        subdomain: Optional[str] = None,
        custom_domain: Optional[str] = None,
        modules: Optional[Sequence[str]] = None,
        branding: Optional[Mapping[str, Any]] = None,
        subscription: Optional[Mapping[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Provision a new tenant organization.

        Uses the canonical Nexora Organization Provisioning Service.
        In TEST environment, sandboxed resources with 30-day trials are created.

        Args:
            name: Organization display name (e.g. 'Apex Specialist Hospital').
            type: Organization sector ('HOSPITAL', 'SCHOOL', 'HOTEL', 'PHARMACY', 'ENTERPRISE').
            owner: Owner details dict with 'firstName', 'lastName', 'email' (and optional 'phone').
            country: ISO country code (e.g. 'NG', 'US', 'GB').
            state: State or province.
            city: City location.
            address: Physical address.
            timezone: Timezone identifier (e.g. 'Africa/Lagos').
            currency: Operating currency code (e.g. 'NGN', 'USD').
            subdomain: Custom subdomain slug (e.g. 'apex-hospital').
            custom_domain: Full custom domain (e.g. 'portal.apex.org').
            modules: List of module keys to enable.
            branding: Optional branding dict with 'primaryColor', 'secondaryColor', 'theme', 'logo'.
            subscription: Optional subscription preferences.
            idempotency_key: Unique key to ensure atomic, non-duplicate provisioning.

        Returns:
            Dictionary containing provisioned organization details, portal URL, owner info, and trial status.
        """
        # Format owner payload
        owner_payload: dict[str, Any] = {}
        for k, v in owner.items():
            if k == "first_name":
                owner_payload["firstName"] = v
            elif k == "last_name":
                owner_payload["lastName"] = v
            else:
                owner_payload[k] = v

        payload: dict[str, Any] = {
            "name": name,
            "type": type,
            "owner": owner_payload,
        }

        if country is not None:
            payload["country"] = country
        if state is not None:
            payload["state"] = state
        if city is not None:
            payload["city"] = city
        if address is not None:
            payload["address"] = address
        if timezone is not None:
            payload["timezone"] = timezone
        if currency is not None:
            payload["currency"] = currency
        if subdomain is not None:
            payload["subdomain"] = subdomain
        if custom_domain is not None:
            payload["customDomain"] = custom_domain
        if modules is not None:
            payload["modules"] = list(modules)
        if branding is not None:
            payload["branding"] = dict(branding)
        if subscription is not None:
            payload["subscription"] = dict(subscription)

        # Include additional kwargs
        payload.update(kwargs)

        return self._http.post(
            "/organizations",
            json_data=payload,
            idempotency_key=idempotency_key,
        )

    def list(
        self,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        environment: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """List organizations authorized under the authenticated developer project.

        Returns:
            Paginated dictionary with 'data' (list of organizations) and 'pagination' metadata.
        """
        params: dict[str, Any] = {
            "page": page,
            "limit": limit,
            "type": type,
            "status": status,
            "search": search,
            "environment": environment,
        }
        params.update(kwargs)

        return self._http.get("/organizations", params=params)

    def get(self, id: str) -> dict[str, Any]:
        """Retrieve organization details by ID."""
        return self._http.get(f"/organizations/{id}")

    def retrieve(self, id: str) -> dict[str, Any]:
        """Alias for get(id)."""
        return self.get(id)

    def update(
        self,
        id: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[Any] = None,
        primary_color: Optional[str] = None,
        secondary_color: Optional[str] = None,
        theme: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update organization metadata, branding, address, phone, or theme."""
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if phone is not None:
            payload["phone"] = phone
        if address is not None:
            payload["address"] = address
        if primary_color is not None:
            payload["primaryColor"] = primary_color
        if secondary_color is not None:
            payload["secondaryColor"] = secondary_color
        if theme is not None:
            payload["theme"] = theme

        payload.update(kwargs)

        return self._http.patch(f"/organizations/{id}", json_data=payload)

    def update_modules(self, id: str, modules: Sequence[str]) -> dict[str, Any]:
        """Update enabled feature modules for an organization."""
        return self._http.patch(
            f"/organizations/{id}/modules",
            json_data={"modules": list(modules)},
        )

    def get_subscription(self, id: str) -> dict[str, Any]:
        """Retrieve subscription and trial status for an organization."""
        return self._http.get(f"/organizations/{id}/subscription")

    def get_domains(self, id: str) -> list[dict[str, Any]]:
        """List custom domains configured for an organization."""
        return self._http.get(f"/organizations/{id}/domains")

    def add_domain(
        self,
        id: str,
        hostname: str,
        is_primary: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Add a custom domain to an organization."""
        payload = {"hostname": hostname, "isPrimary": is_primary}
        payload.update(kwargs)
        return self._http.post(f"/organizations/{id}/domains", json_data=payload)

    def verify_domain(self, id: str, domain_id: str) -> dict[str, Any]:
        """Trigger DNS verification for an organization's custom domain."""
        return self._http.post(f"/organizations/{id}/domains/{domain_id}/verify", json_data={})
