"""Nexora Python SDK Type Definitions.

Provides TypedDict definitions for API responses, including normalized limit and quota structures.
"""

from __future__ import annotations

from typing import Optional, TypedDict


class LimitSummary(TypedDict):
    """Normalized usage limit representation.
    
    When an account possesses an unlimited entitlement, `limit` and `remaining`
    are `None` (null in JSON), and `unlimited` is True.
    For finite tiers, `remaining` is guaranteed to be >= 0 (never negative).
    """

    limit: Optional[int]
    used: int
    remaining: Optional[int]
    unlimited: bool
    overLimit: bool


class PlanLimits(TypedDict, total=False):
    """Developer tier entitlement limits.
    
    For unlimited resources (such as monthly API requests or module credits in enterprise tiers),
    the integer limit is `None` (null in JSON) and the corresponding `*Unlimited` flag is True.
    """

    monthlyApiRequests: Optional[int]
    monthlyApiRequestsUnlimited: bool
    maxLiveOrganizations: int
    maxCustomDomains: int
    moduleCreditLimit: Optional[int]
    moduleCreditUnlimited: bool
    maxKeys: int
    maxWebhooks: int
    rateLimitRps: int


class ModuleCreditSummary(TypedDict, total=False):
    """Credit balance and breakdown for modular capabilities.
    
    For unlimited plans, `limit`, `totalCredits`, and `remaining` are `None`
    and `unlimited` is True.
    """

    totalCredits: Optional[int]
    usedCredits: int
    remainingCredits: Optional[int]
    limit: Optional[int]
    used: int
    remaining: Optional[int]
    unlimited: bool
    overLimit: bool
