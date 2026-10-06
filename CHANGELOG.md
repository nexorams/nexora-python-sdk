# Changelog

All notable changes to the `nexorams` Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-10-06

This is a major release because several changes can break existing integrations. See **Migrating from 1.x** below.

### Breaking
- **Mismatched `environment` now raises.** Passing an `environment` that disagrees with the API key prefix (for example `environment="live"` with an `nx_test_` key) raises `ValidationError` with code `ENVIRONMENT_MISMATCH`. Unknown values raise `INVALID_ENVIRONMENT`. Previously the argument silently overrode the inferred environment. `"test"` is accepted as an alias for `"sandbox"`, and the value is case-insensitive.
- **`webhooks.verify_signature` / `Nexora.verify_webhook_signature` require timestamped signatures by default.** With the default `tolerance_seconds` (300), only the `t=<unix>,v1=<hex>` format is accepted. Bare HMAC signatures (`v1=<hex>` or raw hex) are rejected unless `tolerance_seconds` is explicitly `0`. Signatures must be 64 hex characters, timestamps must be positive, and a negative tolerance always fails verification.
- **`users.list` returns a paginated dictionary** (`{"data": [...], "pagination": {...}}`) instead of a list.
- **`school.classes.list` is paginated.** It now takes `page` (default 1) and `limit` (default 20), and any extra keyword arguments are sent as query parameters.
- **`usage.get_project` no longer returns `tier` or `limits`.** It returns project metadata: `id`, `name`, `slug`, `description`, `status`, `environment`, `organizationSector` and timestamps.

### Added
- `modules.project_modules()` and `modules.credits()` for the project's module entitlements and credit summary.

### Migrating from 1.x
1. **Environment.** Remove the `environment` argument, or make it match the key: `nx_test_` keys are `"sandbox"` (or `"test"`) and `nx_live_` keys are `"live"`.
2. **Webhook verification.** Pass the full `X-Nexora-Signature` header (`t=...,v1=...`). If you still receive legacy signatures without a timestamp, verify them with `tolerance_seconds=0`, which disables replay protection, and plan to drop that path.
3. **`users.list`.** Read users from `result["data"]`.
4. **`usage.get_project`.** Stop reading `tier` and `limits`; use `modules.credits()` for credit capacity.

## [1.0.2] - 2026-09-18

### Added
- `school`, `hospital`, `hotel`, `pharmacy` and `company` resources and their types are exported from `nexorams` and `nexorams.resources`.

## [1.0.1] - 2026-09-10

### Added
- Sector resources on the client: `school` (students, attendance, classes), `hospital` (patients, appointments, vitals), `hotel` (rooms, reservations, guests), `pharmacy` and `company` (employees, attendance, payroll).

## [1.0.0] - 2026-09-09

### Added
- **Official Python Client**: `Nexora` (and alias `NexoraClient`) for the Nexora Developer Platform (`/developer/v1`).
- **Resource Managers**:
  - `organizations`: Full lifecycle management (`create`, `list`, `get`/`retrieve`, `update`, `update_modules`, `get_subscription`, `get_domains`, `add_domain`, `verify_domain`).
  - `users`: Organization user provisioning and directory listing (`create`, `list`).
  - `modules`: Platform and organization module toggling (`list`, `update`).
  - `plans`: Subscription tier listing and quota inspection (`list`).
  - `subscriptions`: Real-time subscription state inspection (`get`/`retrieve`).
  - `domains`: Custom domains registry and verification (`list`, `create`, `verify`).
  - `webhooks`: Webhook endpoint management (`create`, `list`, `get`/`retrieve`, `update`, `rotate_secret`, `disable`, `test`, `delete`) and signature verification (`verify_signature`).
  - `deliveries`: Webhook delivery telemetry inspection and retries (`list`, `get`/`retrieve`, `retry`).
  - `usage`: Developer usage analytics and quota consumption summaries (`summary`, `get_project`).
- **Security & Hardening**:
  - Masked API key representation (`__repr__`) preventing credential leakage in logs, consoles, and tracebacks.
  - Constant-time HMAC-SHA256 signature verification (`hmac.compare_digest`) with timestamp replay defense and 300s clock-skew tolerance.
  - Safe Bearer token header handling without query param leakage.
- **Resilience & Networking**:
  - Connection pooling and connection reuse using `httpx.Client`.
  - Automatic `X-Request-Id` generation for distributed tracing.
  - First-class `Idempotency-Key` header support on mutating requests (`create`, `retry`, etc.).
  - Configurable timeouts and base URL overrides.
  - Python context manager support (`with Nexora(...) as client:`).
- **Hierarchical Error Handling**:
  - Base `NexoraError` exposing `status_code`, `code`, `request_id`, and `details`.
  - Granular subclasses: `AuthenticationError` (401), `PermissionDeniedError` (403), `NotFoundError` (404), `ConflictError` (409), `ValidationError` (422), `RateLimitError` (429), `APITimeoutError`, `APIConnectionError`.
- **Typing & Packaging**:
  - PEP 561 compliance with bundled `py.typed`.
  - Pure Python wheel and sdist built via `hatchling`.
  - Python 3.9 through 3.13 support.
