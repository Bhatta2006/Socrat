# M6 local validation report

Date: 5 October 2026. Scope: repository implementation and local synthetic validation. M6 external acceptance is pending; execution remains disabled.

The preceding M5 Docker follow-up passed all five previously skipped PostgreSQL tests and a schema 0005 backup/restore. This increment implements the M6 editor, autosave/resume, signed durable broker, immutable source/runtime/test pins, quotas, separate gVisor-only worker recipes, resource controls, hidden-output sanitization, signed exactly-once results, M4 diagnostic/evidence integration, and M5 runtime-capability filtering.

| Check | Actual result |
|---|---|
| Complete regression | 173 passed, including PostgreSQL; 24 dedicated-host tests skipped explicitly; 91.73% API coverage, above the required 85% |
| Focused final execution/worker checks | 19 passed after the empty-draft fix; further worker checks below passed after startup-failure classification |
| Worker/contract validation | Nine passed: signature/expiry/hash tampering, no-runc fallback, cosign failure, complete-cgroup CPU accounting/path safety, exported schemas, and unscored sandbox startup/control failure |
| Browser regression | 32 passed across desktop/mobile, including six Monaco cases: actual self-hosted assets, autosave/reload, contrast, Run/Submit payloads, escaped output, and viewport fit |
| M6 PostgreSQL persistence | Two passed: signed Submit, original callback retry, hidden-output persistence secrecy, immutable-job triggers, and concurrent workers/callbacks yielding one claim and one evidence fact |
| Schema 0006 operations | Upgrade and isolated backup/restore passed on PostgreSQL 17 using an ephemeral localhost port |
| Static/web checks | Ruff formatting/lint, mypy, TypeScript passed; production build checked |
| Application Docker builds | API and web builds passed; non-root API image import smoke passed with schema 0006 and execution disabled |
| Staging proxy | Pinned Caddy configuration validation passed; public worker endpoints denied |
| Inherited prototype | 13 Node tests passed |
| Documentation/contracts | 164 passed, zero failed; local links, schemas, and placeholder checks |
| Dependency/asset security | npm audit reports zero vulnerabilities; shipped ESM assets contain patched DOMPurify 3.4.16 and no 3.4.15; all six Monaco cases passed again after rebuilding |

The Monaco API fixtures test editor behavior, not live grading. Nine-cell broker tests use synthetic signed worker facts, not executed reference solutions. Runtime image references in tests are synthetic digests; no production pack or runtime image was published. Mobile Chromium emitted Monaco clipboard-permission/cancellation diagnostics during emulation, although the stated assertions passed; real-device accessibility/editing acceptance remains open.

Docker Desktop reports ordinary runtimes and no `runsc`. Consequently the 24 opt-in dedicated-host checks (21 malicious corpus cases plus 3 cross-language semantic scenarios) are explicitly skipped. Live corpus/kill/egress/metadata/mount proof, compatible attested runtime builds and scans, calibrated Java overhead, beta-load declaration, per-language p95 at 2× load, soak/availability, staging drills, ADR approval, and external security review remain required by the [M6 gate](../milestones/m6-gate.md). No containment, latency, learner-effect, or launch-readiness claim is inferred from test doubles or application-container builds.

The first browser run failed because the current Chromium executable was not on the default lookup path. Using the existing workspace browser cache resolved this. The initial UI fixture also omitted the calibration list response; correcting the fixture allowed all six Monaco cases to pass. The implementation does not mask either issue.

A final correctness check found that deleting all source could leave the prior draft available to Run. Empty drafts now save and reload correctly, and Run/Submit explicitly rejects them before queueing. Focused regression passed after this fix.

Monaco 0.57.0 includes a vendored sanitizer copy affected by [GHSA-p98j-92pf-mc4p](https://github.com/advisories/GHSA-p98j-92pf-mc4p). The build pins DOMPurify 3.4.16, replaces the vendored ESM import with that patched dependency, and bundles local module workers. Dependency audit and generated-asset inspection both passed; replacing only the dependency would leave the prebuilt/vendor copy unchanged.
