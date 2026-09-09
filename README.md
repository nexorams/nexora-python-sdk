# Nexora Python SDK

Official Python client library for the [Nexora Developer Platform](https://nexoragms.com/developer).

Programmatically build, provision, and automate multi-tenant management systems across sectors (Schools, Hospitals, Hotels, Pharmacies, and Enterprises), manage tenant users, inspect modular feature catalogs, connect custom vanity domains, and subscribe to cryptographically signed webhooks.

---

## Installation

Install the official package from PyPI:

```bash
pip install nexorams
```

---

## Security: Server-Side Only

> [!CAUTION]
> **CRITICAL SECURITY WARNING**  
> The Nexora SDK requires secret Developer API credentials (`nx_live_...` or `nx_test_...`) and must **only** be executed in trusted, server-side environments.
>
> Never expose your Nexora secret API key in:
> - Client-side browser code, mobile apps, or frontend bundles
> - Public GitHub/Git repositories or committed configuration files
>
> Always load credentials from secure server-side environment variables:
> ```python
> import os
> from nexorams import Nexora
>
> nexora = Nexora(api_key=os.environ["NEXORA_API_KEY"])
> ```

---

## Requirements

- **Python**: `>= 3.9`
- **Dependencies**: `httpx >= 0.24.0`
- **Developer Account**: Register at [https://nexoragms.com/developers/signup](https://nexoragms.com/developers/signup)
- **API Key**: `nx_test_...` (Sandbox) or `nx_live_...` (Live Production)

---

## Quick Start

```python
import os
from nexorams import Nexora

# Initialize the client (environment is inferred automatically from key prefix)
nexora = Nexora(
    api_key=os.environ["NEXORA_API_KEY"]
)

# Provision a new sandbox tenant organization
organization = nexora.organizations.create(
    name="Bright Future Academy",
    type="SCHOOL",  # SCHOOL | HOSPITAL | HOTEL | PHARMACY | ENTERPRISE
    country="NG",
    owner={
        "firstName": "John",
        "lastName": "Doe",
        "email": "john.doe@brightfuture.edu.ng",
    },
    idempotency_key="bright-future-001",  # Guarantees atomic, duplicate-safe provisioning
)

print(f"Organization ID: {organization['id']}")
print(f"Portal URL: {organization['portalUrl']}")
print(f"Trial Status: {organization['subscription']['status']}")
```

You can also use Nexora as a context manager for automatic connection cleanup:

```python
with Nexora(api_key=os.environ["NEXORA_API_KEY"]) as nexora:
    modules = nexora.modules.list(organization_type="school")
    print(modules)
```

---

## Authentication & Environments

The SDK authenticates using Bearer tokens against the canonical `/developer/v1` API. The environment is inferred directly from your API key prefix:

- `nx_test_...` → **Sandbox (`sandbox` / `TEST`)**
- `nx_live_...` → **Production (`live` / `LIVE`)**

```python
nexora = Nexora(
    api_key=os.environ["NEXORA_API_KEY"],
    # Optional parameters:
    # base_url="http://localhost:5000/developer/v1",  # Local testing override
    # timeout=30.0,                                   # Request timeout in seconds (default: 30.0)
)
```

### Sandbox vs Live

- **Sandbox (`nx_test_...`)**: Test organization provisioning, simulate webhooks on localhost/HTTP endpoints, and verify end-to-end workflows without consuming live quotas or incurring billing charges.
- **Production (`nx_live_...`)**: Provisions live production organizations with authoritative DNS routing, enforces strict SSRF protections and HTTPS on webhook destinations, and provisions production subscriptions.

---

## Resources & API Reference

### 1. Organizations

Provision, list, inspect, and update tenant organizations.

```python
# 1. Provision a Hospital
hospital = nexora.organizations.create(
    name="Apex Specialist Hospital",
    type="HOSPITAL",
    country="US",
    owner={
        "firstName": "Sarah",
        "lastName": "Connor",
        "email": "admin@apex.org",
        "phone": "+14155550192",
    },
    branding={
        "primaryColor": "#0284c7",
        "secondaryColor": "#0f172a",
    },
    idempotency_key="apex-hospital-order-99",
)

# 2. List organizations with pagination
page = nexora.organizations.list(type="HOSPITAL", page=1, limit=20)
print(page["data"])         # List of organizations
print(page["pagination"])   # {'page': 1, 'limit': 20, 'total': 1, 'totalPages': 1}

# 3. Retrieve organization by ID
org = nexora.organizations.get(hospital["id"])

# 4. Update organization branding and settings
updated = nexora.organizations.update(
    hospital["id"],
    name="APEX MEDICAL CENTER",
    primary_color="#0369a1",
)
```

### 2. Users

Provision safe tenant user memberships (practitioners, teachers, staff, clients) within an organization. Platform administration roles are strictly prohibited.

```python
# Provision a practitioner or teacher
user = nexora.users.create(
    organization_id=hospital["id"],
    first_name="Eleanor",
    last_name="Vance",
    email="e.vance@apex.org",
    role="doctor",
)

# List users in an organization
users = nexora.users.list(organization_id=hospital["id"], role="doctor")
```

### 3. Modules

Inspect available system modules by sector and manage organization feature toggles.

```python
# List available modules for schools
modules = nexora.modules.list(organization_type="school")

# Update enabled modules on an organization
nexora.modules.update(
    organization_id=org["id"],
    modules=["school_attendance", "school_grading", "school_fees"],
)
```

### 4. Plans

Query published subscription plans, tiers, and quotas.

```python
plans = nexora.plans.list(organization_type="school")
```

### 5. Subscriptions

Retrieve active subscription tiers and 30-day trial metadata. The backend `TrialPolicyService` is authoritative.

```python
subscription = nexora.subscriptions.get(org["id"])
print("Plan:", subscription["planName"])
print("Trial Ends At:", subscription["trialEndsAt"])
```

### 6. Domains

Connect and verify custom white-label hostnames.

```python
# 1. Connect custom domain (returns required DNS records)
domain = nexora.domains.create(
    organization_id=org["id"],
    hostname="portal.apex.org",
)
print("DNS records to configure:", domain.get("dnsRecords"))

# 2. Trigger authoritative DNS verification
result = nexora.domains.verify(
    organization_id=org["id"],
    domain_id=domain["id"],
)
print("Verified:", result["verified"])
```

### 7. Webhooks & Signature Verification

Register HTTPS webhook receivers, rotate secrets, and cryptographically verify incoming signatures.

```python
# Register an endpoint
webhook = nexora.webhooks.create(
    url="https://api.example.com/webhooks/nexora",
    events=["organization.provisioned", "user.created", "subscription.updated"],
    description="Primary production webhook receiver",
)

# STORE SAFELY (returned ONLY ONCE upon creation):
print("Webhook Signing Secret:", webhook["secret"])
```

#### Cryptographic Signature Verification (FastAPI / Flask / Django)

Every webhook sent by Nexora includes a cryptographic `X-Nexora-Signature` header (`t=<timestamp>,v1=<hmac_sha256>`). Use the constant-time verification helper to protect against timing and replay attacks:

```python
from fastapi import FastAPI, Header, HTTPException, Request
from nexorams import Nexora
import os

app = FastAPI()

@app.post("/webhooks/nexora")
async def handle_nexora_webhook(
    request: Request,
    x_nexora_signature: str = Header(...),
):
    raw_payload = await request.body()
    webhook_secret = os.environ["NEXORA_WEBHOOK_SECRET"]

    is_valid = Nexora.verify_webhook_signature(
        payload=raw_payload,            # Raw bytes or string
        header=x_nexora_signature,      # Header string from request
        secret=webhook_secret,          # Webhook signing secret (whsec_...)
        tolerance_seconds=300,          # 5-minute replay tolerance window
    )

    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event = await request.json()
    print(f"Received verified event: {event['type']}")
    return {"received": True}
```

### 8. Webhook Deliveries

Inspect delivery logs and manually trigger redeliveries.

```python
# List failed delivery attempts
failed = nexora.deliveries.list(status="FAILED")

# Retry a failed delivery
retried = nexora.deliveries.retry(failed["data"][0]["id"])
```

### 9. Usage & Quotas

Monitor API telemetry, rate limit hits, and developer project quotas.

```python
# Monthly usage breakdown
usage = nexora.usage.summary(period="2026-09")
print(f"Total API Requests: {usage['totalRequests']}")

# Project profile & limits
project = nexora.usage.get_project()
print(f"Tier: {project['tier']}, Limits: {project['limits']}")
```

---

## Error Handling

All API transport and validation errors raise structured `NexoraError` exceptions with HTTP status codes, machine-readable error codes, and unique correlation request IDs for support troubleshooting.

```python
import os
from nexorams import (
    Nexora,
    NexoraError,
    AuthenticationError,
    PermissionDeniedError,
    NotFoundError,
    ConflictError,
    RateLimitError,
    ValidationError,
)

nexora = Nexora(api_key=os.environ["NEXORA_API_KEY"])

try:
    nexora.organizations.create(name="Academy", type="SCHOOL", owner={})
except ValidationError as exc:
    print(f"Validation Error ({exc.code}): {exc.message}")
    print(f"Request ID: {exc.request_id}")
except RateLimitError as exc:
    print(f"Rate limited. Retry after {exc.retry_after} seconds.")
except NexoraError as exc:
    print(f"API Error ({exc.status_code} - {exc.code}): {exc.message}")
```

### Error Code Hierarchy

| Exception Class | HTTP Status | Example Error Code |
|---|---|---|
| `AuthenticationError` | 401 | `INVALID_API_KEY`, `API_KEY_REVOKED`, `API_KEY_EXPIRED` |
| `PermissionDeniedError` | 403 | `INSUFFICIENT_SCOPE`, `FORBIDDEN_ROLE`, `LIMIT_REACHED` |
| `NotFoundError` | 404 | `ORGANIZATION_NOT_FOUND`, `WEBHOOK_NOT_FOUND` |
| `ConflictError` | 409 | `IDEMPOTENCY_CONFLICT`, `CONCURRENT_REQUEST`, `USER_EXISTS` |
| `ValidationError` | 400, 422 | `INVALID_OWNER_EMAIL`, `INVALID_EVENT_TYPE`, `INCOMPATIBLE_MODULE` |
| `RateLimitError` | 429 | `RATE_LIMIT_EXCEEDED`, `API_QUOTA_EXCEEDED` |
| `APITimeoutError` | 408 | `REQUEST_TIMEOUT` |
| `APIConnectionError` | 0 | `NETWORK_ERROR` |

---

## Idempotency

All provisioning and mutating operations accept an optional `idempotency_key` parameter. Replaying an identical request with the same key returns the previously created resource without side effects or duplicates.

```python
org = nexora.organizations.create(
    name="St. Mary's Academy",
    type="SCHOOL",
    owner={"firstName": "Mary", "lastName": "Williams", "email": "mary@stmarys.edu"},
    idempotency_key="order_tx_928103",
)
```

---

## Documentation & Support

- **Developer Documentation**: [https://nexoragms.com/developers/docs](https://nexoragms.com/developers/docs)
- **Interactive OpenAPI Reference**: [https://api.nexoragms.com/developer/v1/docs](https://api.nexoragms.com/developer/v1/docs)
- **Support**: `developer@nexoragms.com`
- **GitHub Repository**: [https://github.com/nexorams/nexora-python-sdk](https://github.com/nexorams/nexora-python-sdk)

---

## License

MIT © [Nexora Technologies](https://nexoragms.com)
# nexora-python-sdk
