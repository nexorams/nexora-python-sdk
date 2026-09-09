"""Nexora Plans Resource.

Queries subscription tiers, pricing, limits, and quotas available across
different organization sectors and developer products.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .._http import HttpClient


class PlansResource:
    """Resource for querying available subscription plans."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(
        self,
        organization_type: Optional[str] = None,
        sector: Optional[str] = None,
        product_context: Optional[str] = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """List available subscription plans, tiers, and quotas.

        Args:
            organization_type: Filter by sector ('school', 'hospital', 'hotel', 'pharmacy', 'enterprise').
            sector: Alias for organization_type.
            product_context: Filter by context ('ORGANIZATION' or 'DEVELOPER').

        Returns:
            List of plan definitions with pricing, tiers, and resource quotas.
        """
        params: dict[str, Any] = {}
        resolved_type = organization_type or sector
        if resolved_type is not None:
            params["organizationType"] = resolved_type
        if product_context is not None:
            params["productContext"] = product_context
        params.update(kwargs)

        return self._http.get("/plans", params=params)
