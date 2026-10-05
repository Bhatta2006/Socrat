# M6 gate

Repository implementation is reviewable. **M6 is not approved for learner exposure.** Earlier milestone approvals remain open where their records say so.

| Requirement | Repository evidence | Acceptance still required |
|---|---|---|
| Monaco, autosave/resume, Run/Submit | Desktop/mobile fixtures; real local Monaco assets; revisioned draft and signed broker tests | Accessibility and mobile editing review on released content |
| Durable ownership and exactly-once facts | SQLite and PostgreSQL tests; schema 0006 migration/restore; authenticated callbacks and immutable pins | Hosted CI and staging multi-worker races/incident drill |
| Three attested runtimes | Digest-only profiles, Dockerfile recipes, cosign verification, no runc fallback | Build compatible pinned Python/C++20/Java21 images, SBOM/vulnerability scans, signature references, reference/starter execution evidence |
| Resource/isolation security | Explicit sandbox controls, aggregate cgroup-v2 CPU accounting, signed protocol, 21 opt-in corpus cases and cleanup probes | Actual gVisor corpus pass for all languages; seccomp/AppArmor review; metadata/IPv6/DNS/egress and cross-job tests; kill verification and compromise game day |
| Semantic equivalence | Three opt-in shared-input semantic fixtures | Real runtime fixture results and released-exercise language attestations |
| Performance/availability | Dedicated-host 2× concurrency baseline script with per-language p95 and failure thresholds | Declared beta load, end-to-end broker/worker load and soak, p95 <4 seconds and ≥99.5% availability; calibrated Java overhead |
| External review | Threat model and operational rollback instructions | External security review, closed findings, named Security/Platform/Engineering acceptance, ADR re-review |

Docker Desktop on the validation host does not expose `runsc`. The live gates are skipped explicitly, never treated as passed, and execution is disabled in staging. Ordinary application-container builds cannot satisfy sandbox acceptance.
