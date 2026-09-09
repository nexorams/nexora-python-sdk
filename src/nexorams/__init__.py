"""Nexora Developer Platform Official Python SDK.

Build, provision, and automate multi-tenant management systems across sectors
(Schools, Hospitals, Hotels, Pharmacies, Enterprises) with the Nexora Developer API.
"""

__version__ = "1.0.0"

from .client import Nexora, NexoraClient
from .exceptions import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    ConflictError,
    NexoraError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ValidationError,
)
from .resources.deliveries import WebhookDeliveriesResource
from .resources.domains import DomainsResource
from .resources.modules import ModulesResource
from .resources.organizations import OrganizationsResource
from .resources.plans import PlansResource
from .resources.subscriptions import SubscriptionsResource
from .resources.usage import UsageResource
from .resources.users import UsersResource
from .resources.webhooks import WebhooksResource

__all__ = [
    "__version__",
    "Nexora",
    "NexoraClient",
    "NexoraError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "RateLimitError",
    "APITimeoutError",
    "APIConnectionError",
    "OrganizationsResource",
    "UsersResource",
    "ModulesResource",
    "PlansResource",
    "SubscriptionsResource",
    "DomainsResource",
    "WebhooksResource",
    "WebhookDeliveriesResource",
    "UsageResource",
]
