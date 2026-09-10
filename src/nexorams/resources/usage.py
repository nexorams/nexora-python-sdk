"""Nexora Usage & Observability Resource.

Provides monthly API call volume metrics, status-code class breakdowns,
rate limit hits, endpoint usage, and developer project tier profiles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .._http import HttpClient


class UsageResource:
    """Resource for monitoring API telemetry, quotas, and project tier status."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def summary(
        self,
        period: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Retrieve monthly API call volume, successful requests, error rates, and endpoint breakdowns.

        Args:
            period: Billing period in 'YYYY-MM' format (e.g. '2026-09'). Defaults to current month.

        Returns:
            Dictionary with totalRequests, successCount, clientErrorCount, quota, and endpoints breakdown.
            For accounts with unlimited API requests, `quota.limit` and `quota.remaining` are `None` (null),
            and `quota.unlimited` is True.
        """
        params: dict[str, Any] = {}
        if period is not None:
            params["period"] = period
        params.update(kwargs)

        return self._http.get("/usage", params=params)

    def get_project(self) -> dict[str, Any]:
        """Retrieve authenticated developer project profile, environment, and tier quota limits.

        Returns:
            Dictionary with project ID, name, slug, environment (TEST or LIVE), tier, and limits.
            For unlimited plan tiers, numeric limits in `limits` (e.g. `moduleCreditLimit`,
            `monthlyApiRequests`) are `None` (null), with corresponding `*Unlimited` flags set to True.
        """
        return self._http.get("/project")
