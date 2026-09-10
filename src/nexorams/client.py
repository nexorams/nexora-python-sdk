"""Nexora Official Python Client.

Primary entrypoint for the Nexora Developer Platform.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from ._http import DEFAULT_BASE_URL, DEFAULT_TIMEOUT_SECONDS, HttpClient
from .exceptions import ValidationError
from .resources.deliveries import WebhookDeliveriesResource
from .resources.domains import DomainsResource
from .resources.modules import ModulesResource
from .resources.organizations import OrganizationsResource
from .resources.plans import PlansResource
from .resources.subscriptions import SubscriptionsResource
from .resources.usage import UsageResource
from .resources.users import UsersResource
from .resources.webhooks import WebhooksResource
from .resources.school import SchoolResource
from .resources.hospital import HospitalResource
from .resources.hotel import HotelResource
from .resources.pharmacy import PharmacyResource
from .resources.company import CompanyResource


def _mask_api_key(key: str) -> str:
    """Mask secret API key for safe display in repr and logs."""
    if not key or len(key) < 12:
        return "••••••••"
    prefix = key[:8]  # e.g. "nx_test_" or "nx_live_"
    suffix = key[-4:]
    return f"{prefix}••••••••{suffix}"


class Nexora:
    """Official Python Client for the Nexora Developer Platform.

    Provides access to tenant organization provisioning, users, modular feature
    toggles, subscription plans, custom domains, and signed webhook deliveries.

    Example:
        ```python
        import os
        from nexorams import Nexora

        nexora = Nexora(api_key=os.environ["NEXORA_API_KEY"])

        # Provision a sandbox hospital
        org = nexora.organizations.create(
            name="Apex Specialist Hospital",
            type="HOSPITAL",
            country="NG",
            owner={
                "firstName": "Clara",
                "lastName": "Oswald",
                "email": "clara@example.com",
            },
            idempotency_key="apex-hospital-001",
        )
        ```
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        environment: Optional[str] = None,
    ) -> None:
        """Initialize the Nexora client.

        Args:
            api_key: Nexora Developer API Key ('nx_test_...' for Sandbox or 'nx_live_...' for Live).
            base_url: Custom API base URL (defaults to 'https://api.nexoragms.com/developer/v1').
            timeout: Request timeout in seconds (default 30.0).
            environment: Optional environment label ('sandbox' or 'live'). Inferred from api_key by default.
        """
        if not api_key or not isinstance(api_key, str) or not api_key.strip():
            raise ValidationError(
                message="API key is required to initialize the Nexora client.",
                code="MISSING_API_KEY",
                status_code=400,
            )

        trimmed_key = api_key.strip()
        if not trimmed_key.startswith("nx_test_") and not trimmed_key.startswith("nx_live_"):
            raise ValidationError(
                message="Invalid API key prefix. Expected 'nx_test_' for sandbox or 'nx_live_' for live.",
                code="INVALID_API_KEY_FORMAT",
                status_code=400,
            )

        self._api_key = trimmed_key
        self.environment = environment or ("live" if trimmed_key.startswith("nx_live_") else "sandbox")
        raw_base = base_url or DEFAULT_BASE_URL
        self.base_url = raw_base.rstrip("/")
        self.timeout = float(timeout)

        # Initialize internal shared HTTP client
        self._http = HttpClient(
            api_key=self._api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

        # Initialize canonical public resources
        self.organizations = OrganizationsResource(self._http)
        self.users = UsersResource(self._http)
        self.modules = ModulesResource(self._http)
        self.plans = PlansResource(self._http)
        self.subscriptions = SubscriptionsResource(self._http)
        self.domains = DomainsResource(self._http)
        self.webhooks = WebhooksResource(self._http)
        self.deliveries = WebhookDeliveriesResource(self._http)
        self.usage = UsageResource(self._http)

        # Sector-specific resources
        self.school = SchoolResource(self._http)
        self.hospital = HospitalResource(self._http)
        self.hotel = HotelResource(self._http)
        self.pharmacy = PharmacyResource(self._http)
        self.company = CompanyResource(self._http)

    @property
    def api_key(self) -> str:
        """Access authenticated API key."""
        return self._api_key

    def close(self) -> None:
        """Close underlying HTTP connections."""
        self._http.close()

    def __enter__(self) -> Nexora:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        # Strictly prevent API key credential leakage
        return (
            f"Nexora("
            f"environment={self.environment!r}, "
            f"base_url={self.base_url!r}, "
            f"api_key={_mask_api_key(self._api_key)!r})"
        )

    @staticmethod
    def verify_webhook_signature(
        payload: Union[str, bytes],
        header: str,
        secret: str,
        tolerance_seconds: int = 300,
    ) -> bool:
        """Cryptographically verify an incoming webhook signature using HMAC-SHA256.

        Args:
            payload: Raw webhook body string or bytes.
            header: Signature header string ('X-Nexora-Signature' or 'Nexora-Signature').
            secret: Webhook endpoint HMAC secret key ('whsec_...').
            tolerance_seconds: Maximum allowed clock skew in seconds (default 300).

        Returns:
            True if valid, False otherwise.
        """
        return WebhooksResource.verify_signature(
            payload=payload,
            header=header,
            secret=secret,
            tolerance_seconds=tolerance_seconds,
        )

    # Alias for JS/TS compatibility
    verifyWebhookSignature = verify_webhook_signature


# Named alias for convenience
NexoraClient = Nexora

__all__ = ["Nexora", "NexoraClient"]
