# M8 bounded AI assistance

Owner direction, 6 October 2026: review the codebase and milestone records, then proceed with M8 implementation. This authorizes repository engineering. It does not pass earlier release gates.

The prerequisite review found M4's append-only evidence and independent/assisted projection, M5's deterministic candidate filtering and replay, M6's owned attempt/draft/Submit broker, and M7's pinned session admission suitable for this integration. M6 had pinned `hint_level=0` for every attempt; M8 now captures durable assistance at Submit admission. No model can modify code, run jobs, assign mastery, or change a plan.

## Implementation

- Schema `0008`: immutable ordered tutor receipts, separately removable private reasoning/context/response artifacts, immutable Submit assistance pins, and append-only advisor shadow decisions.
- Authenticated owned tutor history/requests with Origin/CSRF protection, idempotency, revision checks, released-content checks and existing M7 session gates. Diagnostic/assessment attempts cannot access the tutor.
- Progressive level 1–3 help, track ceilings and a required learner action before escalation. Accessibility requests can skip within the permitted ceiling. Levels 4–5 require a completed Submit or explicit exit; these levels use authored content only. A missing authored scaffold falls back to a lower level.
- Small approved-content context: active task, selected language, concept excerpts, controlled misconception labels, saved learner source/reasoning, public run output and recent hints. Hidden test content, protected inventory, full pack payloads and identities are excluded. No model tools exist.
- Provider-neutral gateway plus OpenAI Responses and OpenAI-compatible chat adapters (including the owner's selected Nebius `zai-org/GLM-5.3-Flash`), exact model allow-list, a total network deadline, bounded request/response sizes, output-token cap, per-session/learner-day call and spend reservations, deterministic percentage rollout and independent kill switches. No automatic retries or shared personalized cache. A separate synthetic live smoke runner can test credentials/model access while deployment switches remain off; current live generation timeout evidence is recorded in validation.
- Strict structured-output validation, citation/range checks, conservative code/API/reference-overlap guards and curated fallbacks. Repeated rejected/unavailable proposals create durable operator review events. The validator is not a proof of semantic correctness or leakage safety.
- Prompt versions `tutor_1.0.0`, `tutor_1.0.1`, `advisor_1.0.0` with hashes, selected model, policy, context/output hashes, latency and token/reservation metadata. Tutor prompt ownership: Learning Design/AI Engineering; advisor ownership: Personalization Engineering. Named release reviewers remain unassigned.
- Last-ten-eligible-attempt dependency summary and gradual fading that asks for a stated plan. Revealed/scaffolded families cannot become fresh independent tasks through reopening. New plan replay inputs exclude those families; stale draft plans must be refreshed before confirmation.
- An operator-triggered advisor evaluates 3–8 production-planner candidates from a pinned revision. Only exact permutations pass; baseline and proposal are retained, measurable, and never applied. Sparse candidate sets are explicitly unavailable.
- Accessible text-only tutor panel, saved history, code autosave before hints, explicit learning-only explanation action, and assisted Submit labels.
- Private expert evaluation contract, per-cell quality reporting, protected operational metrics and cost/latency alert rules.

See [operations](../../operations/m8-assistance.md), [gate](m8-gate.md), and [validation](../validation/m8-validation-report.md).

## Preserved deferrals

M0 user research and human approvals, M1 deployed operations and relevant earlier external gates remain open. M6 dedicated-host gVisor/security/load acceptance remains deferred. M7's original limited-pilot bank is still an unreviewed offline draft; reviewers, learner calibration, staff dogfood, accessibility and deployed acceptance remain deferred. M8 does not publish that bank or enable execution/model traffic in staging.
