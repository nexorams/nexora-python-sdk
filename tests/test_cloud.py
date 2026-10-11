"""Tests for the Nexora Cloud generic, schema-driven resources."""

from __future__ import annotations

import json

import httpx
import pytest

from nexorams import CloudEntityClient, Nexora, NexoraError, PermissionDeniedError, ValidationError

APP = "a" * 24
KEY = "nx_live_" + "b" * 32


def make_client(handler, **kwargs):
    client = Nexora(api_key=KEY, base_url="https://api.test/developer/v1", **kwargs)
    client._http._session = httpx.Client(
        base_url="https://api.test/developer/v1",
        transport=httpx.MockTransport(handler),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "Accept": "application/json", "User-Agent": "test"},
    )
    return client


def test_entities_are_resolved_dynamically():
    client = make_client(lambda r: httpx.Response(200, json={"data": []}), application_id=APP)
    members = client.cloud.entities.members
    assert isinstance(members, CloudEntityClient)
    assert members.entity_key == "members"
    assert client.resources("members").application_id == APP
    assert client.cloud.app(APP).entities["trainers"].entity_key == "trainers"
    assert client.resources("members").events() == {
        "created": "cloud.members.created",
        "updated": "cloud.members.updated",
        "archived": "cloud.members.archived",
    }


def test_crud_uses_generic_endpoints_headers_and_idempotency():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        seen.append((request.method, request.url.path, dict(request.url.params), request.headers, body))
        if request.method == "GET" and request.url.path.endswith("/records"):
            page = int(request.url.params.get("page", 1))
            return httpx.Response(200, json={"data": [{"id": f"r{page}"}], "pagination": {"page": page, "totalPages": 2, "total": 2}})
        if request.method == "POST":
            return httpx.Response(201, json={"data": {"id": "new", "data": body["data"]}})
        if request.method == "PATCH":
            return httpx.Response(200, json={"data": {"id": "r1", "data": body["data"]}})
        if request.method == "DELETE":
            return httpx.Response(200, json={"data": {"id": "r1", "status": "ARCHIVED"}})
        return httpx.Response(200, json={"data": {"id": "r1"}})

    client = make_client(handler, organization_id="org_1", application_id=APP)
    members = client.resources("members")

    page = members.list(page=1, limit=1)
    assert page["pagination"]["totalPages"] == 2
    assert seen[-1][2] == {"page": "1", "limit": "1"}
    assert seen[-1][3]["x-organization-id"] == "org_1"
    assert seen[-1][3]["authorization"] == f"Bearer {KEY}"

    assert [r["id"] for r in members.list_all(limit=1)] == ["r1", "r2"]

    created = members.create({"first_name": "Ada"}, idempotency_key="create-ada-1")
    assert created["id"] == "new"
    assert seen[-1][3]["idempotency-key"] == "create-ada-1"
    assert seen[-1][4] == {"data": {"first_name": "Ada"}}
    assert seen[-1][1] == f"/developer/v1/cloud/apps/{APP}/entities/members/records"

    assert members.update("r1", {"plan": "gold"})["data"]["plan"] == "gold"
    assert seen[-1][0] == "PATCH"
    assert members.archive("r1")["status"] == "ARCHIVED"
    assert seen[-1][0] == "DELETE"
    assert members.get("r1")["id"] == "r1"


def test_discovery_and_per_call_organization_override():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.path, request.headers.get("x-organization-id")))
        if request.url.path.endswith("/installations"):
            return httpx.Response(200, json={"data": [{"organizationId": "o1", "applicationId": APP, "sandbox": False}]})
        return httpx.Response(200, json={"data": {"applicationId": APP, "entities": [{"key": "members"}]}})

    client = make_client(handler, organization_id="org_1", application_id=APP)
    assert client.cloud.installations()[0]["organizationId"] == "o1"
    assert client.cloud.schema()["entities"][0]["key"] == "members"
    client.resources("members").list(headers={"X-Organization-Id": "org_2"})
    assert seen[-1][1] == "org_2"


def test_errors_are_mapped():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"code": "PERMISSION_DENIED", "message": "Missing Cloud permission", "requestId": "req_1"}})

    client = make_client(handler, application_id=APP)
    with pytest.raises(PermissionDeniedError) as err:
        client.resources("forbidden").list()
    assert err.value.code == "PERMISSION_DENIED"


def test_input_is_validated_before_any_request():
    calls = []
    client = make_client(lambda r: calls.append(r) or httpx.Response(200, json={"data": []}), application_id=APP)
    with pytest.raises(ValidationError):
        client.resources("Not-Valid")
    with pytest.raises(ValidationError):
        client.resources("members", "short")
    bare = make_client(lambda r: httpx.Response(200, json={"data": []}))
    with pytest.raises(ValidationError) as err:
        bare.resources("members")
    assert err.value.code == "APPLICATION_ID_REQUIRED"
    assert calls == []
    assert issubclass(ValidationError, NexoraError)
