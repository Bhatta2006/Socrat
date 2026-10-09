# M2 repository validation report

**Date:** 2026-10-02

**Repository result:** PASS

**Milestone decision:** NOT YET PASSED; hosted PostgreSQL evidence, staging drills, and human approvals remain.

## Verified locally

| Check | Result |
|---|---|
| Locked Python environment | `uv sync --frozen --python 3.12` completed; Python 3.12.10 and locked dependencies |
| Full API/operations acceptance suite | 57 passed, 2 skipped; 90.10% statement coverage, above the 85% threshold |
| M2 acceptance cases | 29 passed, including both domains, editorial authorization, lifecycle, rollback, immutability, CLI, schema parity, source whitespace, and additive migration |
| Static types | mypy passed on 13 source files |
| Python format/lint | Ruff format/check passed |
| Developer and staging Compose | Both rendered successfully; staging used synthetic secret/image/client fixtures, not real credentials or images |
| Document/contracts | 140 passed, 0 failed after adding this report |
| Whitespace | `git diff --check` passed |

The generated JSON Schema matches the typed source model. DSA and writing fixtures import through the same kernel. The DSA revision fixture pins an old-to-new concept mapping; no learner-state migration is performed.

## Behavior exercised

- Cycles, duplicate IDs, invalid references/overlays, omitted prerequisites, unsupported modalities/plugins, undeclared language variants, non-finite thresholds, passive mastery changes, and self-migration are rejected.
- Absent language variants are explicitly unavailable; code and deterministic test I/O retain meaningful whitespace, including empty input.
- Admin access defaults off and requires an exact issuer/subject pair. Normal learners, a matching subject under a different issuer, missing CSRF, and wrong Origin are denied.
- Identical imports are idempotent; conflicting content at the same key/version is rejected. Import/audit/outbox mutation rollback leaves no content event behind.
- Authors cannot approve their own versions. Publication cannot skip review stages; language verification must attest every declared language.
- Database triggers protect immutable source payloads and append-only reviews. A revision `0001 → 0002` upgrade preserves existing M1 user data; development downgrade/upgrade is exercised.
- Synthetic publication does not expose fixture packs. Launch manifests omit assessment items, test cases, reference solutions, starter code, rubrics, and private review data.
- Explicit activation and quarantine restore a valid earlier release or leave no active version. Withdrawn versions cannot reactivate; pinned source/digests remain readable by editors.

## Not verified or claimed

Two real PostgreSQL cases are configured in the hosted CI workflow but skipped locally without `SOCRAT_TEST_POSTGRES_URL`: concurrent release-pointer serialization/immutability and parallel outbox delivery. No new hosted CI result is claimed.

The local Docker client can render Compose, but no daemon-backed database or container run was performed. No new browser E2E/build, cloud infrastructure, DNS modification, managed Google login, live content release, reference-solution execution, off-host backup, delivered notification, or staging rollback is claimed. Web source and dependency lock files were unchanged.

FastAPI/Starlette and Authlib emit the existing upstream HTTPX deprecation warnings. The API acceptance suite passes despite them; retain dependency-update follow-up.

Schema revision `0002` is additive, but original M1 application images insist on readiness at `0001`. A production application rollback must use a revision-compatible image; do not discard content tables to accommodate an older image. Fixtures and simulated reviewers are test artifacts, never real content approval.

The owner selected Google sign-in and deferred remaining M1 work to proceed with M2. [M0](../milestones/m0-gate.md), [M1](../milestones/m1-gate.md), and [M2](../milestones/m2-gate.md) keep their outstanding human/operational gates.
