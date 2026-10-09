# Native demo verification — 7 October 2026

Branch: `ramkrsna1` (created from the work on `sathish`). These checks demonstrate local sample behavior; they do not approve a release, staging gate, production runtime, or human review.

## Recorded Windows checks

- Python 3.12.14, Node 24.21.0, GNU C++20 GCC 16.1.0, Microsoft OpenJDK 21.0.12.1. The native doctor reports Python, C++ and Java ready. No Docker or WSL is required for these checks.
- Full API regression: **627 passed, 46 skipped, 0 failures, 0 errors** in 991.59 seconds. Existing environment-dependent skips remain skips. The later worker/process follow-up changes also passed the focused native suite: **42 passed** in 27.79 seconds.
- All **252 reference variants** passed their complete 20-case bundles through `local_process`: **84 Python, 84 C++, 84 Java**, 5,040 passed cases, 656.91 seconds. [Machine-readable results](reference-results.json) record the exact sample-pack digest. No execution result or hidden oracle was mocked.
- The native suite checks correct and wrong answers, real compile/runtime diagnostics, infinite-loop timeout, memory/process/output limits, environment scrubbing, temporary directory cleanup, and Windows process-tree containment. Windows Job Objects are assigned before suspended children resume. Failed infrastructure does not create mastery evidence.
- Fresh local SQLite bootstrap completed all seven historical sessions for both the Java interview and C++ competitive personas through the normal signed broker and actual native executions. The beginner has zero implementation evidence. This is fresh-database proof, **not yet a fresh-clone startup timing measurement**.
- Ruff check and formatting passed for 149 files; mypy passed for 83 source files. TypeScript, the final production build (all twelve route entries), and four compiler-diagnostic parser tests passed. The existing 13-test M0 model suite passed.
- All three desktop language journeys passed after the worker-heartbeat fix (29.6 / 30.0 / 30.8 seconds). All three mobile journeys passed in a separate final run after the 390-pixel layout corrections (30.8 / 28.8 / 30.8 seconds). [Browser results](browser-results.json) explicitly preserve the separate runs; this is not a claim that an earlier failing combined run passed. The journeys use clicks, real native compile errors, Run, assisted Submit with all 20 cases, exit check, baseline/weekly/retention, recovery, export and deletion. Screenshots and six successful videos are under `screens/`. Earlier failed attempts remain failures. The original **64-test browser regression passed** on desktop and mobile in 4.7 minutes after adapting routes and using normal keyboard entry for CodeMirror. No tests were removed or skipped.

## Editor measurements and removed files

The actual route-to-editor JavaScript body bytes fell from **4,963,761** (Monaco) to **1,169,363** (CodeMirror), a **76.4% reduction**. Three-run median editor readiness was **570 ms** versus **1,062 ms**: the smaller editor was slower in this small sample. [ADR 0007](../architecture/adr/0007-code-editor.md) explains the method and limits.

Removed tracked files: `apps/web/scripts/prepare-monaco.mjs`, `apps/web/scripts/monaco-entry.mjs`, and root `temp.py`. Monaco dependencies and its preparation hooks were removed. The old ignored generated assets were archived under `.cache/monaco-retired` after automatic deletion approval was blocked; they are excluded from Git and the served public directory.

## Proof boundaries

- Production intentionally retains Linux gVisor, attestation and private HTTPS worker transport. Native execution is explicitly insecure, development/test-only, and rejected in staging/production. The optional Docker demo backend remains unverified end to end after Docker Desktop filesystem stalls.
- Windows local execution and original references have been verified. POSIX process-group behavior must pass the new Ubuntu CI job before it is claimed as verified. GitHub CI has not yet completed for this branch.
- The original clean-clone Compose baseline is unverified: `before.png` records the earlier failed local startup, not a successful container baseline. The initial [audit](AUDIT.md) records source reachability limitations.
- The sample inventory covers fourteen concepts, all three tracks and languages. Its current protected assessment forms exercise the two root concepts; they are not comprehensive DSA certification or release-approved assessment content.
- Local native execution does not isolate untrusted host filesystem/network access. The interface displays “Local dev sandbox — not secure for untrusted code”. Generated credentials, databases, logs, browser request traces and private receipts stay out of Git.
