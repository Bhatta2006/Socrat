# M6 execution platform

The repository increment implements Monaco and an execution plane boundary for Python, GNU C++20, and Java 21. M6 launch acceptance remains pending; consult the [gate](m6-gate.md) and [actual validation](../validation/m6-validation-report.md).

Monaco assets are served locally, with no CDN dependency. Owned attempts save source every five seconds, on blur, and before Run/Submit. Revision checks protect concurrent drafts. Font size, light/dark/high contrast, accessible editor labels, public samples/custom input, history, and text-only output are available. There is no terminal or package-installation flow.

The API brokers immutable signed jobs and never executes learner source. The independently deployed worker authenticates expiring jobs and rechecks source/test hashes. Each case runs in a fresh gVisor sandbox using an attested digest-pinned runtime. The signed manifest binds language, image, compiler configuration, content digest, source hash, test digest, resource limits, nonce, and deadline. Worker callbacks are authenticated and signed, leased to one worker, and finalized idempotently.

Run uses public samples or custom input and produces no learning evidence. Submit uses the pinned test bundle. Hidden inputs, expected values, and reference solutions never reach browser payloads; hidden output is removed before persistence. A healthy Submit produces one implementation fact through the M4 adapter. Operational failures and withdrawn/expired diagnostic content produce no evidence. Diagnostic Submit also advances the issued M4 item. M5 code selection requires a current approved worker capability.

Schema `0006` adds owned immutable attempt snapshots, mutable revisioned drafts, signed immutable jobs, separable source artifacts, worker capability leases, and a singleton admission lock. User/IP/day and queue limits protect admission. M7 retains ownership of full teaching sessions and the reviewed launch content bank; M9 retains sequestered assessments.

See [operations](../../operations/m6-execution.md), [threat model](../../security/execution-threat-model.md), and [ADR-0005](../../architecture/adr/0005-isolated-code-execution-plane.md). ADR approval is still owned by its named reviewers.
