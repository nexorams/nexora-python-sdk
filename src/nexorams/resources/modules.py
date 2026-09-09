"""Nexora Modules Resource.

Lists available modular features from the Nexora system catalog and toggles
entitled capabilities for tenant organizations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Sequence

if TYPE_CHECKING:
    from .._http import HttpClient


class ModulesResource:
    """Resource for inspecting and configuring system modular features."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(
        self,
        organization_type: Optional[str] = None,
        sector: Optional[str] = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """List extensible modules, optionally filtered by sector / organization type.

        Args:
            organization_type: Filter by sector ('school', 'hospital', 'hotel', 'pharmacy', 'enterprise').
            sector: Alias for organization_type.

        Returns:
            List of available module catalog items.
        """
        params: dict[str, Any] = {}
        resolved_type = organization_type or sector
        if resolved_type is not None:
            params["organizationType"] = resolved_type
        params.update(kwargs)

        return self._http.get("/modules", params=params)

    def update(
        self,
        organization_id: str,
        modules: Sequence[str],
    ) -> dict[str, Any]:
        """Update enabled feature modules for a specific organization.

        Args:
            organization_id: Target organization ID.
            modules: Sequence of feature module keys to enable.

        Returns:
            Dictionary with organizationId, activeFeatures, and updatedAt timestamp.
        """
        return self._http.patch(
            f"/organizations/{organization_id}/modules",
            json_data={"modules": list(modules)},
        )
