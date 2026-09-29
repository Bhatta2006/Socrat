# M1 local validation report

**Date:** 2026-09-29  
**Overall local result:** PASS  
**M1 milestone result:** NOT YET PASSED — external staging and operational gates remain

## Verified

| Check | Result |
|---|---|
| API acceptance suite | 12 passed; 86% statement coverage |
| Python lint | Ruff passed |
| Python static types | mypy passed |
| Web static types | TypeScript passed |
| Production web build | Next.js build passed |
| Browser journeys | 4 passed: desktop/mobile profile persist/reload/logout and invalid-timezone handling |
| Dependency advisories | npm audit and pip-audit reported no known vulnerabilities |
| OCI infrastructure | Terraform 1.16.4 formatting/schema validation and 3 mocked safety tests passed with OCI provider 9.7.1; no account plan or apply performed |
| M0 regression suite | Must remain green; rerun in the final verification bundle |

## Acceptance behavior exercised

- no-session denial with stable error envelope and request ID;
- session tokens stored only as hashes, expiry enforced, logout revokes replayed cookies;
- exact-origin and CSRF enforcement on writes;
- cross-learner profile requests concealed with `404`;
- profile update, audit entry, and outbox event committed atomically;
- rolled-back events are never delivered and delivered events are idempotent;
- migration downgrade/upgrade and isolated SQLite backup restoration;
- ready/live endpoints, disabled future feature flags, and baseline response hardening;
- real Chromium desktop/mobile persistence, responsive width, validation, and sign-out.

## Environment limitations

Docker is not installed on this workstation. Terraform was downloaded locally with its published SHA-256 checksum and used only to format and validate the OCI stack. The Compose PostgreSQL topology, container builds, managed OIDC, hosted CI, Terraform plan/apply, and staging operations are not claimed as executed. See [the M1 gate](../milestones/m1-gate.md).

The passing API run emits upstream deprecation warnings from FastAPI's current test client and Authlib's HTTPX compatibility layer. They do not affect the tested behavior, but dependency updates must keep this warning set from becoming an ignored baseline.
