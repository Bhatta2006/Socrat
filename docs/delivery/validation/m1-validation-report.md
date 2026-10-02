# M1 local validation report

## Closeout revalidation — 2026-10-02

The API now has a dedicated outbound bridge for managed OIDC while internal services retain their isolated network and the API publishes no host port. The targeted staging/release suite passed **13 tests**. This establishes configuration and release-controller behavior only; no live Docker, OCI, or identity-provider drill is claimed.

The workstation currently has a Docker client but no running Docker daemon, and GitHub CLI is not authenticated. The full locked Python environment has not been reproduced in this session. External account/domain/identity/notification inputs remain needed; see the [staging evidence record](m1-staging-evidence.md).

The evidence below is the historical 29 September validation and hosted artifact record.

**Date:** 2026-09-29  
**Overall local result:** PASS  
**M1 milestone result:** NOT YET PASSED — external staging and operational gates remain

## Verified

| Check | Result |
|---|---|
| API and operations suite | 28 passed; 86.28% statement coverage locally and above the 85% hosted threshold |
| Python lint | Ruff passed |
| Python static types | mypy passed |
| Web static types | TypeScript passed |
| Production web build | Next.js build passed |
| Browser journeys | 4 passed: desktop/mobile profile persist/reload/logout and invalid-timezone handling |
| Dependency advisories | npm audit and pip-audit reported no known vulnerabilities |
| OCI infrastructure | Terraform 1.16.4 formatting/schema validation and 3 mocked safety tests passed with OCI provider 9.7.1; no account plan or apply performed |
| PostgreSQL recovery | Hosted PostgreSQL 17 migration, custom-format dump, and isolated restore at schema revision `0001` passed |
| Runtime configuration | Production API/web image builds, staging Compose render, Prometheus config/rules, and Caddy config passed on hosted Linux |
| M0 regression suite | 13 model tests and 127 document/contract checks passed |

Hosted evidence:

- [pull-request run 36575689963](https://github.com/Bhatta2006/Socrat/actions/runs/36575689963), commit `5f98cd2`;
- [protected-main run 36601938034](https://github.com/Bhatta2006/Socrat/actions/runs/36601938034), commit `b69ec31`;
- API manifest `sha256:555568e1369087f539db85832952fa0110316e7b2ab13570e52e9c4e68965158`, [attestation 51197638](https://github.com/Bhatta2006/Socrat/attestations/51197638);
- web manifest `sha256:c4621beecdb76ccf66ee129316f6167992304bf0849a74bea628fa89506aad01`, [attestation 51198743](https://github.com/Bhatta2006/Socrat/attestations/51198743).

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

Docker is not installed on this workstation, so container and PostgreSQL evidence comes from the hosted Ubuntu runner rather than a local daemon. Terraform was downloaded locally with its published SHA-256 checksum and used only to format, validate, and run mocked tests. No OCI account plan/apply, managed OIDC integration, off-host backup, alert delivery, staging deploy, or staging rollback is claimed. Multi-architecture image publication correctly skipped the pull request and passed only after protected `main` verification. See [the M1 gate](../milestones/m1-gate.md).

The passing API run emits upstream deprecation warnings from FastAPI's current test client and Authlib's HTTPX compatibility layer. They do not affect the tested behavior, but dependency updates must keep this warning set from becoming an ignored baseline.
