"""Nexora Webhook Endpoints Resource.

Registers HTTPS webhook endpoints, configures event subscriptions, rotates
HMAC signing secrets, dispatches test pings, and verifies incoming signatures.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import TYPE_CHECKING, Any, Optional, Sequence, Union

if TYPE_CHECKING:
    from .._http import HttpClient


class WebhooksResource:
    """Resource for managing developer webhook endpoints and verifying signatures."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def create(
        self,
        url: str,
        events: Optional[Sequence[str]] = None,
        description: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Register a new webhook endpoint to receive real-time signed event dispatches.

        The signing secret (whsec_...) is returned only once upon creation and must be stored safely.

        Args:
            url: HTTPS destination URL (e.g. 'https://api.example.com/webhooks/nexora').
            events: List of event types to subscribe to (e.g. ['organization.created', 'user.created']).
            description: Optional description of this receiver's purpose.
            name: Optional display name for the endpoint.

        Returns:
            Dictionary containing the registered endpoint and its show-once plain signing secret.
        """
        payload: dict[str, Any] = {
            "url": url,
            "events": list(events) if events is not None else ["organization.provisioned"],
        }
        if description is not None:
            payload["description"] = description
        if name is not None:
            payload["name"] = name
        payload.update(kwargs)

        return self._http.post("/webhook-endpoints", json_data=payload)

    def list(self) -> list[dict[str, Any]]:
        """List registered webhook endpoints for the authenticated project."""
        return self._http.get("/webhook-endpoints")

    def get(self, id: str) -> dict[str, Any]:
        """Retrieve webhook endpoint configuration and delivery stats by ID."""
        return self._http.get(f"/webhook-endpoints/{id}")

    def retrieve(self, id: str) -> dict[str, Any]:
        """Alias for get(id)."""
        return self.get(id)

    def update(
        self,
        id: str,
        url: Optional[str] = None,
        events: Optional[Sequence[str]] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update a registered webhook endpoint (URL, subscribed events, description, status)."""
        payload: dict[str, Any] = {}
        if url is not None:
            payload["url"] = url
        if events is not None:
            payload["events"] = list(events)
        if description is not None:
            payload["description"] = description
        if status is not None:
            payload["status"] = status
        payload.update(kwargs)

        return self._http.patch(f"/webhook-endpoints/{id}", json_data=payload)

    def rotate_secret(self, id: str) -> dict[str, Any]:
        """Rotate the signing secret for a registered webhook endpoint.

        Immediately invalidates the previous secret and returns the new secret (show-once).
        """
        return self._http.post(f"/webhook-endpoints/{id}/rotate-secret", json_data={})

    def disable(self, id: str) -> dict[str, Any]:
        """Disable a webhook endpoint to pause event dispatches."""
        return self._http.post(f"/webhook-endpoints/{id}/disable", json_data={})

    def test(
        self,
        id: str,
        event_type: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a synthetic test ping event (webhook.test) to verify endpoint connectivity."""
        payload: dict[str, Any] = {}
        if event_type is not None:
            payload["eventType"] = event_type
        payload.update(kwargs)

        return self._http.post(f"/webhook-endpoints/{id}/test", json_data=payload)

    def delete(self, id: str) -> dict[str, Any]:
        """Delete a registered webhook endpoint."""
        return self._http.delete(f"/webhook-endpoints/{id}")

    @staticmethod
    def verify_signature(
        payload: Union[str, bytes],
        header: str,
        secret: str,
        tolerance_seconds: int = 300,
    ) -> bool:
        """Cryptographically verify an incoming webhook signature.

        Matches the canonical Nexora backend WebhookSigningService algorithm.
        Uses HMAC-SHA256 and constant-time string comparison (hmac.compare_digest).

        Supports:
        1. Standard Nexora signature format: "t=1700000000,v1=abcdef..."
        2. Direct HMAC hash: "v1=abcdef..." or raw hex

        Args:
            payload: Raw request body as bytes or string.
            header: The 'X-Nexora-Signature' or 'Nexora-Signature' header string.
            secret: The endpoint's HMAC signing secret (whsec_...).
            tolerance_seconds: Maximum allowed clock skew in seconds (default 300 = 5 minutes).
                Set to 0 to disable timestamp verification.

        Returns:
            True if the signature is authentic and within the tolerance window, False otherwise.
        """
        if not payload or not header or not secret:
            return False

        if isinstance(payload, bytes):
            try:
                payload_str = payload.decode("utf-8")
            except UnicodeDecodeError:
                return False
        else:
            payload_str = str(payload)

        timestamp: Optional[int] = None
        signature_hash: Optional[str] = None

        if "t=" in header and "v1=" in header:
            parts = header.split(",")
            for part in parts:
                item = part.strip()
                if "=" in item:
                    k, v = item.split("=", 1)
                    k = k.strip()
                    v = v.strip()
                    if k == "t":
                        try:
                            timestamp = int(v)
                        except ValueError:
                            return False
                    elif k == "v1":
                        signature_hash = v
        elif header.startswith("v1="):
            signature_hash = header[3:].strip()
        else:
            signature_hash = header.strip()

        if not signature_hash:
            return False

        # Verify timestamp tolerance window to protect against replay attacks
        if timestamp is not None and tolerance_seconds > 0:
            now = int(time.time())
            if abs(now - timestamp) > tolerance_seconds:
                return False

        secret_bytes = secret.encode("utf-8")

        # 1. Standard timestamped HMAC: HMAC-SHA256(f"{timestamp}.{payload}")
        if timestamp is not None:
            signed_data = f"{timestamp}.{payload_str}".encode("utf-8")
            expected_hash = hmac.new(secret_bytes, signed_data, hashlib.sha256).hexdigest()
            if hmac.compare_digest(signature_hash.lower(), expected_hash.lower()):
                return True

        # 2. Direct fallback HMAC over raw payload without timestamp prefix
        direct_data = payload_str.encode("utf-8")
        direct_expected_hash = hmac.new(secret_bytes, direct_data, hashlib.sha256).hexdigest()
        if hmac.compare_digest(signature_hash.lower(), direct_expected_hash.lower()):
            return True

        return False
