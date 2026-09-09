"""Integration Test Suite for Nexora Python SDK.

Supports two execution modes:
1. End-to-end simulated Sandbox developer journey (enabled by default).
2. Live Sandbox TEST environment against a real Nexora instance
   (enabled only when NEXORA_RUN_INTEGRATION_TESTS="1" is set in the environment).

Protections:
- Never executes production operations.
- Strictly guards against and rejects 'nx_live_' production keys in automated test suites.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any

import httpx
import pytest

from nexorams import Nexora, NexoraError, ValidationError


class TestSandboxDeveloperJourneyMock:
    """Simulates the full end-to-end developer onboarding and provisioning journey."""

    @pytest.fixture
    def sandbox_env(self) -> tuple[Nexora, list[dict[str, Any]]]:
        received_requests: list[dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = None
            if request.content:
                try:
                    body = json.loads(request.content.decode("utf-8"))
                except Exception:
                    body = request.content.decode("utf-8")

            path = request.url.path
            method = request.method
            req_id = f"req_sb_{os.urandom(6).hex()}"

            received_requests.append({
                "method": method,
                "path": path,
                "headers": dict(request.headers),
                "body": body,
            })

            headers = {
                "content-type": "application/json",
                "x-request-id": req_id,
            }

            # 1. Provision organization: POST /developer/v1/organizations
            if method == "POST" and path.endswith("/organizations"):
                if not body or not body.get("owner", {}).get("email"):
                    return httpx.Response(
                        400,
                        headers=headers,
                        json={
                            "error": {
                                "code": "INVALID_OWNER_EMAIL",
                                "message": "A valid owner email address is required.",
                                "requestId": req_id,
                            }
                        },
                    )

                return httpx.Response(
                    201,
                    headers=headers,
                    json={
                        "success": True,
                        "data": {
                            "organizationId": "org_sb_66da18b4e72391001a4f0099",
                            "id": "org_sb_66da18b4e72391001a4f0099",
                            "name": body.get("name", "").upper(),
                            "type": body.get("type", "").lower(),
                            "environment": "TEST",
                            "primaryDomain": f"{body.get('name', '').lower().replace(' ', '-')}.nexoragms.com",
                            "portalUrl": f"https://{body.get('name', '').lower().replace(' ', '-')}.nexoragms.com",
                            "status": "ACTIVE",
                            "ownerUser": {
                                "firstName": body.get("owner", {}).get("firstName"),
                                "lastName": body.get("owner", {}).get("lastName"),
                                "email": body.get("owner", {}).get("email"),
                            },
                            "subscription": {
                                "plan": "trial",
                                "status": "TRIAL",
                                "trialEndsAt": "2026-10-09T00:00:00.000Z",
                            },
                        },
                    },
                )

            # 2. Retrieve organization: GET /developer/v1/organizations/:id
            if method == "GET" and "/organizations/org_sb_" in path:
                org_id = path.split("/")[-1]
                return httpx.Response(
                    200,
                    headers=headers,
                    json={
                        "data": {
                            "id": org_id,
                            "name": "BRIGHT FUTURE ACADEMY",
                            "type": "SCHOOL",
                            "environment": "TEST",
                            "status": "ACTIVE",
                            "portalUrl": "https://bright-future-academy.nexoragms.com",
                            "subscription": {
                                "status": "TRIAL",
                                "trialEndsAt": "2026-10-09T00:00:00.000Z",
                            },
                        }
                    },
                )

            # 3. Modules catalog: GET /developer/v1/modules
            if method == "GET" and path.endswith("/modules"):
                return httpx.Response(
                    200,
                    headers=headers,
                    json={
                        "data": [
                            {"key": "school_attendance", "name": "Attendance", "organizationTypes": ["school"]},
                            {"key": "school_grades", "name": "Gradebook", "organizationTypes": ["school"]},
                            {"key": "school_fees", "name": "Fee Collection", "organizationTypes": ["school"]},
                        ]
                    },
                )

            # 4. Webhook registration: POST /developer/v1/webhook-endpoints
            if method == "POST" and path.endswith("/webhook-endpoints"):
                return httpx.Response(
                    201,
                    headers=headers,
                    json={
                        "data": {
                            "id": "wh_sb_555",
                            "url": body.get("url"),
                            "events": body.get("events"),
                            "secret": "whsec_sandbox_test_secret_789",
                            "status": "ACTIVE",
                        }
                    },
                )

            return httpx.Response(404, headers=headers, json={"error": {"code": "NOT_FOUND", "message": "Not Found"}})

        client = Nexora(
            api_key="nx_test_sandbox_credential_001",
            base_url="https://api.nexoragms.com/developer/v1",
        )
        client._http._session = httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url=client.base_url,
            headers={
                "Authorization": f"Bearer {client.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "nexorams-python/1.0.0",
            },
        )

        return client, received_requests

    def test_step_1_initialize_client_with_test_key(self, sandbox_env: tuple[Nexora, list[dict[str, Any]]]) -> None:
        client, _ = sandbox_env
        assert client.environment == "sandbox"
        assert client.api_key == "nx_test_sandbox_credential_001"

    def test_step_2_provision_sandbox_organization_with_idempotency(self, sandbox_env: tuple[Nexora, list[dict[str, Any]]]) -> None:
        client, requests = sandbox_env
        org = client.organizations.create(
            name="Bright Future Academy",
            type="SCHOOL",
            country="NG",
            owner={
                "firstName": "John",
                "lastName": "Doe",
                "email": "john.doe@brightfuture.edu.ng",
            },
            idempotency_key="idemp_bright_future_001",
        )

        assert org["id"] == "org_sb_66da18b4e72391001a4f0099"
        assert org["name"] == "BRIGHT FUTURE ACADEMY"
        assert org["environment"] == "TEST"
        assert org["status"] == "ACTIVE"
        assert org["subscription"]["status"] == "TRIAL"

        last_req = requests[-1]
        assert last_req["headers"]["authorization"] == "Bearer nx_test_sandbox_credential_001"
        assert last_req["headers"]["idempotency-key"] == "idemp_bright_future_001"

    def test_step_3_retrieve_organization_by_id(self, sandbox_env: tuple[Nexora, list[dict[str, Any]]]) -> None:
        client, _ = sandbox_env
        org = client.organizations.get("org_sb_66da18b4e72391001a4f0099")
        assert org["id"] == "org_sb_66da18b4e72391001a4f0099"
        assert org["type"] == "SCHOOL"
        assert org["status"] == "ACTIVE"

    def test_step_4_fetch_sector_module_catalog(self, sandbox_env: tuple[Nexora, list[dict[str, Any]]]) -> None:
        client, _ = sandbox_env
        modules = client.modules.list(organization_type="school")
        assert isinstance(modules, list)
        assert len(modules) >= 3
        assert modules[0]["key"] == "school_attendance"

    def test_step_5_register_webhook_and_verify_signature(self, sandbox_env: tuple[Nexora, list[dict[str, Any]]]) -> None:
        client, _ = sandbox_env
        webhook = client.webhooks.create(
            url="https://example.com/webhooks/nexora",
            events=["organization.created", "user.created"],
        )
        assert webhook["id"] == "wh_sb_555"
        assert webhook["secret"] == "whsec_sandbox_test_secret_789"

        # Simulate signed webhook event received by developer backend
        simulated_event = json.dumps({
            "id": "evt_sb_123",
            "type": "organization.created",
            "data": {"organizationId": "org_sb_66da18b4e72391001a4f0099"},
        })
        now = int(time.time())
        to_sign = f"{now}.{simulated_event}".encode("utf-8")
        sig = hmac.new(webhook["secret"].encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
        header = f"t={now},v1={sig}"

        is_valid = Nexora.verify_webhook_signature(
            payload=simulated_event,
            header=header,
            secret=webhook["secret"],
        )
        assert is_valid is True

    def test_step_6_error_reporting_and_correlation_id(self, sandbox_env: tuple[Nexora, list[dict[str, Any]]]) -> None:
        client, _ = sandbox_env
        with pytest.raises(ValidationError) as exc_info:
            client.organizations.create(
                name="Invalid School",
                type="SCHOOL",
                owner={"firstName": "No", "lastName": "Email", "email": ""},
            )

        err = exc_info.value
        assert err.status_code == 400
        assert err.code == "INVALID_OWNER_EMAIL"
        assert err.request_id is not None
        assert err.request_id.startswith("req_sb_")


class TestOptionalLiveIntegration:
    """Optional tests executed against a live running Nexora instance.

    Guarded by NEXORA_RUN_INTEGRATION_TESTS=1.
    Strictly forbids running destructive tests with 'nx_live_' production credentials.
    """

    def test_live_sandbox_execution(self) -> None:
        run_live = os.environ.get("NEXORA_RUN_INTEGRATION_TESTS", "").strip() == "1"
        if not run_live:
            pytest.skip("Skipping live integration tests: NEXORA_RUN_INTEGRATION_TESTS != '1'")

        live_key = os.environ.get("NEXORA_API_KEY", "")
        if not live_key:
            pytest.skip("NEXORA_API_KEY is not configured")

        if live_key.startswith("nx_live_"):
            pytest.fail("CRITICAL SAFETY GUARD: Live integration test suite must NEVER run with a production 'nx_live_' key.")

        base_url = os.environ.get("NEXORA_API_BASE_URL", "https://api.nexoragms.com/developer/v1")
        client = Nexora(api_key=live_key, base_url=base_url)

        # Basic non-destructive read
        modules = client.modules.list()
        assert isinstance(modules, list)
