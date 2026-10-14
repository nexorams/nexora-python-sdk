"""Nexora Cloud generic, schema-driven resources.

Nothing here is generated or hard-coded per application: entity keys are data, resolved by the
server against the application's schema, the organization's grants and your API key's scopes.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional

from ..exceptions import ValidationError

if TYPE_CHECKING:
    from .._http import HttpClient

_ENTITY_KEY = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
_APPLICATION_ID = re.compile(r"^[a-fA-F0-9]{24}$")


class CloudEntityClient:
    """Client for ONE entity of ONE Nexora Cloud application."""

    def __init__(self, http: HttpClient, application_id: str, entity_key: str) -> None:
        if not isinstance(application_id, str) or not _APPLICATION_ID.match(application_id):
            raise ValidationError(message="application_id must be a Nexora Cloud application id.", code="INVALID_APPLICATION_ID", status_code=400)
        if not isinstance(entity_key, str) or not _ENTITY_KEY.match(entity_key):
            raise ValidationError(
                message=f"Invalid entity key {entity_key!r}. Entity keys are lowercase letters, digits and underscores.",
                code="INVALID_ENTITY_KEY",
                status_code=400,
            )
        self._http = http
        self.application_id = application_id
        self.entity_key = entity_key

    @property
    def _base(self) -> str:
        return f"/cloud/apps/{self.application_id}/entities/{self.entity_key}/records"

    def list(self, page: int = 1, limit: int = 20, status: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        """Returns ``{"data": [...], "pagination": {...}}``."""
        return self._http.get(self._base, params={"page": page, "limit": limit, "status": status}, **kwargs)

    def list_all(self, limit: int = 100, status: Optional[str] = None, **kwargs: Any) -> Iterator[Dict[str, Any]]:
        """Iterates every record, fetching pages lazily."""
        page = 1
        while True:
            result = self.list(page=page, limit=limit, status=status, **kwargs)
            for record in result["data"]:
                yield record
            total_pages = (result.get("pagination") or {}).get("totalPages", 1)
            if page >= total_pages or not result["data"]:
                return
            page += 1

    def get(self, record_id: str, **kwargs: Any) -> Dict[str, Any]:
        return self._http.get(f"{self._base}/{record_id}", **kwargs)

    def create(self, data: Optional[Dict[str, Any]] = None, relations: Optional[Dict[str, Any]] = None, idempotency_key: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        """Creates a record. Pass ``idempotency_key`` to make retries safe."""
        return self._http.post(self._base, json_data=_body(data, relations), idempotency_key=idempotency_key, **kwargs)

    def update(self, record_id: str, data: Optional[Dict[str, Any]] = None, relations: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        return self._http.patch(f"{self._base}/{record_id}", json_data=_body(data, relations), **kwargs)

    def archive(self, record_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Archives (soft-deletes) a record; data is never hard-deleted through the API."""
        return self._http.delete(f"{self._base}/{record_id}", **kwargs)

    def events(self) -> Dict[str, str]:
        """Webhook event names for this entity, e.g. ``cloud.members.created``."""
        return {action: f"cloud.{self.entity_key}.{action}" for action in ("created", "updated", "archived")}


def _body(data: Optional[Dict[str, Any]], relations: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    if data is not None:
        body["data"] = data
    if relations is not None:
        body["relations"] = relations
    return body


class _Entities:
    """``app.entities.members`` resolves the entity dynamically."""

    def __init__(self, factory: Any) -> None:
        self._factory = factory

    def __getattr__(self, name: str) -> CloudEntityClient:
        if name.startswith("_"):
            raise AttributeError(name)
        return self._factory(name)

    def __getitem__(self, name: str) -> CloudEntityClient:
        return self._factory(name)


class CloudApplicationClient:
    def __init__(self, http: HttpClient, application_id: str) -> None:
        self._http = http
        self.application_id = application_id
        self.entities = _Entities(self.entity)

    def schema(self, **kwargs: Any) -> Dict[str, Any]:
        return self._http.get(f"/cloud/apps/{self.application_id}/schema", **kwargs)

    def entity(self, entity_key: str) -> CloudEntityClient:
        return CloudEntityClient(self._http, self.application_id, entity_key)


class CloudResource:
    def __init__(self, http: HttpClient, default_application_id: Optional[str] = None) -> None:
        self._http = http
        self._default_application_id = default_application_id
        self.entities = _Entities(self.entity)

    def installations(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """Organizations that granted this project access to an installed Cloud application."""
        return self._http.get("/cloud/installations", **kwargs)

    def app(self, application_id: str) -> CloudApplicationClient:
        return CloudApplicationClient(self._http, application_id)

    def _default(self) -> str:
        if not self._default_application_id:
            raise ValidationError(
                message="Set application_id on the Nexora client or use nexora.cloud.app(application_id).",
                code="APPLICATION_ID_REQUIRED",
                status_code=400,
            )
        return self._default_application_id

    def entity(self, entity_key: str, application_id: Optional[str] = None) -> CloudEntityClient:
        return CloudEntityClient(self._http, application_id or self._default(), entity_key)

    def schema(self, **kwargs: Any) -> Dict[str, Any]:
        return self.app(self._default()).schema(**kwargs)
