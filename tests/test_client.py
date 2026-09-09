"""Comprehensive Unit Tests for Nexora Python SDK.

Covers client initialization, secret redaction, cryptographic webhook signature verification,
error mapping, HTTP transport, and all 9 platform resources.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import httpx
import pytest

from nexorams import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    ConflictError,
    Nexora,
    NexoraClient,
    NexoraError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ValidationError,
)
from nexorams.resources import (
    DomainsResource,
    ModulesResource,
    OrganizationsResource,
    PlansResource,
    SubscriptionsResource,
    UsageResource,
    UsersResource,
    WebhookDeliveriesResource,
    WebhooksResource,
)


class TestClientInitialization:
    """Validates constructor parameters, prefixes, environment inference, and resource binding."""

    def test_missing_api_key_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Nexora(api_key="")
        assert exc_info.value.code == "MISSING_API_KEY"
        assert exc_info.value.status_code == 400

    def test_whitespace_api_key_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Nexora(api_key="   ")
        assert exc_info.value.code == "MISSING_API_KEY"

    def test_invalid_prefix_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Nexora(api_key="invalid_prefix_12345")
        assert exc_info.value.code == "INVALID_API_KEY_FORMAT"
        assert exc_info.value.status_code == 400

    def test_infers_sandbox_environment_from_test_key(self) -> None:
        client = Nexora(api_key="nx_test_sample_sandbox_key_123")
        assert client.environment == "sandbox"
        assert client.base_url == "https://api.nexoragms.com/developer/v1"

    def test_infers_live_environment_from_live_key(self) -> None:
        client = Nexora(api_key="nx_live_sample_live_key_456")
        assert client.environment == "live"
        assert client.base_url == "https://api.nexoragms.com/developer/v1"

    def test_trims_whitespace_from_api_key(self) -> None:
        client = Nexora(api_key="  nx_test_padded_key_789  ")
        assert client.api_key == "nx_test_padded_key_789"

    def test_custom_base_url_trims_trailing_slashes(self) -> None:
        client = Nexora(
            api_key="nx_test_sample",
            base_url="http://localhost:5000/developer/v1///",
        )
        assert client.base_url == "http://localhost:5000/developer/v1"

    def test_named_export_nexora_client_alias_identical(self) -> None:
        assert Nexora is NexoraClient

    def test_exposes_all_platform_resources(self) -> None:
        client = Nexora(api_key="nx_test_sample")
        assert isinstance(client.organizations, OrganizationsResource)
        assert isinstance(client.users, UsersResource)
        assert isinstance(client.modules, ModulesResource)
        assert isinstance(client.plans, PlansResource)
        assert isinstance(client.subscriptions, SubscriptionsResource)
        assert isinstance(client.domains, DomainsResource)
        assert isinstance(client.webhooks, WebhooksResource)
        assert isinstance(client.deliveries, WebhookDeliveriesResource)
        assert isinstance(client.usage, UsageResource)

    def test_context_manager_closes_cleanly(self) -> None:
        with Nexora(api_key="nx_test_sample") as client:
            assert client.environment == "sandbox"
            assert not client._http._session.is_closed
        assert client._http._session.is_closed


class TestSecurityAndSecretRedaction:
    """Ensures raw API keys and credentials are never exposed in representations or exceptions."""

    def test_client_repr_masks_api_key(self) -> None:
        raw_secret = "nx_test_SUPER_SECRET_VALUE_99999999"
        client = Nexora(api_key=raw_secret)
        repr_str = repr(client)
        assert "SUPER_SECRET_VALUE" not in repr_str
        assert "nx_test_••••••••" in repr_str

    def test_error_message_and_repr_do_not_contain_secret(self) -> None:
        secret = "nx_test_SECRET_TOKEN_12345"
        err = NexoraError(
            message="Provisioning failed",
            code="TEST_ERROR",
            status_code=400,
            request_id="req_98765",
            details={"safe": "data"},
        )
        assert secret not in str(err)
        assert secret not in repr(err)
        serialized = json.dumps(err.to_dict())
        assert secret not in serialized


class TestWebhookSignatureVerification:
    """Verifies HMAC-SHA256 signature verification matching canonical backend WebhookSigningService."""

    secret = "whsec_test_secret_key_abcdef123456"
    payload = json.dumps({"id": "evt_123", "type": "organization.created", "data": {"name": "Acme Academy"}})

    def test_verifies_valid_standard_header(self) -> None:
        now = int(time.time())
        to_sign = f"{now}.{self.payload}".encode("utf-8")
        sig = hmac.new(self.secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
        header = f"t={now},v1={sig}"

        assert Nexora.verify_webhook_signature(self.payload, header, self.secret, tolerance_seconds=300) is True

    def test_verifies_valid_bytes_payload(self) -> None:
        now = int(time.time())
        payload_bytes = self.payload.encode("utf-8")
        to_sign = f"{now}.{self.payload}".encode("utf-8")
        sig = hmac.new(self.secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
        header = f"t={now},v1={sig}"

        assert Nexora.verify_webhook_signature(payload_bytes, header, self.secret, tolerance_seconds=300) is True

    def test_verifies_direct_v1_header_format(self) -> None:
        sig = hmac.new(self.secret.encode("utf-8"), self.payload.encode("utf-8"), hashlib.sha256).hexdigest()
        header = f"v1={sig}"

        assert Nexora.verify_webhook_signature(self.payload, header, self.secret, tolerance_seconds=300) is True

    def test_rejects_tampered_payload(self) -> None:
        now = int(time.time())
        to_sign = f"{now}.{self.payload}".encode("utf-8")
        sig = hmac.new(self.secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
        header = f"t={now},v1={sig}"

        tampered = json.dumps({"id": "evt_999", "type": "tampered"})
        assert Nexora.verify_webhook_signature(tampered, header, self.secret, tolerance_seconds=300) is False

    def test_rejects_stale_timestamp_beyond_tolerance(self) -> None:
        stale_time = int(time.time()) - 600  # 10 minutes ago
        to_sign = f"{stale_time}.{self.payload}".encode("utf-8")
        sig = hmac.new(self.secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
        header = f"t={stale_time},v1={sig}"

        assert Nexora.verify_webhook_signature(self.payload, header, self.secret, tolerance_seconds=300) is False

    def test_rejects_wrong_secret(self) -> None:
        now = int(time.time())
        to_sign = f"{now}.{self.payload}".encode("utf-8")
        sig = hmac.new(self.secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
        header = f"t={now},v1={sig}"

        assert Nexora.verify_webhook_signature(self.payload, header, "wrong_secret", tolerance_seconds=300) is False

    def test_rejects_empty_inputs_gracefully(self) -> None:
        assert Nexora.verify_webhook_signature("", "v1=123", self.secret) is False
        assert Nexora.verify_webhook_signature(self.payload, "", self.secret) is False
        assert Nexora.verify_webhook_signature(self.payload, "v1=123", "") is False


@pytest.fixture
def mock_client() -> tuple[Nexora, dict[str, Any]]:
    state: dict[str, Any] = {
        "last_request": None,
        "response_status": 200,
        "response_headers": {
            "content-type": "application/json",
            "x-request-id": "req_unit_mock_12345",
        },
        "response_body": {"data": {}},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        body = None
        if request.content:
            try:
                body = json.loads(request.content.decode("utf-8"))
            except Exception:
                body = request.content.decode("utf-8")

        state["last_request"] = {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "body": body,
        }

        resp_body = state["response_body"]
        content = json.dumps(resp_body).encode("utf-8") if isinstance(resp_body, (dict, list)) else str(resp_body).encode("utf-8")

        return httpx.Response(
            status_code=state["response_status"],
            headers=state["response_headers"],
            content=content,
        )

    client = Nexora(api_key="nx_test_mockkey123")
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

    return client, state


class TestMockHttpTransportAndResources:
    """Tests HTTP transport, Bearer authentication headers, idempotency keys, error mapping, and resources."""


    def test_bearer_token_and_user_agent_headers(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_body"] = {"data": []}

        client.organizations.list()
        last = state["last_request"]
        assert last["headers"]["authorization"] == "Bearer nx_test_mockkey123"
        assert last["headers"]["user-agent"] == "nexorams-python/1.0.0"
        assert last["url"].endswith("/developer/v1/organizations")

    def test_idempotency_key_header_injection(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 201
        state["response_body"] = {
            "data": {"id": "org_123", "name": "Pinecrest Hospital", "status": "ACTIVE"}
        }

        result = client.organizations.create(
            name="Pinecrest Hospital",
            type="HOSPITAL",
            country="US",
            owner={"firstName": "Sarah", "lastName": "Connor", "email": "admin@pinecrest.org"},
            idempotency_key="idemp_py_unit_001",
        )

        last = state["last_request"]
        assert last["headers"]["idempotency-key"] == "idemp_py_unit_001"
        assert result["id"] == "org_123"
        assert result["name"] == "Pinecrest Hospital"

    def test_error_parsing_400_bad_request(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 400
        state["response_body"] = {
            "error": {
                "message": "Owner email is required",
                "code": "INVALID_OWNER_EMAIL",
                "requestId": "req_unit_mock_12345",
            }
        }

        with pytest.raises(ValidationError) as exc_info:
            client.organizations.create(
                name="Bad School",
                type="SCHOOL",
                owner={"firstName": "A", "lastName": "B", "email": ""},
            )

        err = exc_info.value
        assert err.status_code == 400
        assert err.code == "INVALID_OWNER_EMAIL"
        assert err.message == "Owner email is required"
        assert err.request_id == "req_unit_mock_12345"

    def test_error_parsing_401_unauthorized(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 401
        state["response_body"] = {
            "error": {"message": "Invalid API key credentials provided.", "code": "INVALID_API_KEY"}
        }

        with pytest.raises(AuthenticationError) as exc_info:
            client.organizations.list()
        assert exc_info.value.status_code == 401
        assert exc_info.value.code == "INVALID_API_KEY"

    def test_error_parsing_403_forbidden(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 403
        state["response_body"] = {
            "error": {"message": "Lacks required scope organizations.create", "code": "INSUFFICIENT_SCOPE"}
        }

        with pytest.raises(PermissionDeniedError) as exc_info:
            client.organizations.create(
                name="Forbidden Org",
                type="SCHOOL",
                owner={"firstName": "A", "lastName": "B", "email": "a@b.com"},
            )
        assert exc_info.value.status_code == 403
        assert exc_info.value.code == "INSUFFICIENT_SCOPE"

    def test_error_parsing_404_not_found(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 404
        state["response_body"] = {
            "error": {"message": "Organization not found.", "code": "ORGANIZATION_NOT_FOUND"}
        }

        with pytest.raises(NotFoundError) as exc_info:
            client.organizations.get("org_missing")
        assert exc_info.value.status_code == 404
        assert exc_info.value.code == "ORGANIZATION_NOT_FOUND"

    def test_error_parsing_409_conflict(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 409
        state["response_body"] = {
            "error": {"message": "Idempotency key payload mismatch", "code": "IDEMPOTENCY_CONFLICT"}
        }

        with pytest.raises(ConflictError) as exc_info:
            client.organizations.create(
                name="Conflict Org",
                type="SCHOOL",
                owner={"firstName": "A", "lastName": "B", "email": "a@b.com"},
                idempotency_key="k1",
            )
        assert exc_info.value.status_code == 409
        assert exc_info.value.code == "IDEMPOTENCY_CONFLICT"

    def test_error_parsing_429_rate_limit(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 429
        state["response_headers"]["retry-after"] = "60"
        state["response_body"] = {
            "error": {"message": "Rate limit exceeded.", "code": "RATE_LIMIT_EXCEEDED"}
        }

        with pytest.raises(RateLimitError) as exc_info:
            client.organizations.list()
        assert exc_info.value.status_code == 429
        assert exc_info.value.code == "RATE_LIMIT_EXCEEDED"
        assert exc_info.value.retry_after == 60

    def test_organizations_lifecycle(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client

        # Update
        state["response_status"] = 200
        state["response_body"] = {"data": {"id": "org_123", "name": "UPDATED ACADEMY"}}
        res_update = client.organizations.update("org_123", name="UPDATED ACADEMY", primary_color="#0284c7")
        assert res_update["name"] == "UPDATED ACADEMY"
        assert state["last_request"]["method"] == "PATCH"
        assert state["last_request"]["body"] == {"name": "UPDATED ACADEMY", "primaryColor": "#0284c7"}

        # Update modules
        state["response_body"] = {"data": {"organizationId": "org_123", "activeFeatures": ["school_attendance"]}}
        res_modules = client.organizations.update_modules("org_123", ["school_attendance"])
        assert res_modules["activeFeatures"] == ["school_attendance"]

        # Get subscription
        state["response_body"] = {"data": {"status": "TRIAL", "planCode": "trial"}}
        res_sub = client.organizations.get_subscription("org_123")
        assert res_sub["status"] == "TRIAL"

        # Domains
        state["response_body"] = {"data": [{"id": "dom_1", "hostname": "portal.myorg.com"}]}
        domains = client.organizations.get_domains("org_123")
        assert domains[0]["hostname"] == "portal.myorg.com"

        state["response_status"] = 201
        state["response_body"] = {"data": {"id": "dom_2", "hostname": "new.myorg.com"}}
        new_dom = client.organizations.add_domain("org_123", "new.myorg.com")
        assert new_dom["hostname"] == "new.myorg.com"

        state["response_status"] = 200
        state["response_body"] = {"data": {"verified": True, "status": "VERIFIED"}}
        verified = client.organizations.verify_domain("org_123", "dom_2")
        assert verified["verified"] is True

    def test_users_resource(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 201
        state["response_body"] = {
            "data": {"id": "usr_1", "firstName": "Jane", "lastName": "Doe", "email": "jane@org.com", "role": "teacher"}
        }

        user = client.users.create(
            organization_id="org_123",
            first_name="Jane",
            last_name="Doe",
            email="jane@org.com",
            role="teacher",
        )
        assert user["email"] == "jane@org.com"
        assert state["last_request"]["method"] == "POST"

        state["response_status"] = 200
        state["response_body"] = {"data": [user]}
        users = client.users.list("org_123", role="teacher")
        assert len(users) == 1
        assert "role=teacher" in state["last_request"]["url"]

    def test_modules_resource(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 200
        state["response_body"] = {
            "data": [{"key": "school_attendance", "name": "Attendance", "organizationTypes": ["school"]}]
        }

        modules = client.modules.list(organization_type="school")
        assert len(modules) == 1
        assert modules[0]["key"] == "school_attendance"
        assert "organizationType=school" in state["last_request"]["url"]

        state["response_body"] = {"data": {"organizationId": "org_1", "activeFeatures": ["school_attendance"]}}
        updated = client.modules.update("org_1", ["school_attendance"])
        assert updated["activeFeatures"] == ["school_attendance"]

    def test_plans_resource(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 200
        state["response_body"] = {"data": [{"name": "School Starter", "slug": "school-starter"}]}

        plans = client.plans.list(sector="school")
        assert plans[0]["slug"] == "school-starter"
        assert "organizationType=school" in state["last_request"]["url"]

    def test_subscriptions_resource(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 200
        state["response_body"] = {"data": {"organizationId": "org_123", "status": "TRIAL"}}

        sub = client.subscriptions.get("org_123")
        assert sub["status"] == "TRIAL"
        assert state["last_request"]["url"].endswith("/organizations/org_123/subscription")

    def test_domains_resource(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 200
        state["response_body"] = {"data": [{"id": "dom_1", "hostname": "custom.domain.com"}]}

        domains = client.domains.list("org_123")
        assert domains[0]["hostname"] == "custom.domain.com"

        state["response_status"] = 201
        state["response_body"] = {"data": {"id": "dom_2", "hostname": "portal.domain.com", "status": "PENDING"}}
        created = client.domains.create("org_123", hostname="portal.domain.com")
        assert created["status"] == "PENDING"

        state["response_status"] = 200
        state["response_body"] = {"data": {"verified": True, "status": "VERIFIED"}}
        verified = client.domains.verify("org_123", "dom_2")
        assert verified["verified"] is True

    def test_webhooks_resource(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 201
        state["response_body"] = {
            "data": {
                "id": "wh_101",
                "url": "https://example.com/webhooks",
                "events": ["organization.created"],
                "secret": "whsec_plain_123",
            }
        }

        created = client.webhooks.create(
            url="https://example.com/webhooks",
            events=["organization.created"],
        )
        assert created["id"] == "wh_101"
        assert created["secret"] == "whsec_plain_123"

        state["response_status"] = 200
        state["response_body"] = {"data": [created]}
        listed = client.webhooks.list()
        assert len(listed) == 1

        state["response_body"] = {"data": created}
        got = client.webhooks.get("wh_101")
        assert got["id"] == "wh_101"

        state["response_body"] = {"data": {**created, "url": "https://example.com/updated"}}
        updated = client.webhooks.update("wh_101", url="https://example.com/updated")
        assert updated["url"] == "https://example.com/updated"

        state["response_body"] = {"data": {"secret": "whsec_rotated_999"}}
        rotated = client.webhooks.rotate_secret("wh_101")
        assert rotated["secret"] == "whsec_rotated_999"

        state["response_body"] = {"data": {**created, "status": "DISABLED"}}
        disabled = client.webhooks.disable("wh_101")
        assert disabled["status"] == "DISABLED"

        state["response_body"] = {"data": {"success": True, "deliveryId": "del_101"}}
        test_res = client.webhooks.test("wh_101")
        assert test_res["success"] is True

        state["response_body"] = {"success": True, "message": "Webhook endpoint deleted."}
        deleted = client.webhooks.delete("wh_101")
        assert deleted["success"] is True

    def test_deliveries_resource(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 200
        state["response_body"] = {
            "data": [{"id": "del_1", "status": "FAILED"}],
            "pagination": {"page": 1, "limit": 20, "total": 1, "totalPages": 1},
        }

        deliveries = client.deliveries.list(status="FAILED")
        assert len(deliveries["data"]) == 1
        assert deliveries["pagination"]["total"] == 1
        assert "status=FAILED" in state["last_request"]["url"]

        state["response_body"] = {"data": {"id": "del_1", "status": "FAILED"}}
        single = client.deliveries.get("del_1")
        assert single["id"] == "del_1"

        state["response_body"] = {"data": {"id": "del_1", "status": "SUCCESS"}}
        retried = client.deliveries.retry("del_1")
        assert retried["status"] == "SUCCESS"

    def test_usage_resource(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 200
        state["response_body"] = {
            "data": {"totalRequests": 1500, "successCount": 1490, "clientErrorCount": 10}
        }

        summary = client.usage.summary(period="2026-09")
        assert summary["totalRequests"] == 1500
        assert "period=2026-09" in state["last_request"]["url"]

        state["response_body"] = {
            "data": {"id": "proj_1", "name": "Production Project", "environment": "LIVE"}
        }
        proj = client.usage.get_project()
        assert proj["name"] == "Production Project"
        assert state["last_request"]["url"].endswith("/project")


class TestTransportFailureHandling:
    """Tests network and timeout exception translations."""

    def test_timeout_exception_handling(self) -> None:
        def hang_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("Connection timed out", request=request)

        client = Nexora(api_key="nx_test_timeout_test")
        client._http._session = httpx.Client(
            transport=httpx.MockTransport(hang_handler),
            base_url=client.base_url,
        )

        with pytest.raises(APITimeoutError) as exc_info:
            client.organizations.list()
        assert exc_info.value.status_code == 408
        assert exc_info.value.code == "REQUEST_TIMEOUT"
        assert "nx_test_timeout_test" not in str(exc_info.value)

    def test_network_connection_error_handling(self) -> None:
        def dead_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused", request=request)

        client = Nexora(api_key="nx_test_dead_test")
        client._http._session = httpx.Client(
            transport=httpx.MockTransport(dead_handler),
            base_url=client.base_url,
        )

        with pytest.raises(APIConnectionError) as exc_info:
            client.organizations.list()
        assert exc_info.value.status_code == 0
        assert exc_info.value.code == "NETWORK_ERROR"
        assert "nx_test_dead_test" not in str(exc_info.value)


class TestAdditionalCoverage:
    """Covers edge cases, aliases, and full parameter branches."""

    def test_exception_alias_module(self) -> None:
        from nexorams.exception import NexoraError as NE
        assert NE is NexoraError

    def test_domains_missing_hostname_raises(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, _ = mock_client
        with pytest.raises(ValueError, match="Either 'hostname' or 'domain'"):
            client.domains.create("org_1")

    def test_resource_retrieve_aliases(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_body"] = {"data": {"id": "res_1"}}

        assert client.organizations.retrieve("res_1")["id"] == "res_1"
        assert client.subscriptions.retrieve("res_1")["id"] == "res_1"
        assert client.webhooks.retrieve("res_1")["id"] == "res_1"
        assert client.deliveries.retrieve("res_1")["id"] == "res_1"

    def test_organizations_create_all_parameters(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 201
        state["response_body"] = {"data": {"id": "org_all"}}

        res = client.organizations.create(
            name="Apex",
            type="HOSPITAL",
            owner={"first_name": "Clara", "last_name": "Oswald", "email": "clara@apex.com", "phone": "123"},
            country="NG",
            state="Lagos",
            city="Ikeja",
            address="12 Main St",
            timezone="Africa/Lagos",
            currency="NGN",
            subdomain="apex",
            custom_domain="portal.apex.ng",
            modules=["hospital_billing"],
            branding={"primaryColor": "#000"},
            subscription={"plan": "starter"},
            custom_param="extra",
        )
        assert res["id"] == "org_all"
        body = state["last_request"]["body"]
        assert body["country"] == "NG"
        assert body["state"] == "Lagos"
        assert body["city"] == "Ikeja"
        assert body["address"] == "12 Main St"
        assert body["timezone"] == "Africa/Lagos"
        assert body["currency"] == "NGN"
        assert body["subdomain"] == "apex"
        assert body["customDomain"] == "portal.apex.ng"
        assert body["modules"] == ["hospital_billing"]
        assert body["branding"] == {"primaryColor": "#000"}
        assert body["subscription"] == {"plan": "starter"}
        assert body["custom_param"] == "extra"

    def test_plans_product_context_parameter(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_body"] = {"data": []}
        client.plans.list(product_context="DEVELOPER")
        assert "productContext=DEVELOPER" in state["last_request"]["url"]

    def test_users_create_with_phone(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 201
        state["response_body"] = {"data": {"id": "u1"}}
        client.users.create("org_1", "Jane", "Doe", "j@d.com", "staff", phone="123456")
        assert state["last_request"]["body"]["phone"] == "123456"

    def test_webhooks_create_with_name_desc(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 201
        state["response_body"] = {"data": {"id": "wh1"}}
        client.webhooks.create(
            url="https://a.com",
            description="receiver",
            name="primary",
        )
        assert state["last_request"]["body"]["description"] == "receiver"
        assert state["last_request"]["body"]["name"] == "primary"

    def test_http_client_repr_and_put_and_clean_params(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        repr_str = repr(client._http)
        assert "HttpClient" in repr_str
        assert "nx_test_" not in repr_str

        # PUT method
        state["response_body"] = {"data": {"put": True}}
        res = client._http.put("/custom", json_data={"k": "v"}, params={"flag": True, "omit": None})
        assert res["put"] is True
        assert "flag=true" in state["last_request"]["url"]
        assert "omit" not in state["last_request"]["url"]

    def test_non_json_error_fallback(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_status"] = 502
        state["response_headers"] = {"content-type": "text/html"}
        state["response_body"] = "Bad Gateway"

        with pytest.raises(NexoraError) as exc_info:
            client.organizations.list()
        assert exc_info.value.status_code == 502
        assert "Bad Gateway" in exc_info.value.message

    def test_verify_signature_camel_case_alias(self) -> None:
        now = int(time.time())
        payload = '{"test": 1}'
        secret = "whsec_abc123"
        to_sign = f"{now}.{payload}".encode("utf-8")
        sig = hmac.new(secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
        header = f"t={now},v1={sig}"

        assert Nexora.verifyWebhookSignature(payload, header, secret) is True

    def test_mask_api_key_short(self) -> None:
        from nexorams.client import _mask_api_key
        assert _mask_api_key("short") == "••••••••"

    def test_organizations_list_all_query_params(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_body"] = {"data": [], "pagination": {"page": 2, "limit": 10, "total": 0, "totalPages": 0}}
        client.organizations.list(page=2, limit=10, type="HOSPITAL", status="ACTIVE", search="general", environment="TEST")
        url = state["last_request"]["url"]
        assert "page=2" in url
        assert "limit=10" in url
        assert "type=HOSPITAL" in url
        assert "status=ACTIVE" in url
        assert "search=general" in url
        assert "environment=TEST" in url

    def test_deliveries_list_all_query_params(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_body"] = {"data": [], "pagination": {"page": 1, "limit": 5, "total": 0, "totalPages": 0}}
        client.deliveries.list(endpoint_id="wh_1", status="SUCCESS", page=1, limit=5)
        url = state["last_request"]["url"]
        assert "endpointId=wh_1" in url
        assert "status=SUCCESS" in url
        assert "page=1" in url
        assert "limit=5" in url

    def test_users_list_all_query_params(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_body"] = {"data": []}
        client.users.list("org_1", role="doctor", page=1, limit=15)
        url = state["last_request"]["url"]
        assert "role=doctor" in url
        assert "page=1" in url
        assert "limit=15" in url

    def test_webhooks_update_all_params(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_body"] = {"data": {"id": "wh_1"}}
        client.webhooks.update("wh_1", events=["user.created"], description="new desc", status="DISABLED")
        body = state["last_request"]["body"]
        assert body["events"] == ["user.created"]
        assert body["description"] == "new desc"
        assert body["status"] == "DISABLED"

    def test_http_request_relative_path(self, mock_client: tuple[Nexora, dict[str, Any]]) -> None:
        client, state = mock_client
        state["response_body"] = {"data": {"ok": True}}
        res = client._http.get("custom/relative/path")
        assert res["ok"] is True
        assert state["last_request"]["url"].endswith("/developer/v1/custom/relative/path")


