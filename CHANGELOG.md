# Changelog

All notable changes to the `nexorams` Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
