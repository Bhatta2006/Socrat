# Socrat Repository Assessment and Adoption Register

**Status:** Decision-ready; reviewed 2026-09-29  
**Scope:** Repositories proposed for the DSA V1 platform  
**Authority:** This document refines the technical choices in the [V1 product requirements](../product/v1-product-requirements.md). It does not authorize installing a dependency without normal security, license, and proof-of-concept review.

## Executive decision

Adopt a deliberately small production stack. The valuable repositories are the ones that remove commodity work while leaving the learning engine, content truth, and security boundary under Socrat control.

**Adopt now or at the named milestone:** CodeMirror 6, Alembic, Hypothesis, Schemathesis, axe-core, Locust, NetworkX (admin validation only), Promptfoo, gVisor, Dolos (later integrity workflow), Langfuse, PostHog Cloud, Sentry Cloud, and pgvector as an optional database capability.

**Adopt only after a narrow proof of fit:** LiteLLM, Instructor, GrowthBook, Taskiq, Payload CMS, Auth.js, Firecracker, and an FSRS implementation.

**Reference or research only:** catsim, pyBKT, py-irt, tutor-agent, socratix, DSPy, quizzer, and AI Question Paper Generator.

**Do not adopt for V1:** Piston or nsjail as the production code sandbox; Judge0 Community Edition; JPlag; self-hosted Zitadel; Nhost; LangGraph and multi-agent frameworks; Strapi and Directus as core content systems; and k6.

The most important distinction is this: **the deterministic learner model, mastery updater, prerequisite eligibility engine, curriculum optimizer, exercise ranker, and assessment scoring are Socrat code.** Third-party projects can accelerate surrounding infrastructure, never replace those decision systems.

## Decision legend

| Decision | Meaning |
|---|---|
| **Adopt** | Approved for the named V1 milestone after normal version pinning, SBOM/dependency scanning, and integration tests. |
| **Conditional** | Run a time-boxed proof of concept against named exit criteria before committing. Keep an interface that permits replacement. |
| **Later** | Sound fit, but not needed to prove the learning loop. Reconsider only at the stated scale or product trigger. |
| **Reference** | Learn from algorithms/patterns; do not copy code or make it a runtime dependency. |
| **Reject** | Do not introduce into the V1 production path. |

## Non-negotiable integration rules

1. Pin exact versions or image digests; record every dependency in an SBOM and scan it in CI.
2. Dependencies never receive database credentials broader than their function requires.
3. Learner code is untrusted. The execution boundary is separate from the API, worker queue, LLM stack, and editorial tools.
4. All content, graph, policy, prompt, runtime, and assessment versions are immutable once published. A CMS can draft content but cannot bypass the publish contract.
5. Deterministic rules remain runnable when LLM, analytics, experimentation, observability, or a SaaS product is unavailable.
6. An LLM may only recommend within a deterministic candidate envelope. No dependency may let a model directly write mastery, choose a hidden assessment item, or bypass a prerequisite.
7. Copyleft/source-available licensing must be reviewed by counsel before use. A network/API boundary does not by itself settle license obligations.
8. Every SaaS vendor needs a data-processing, retention, region, and deletion review before learner data is sent.

## Summary decision matrix

| Repository / service | Decision | V1 milestone | Why / boundary |
|---|---|---|---|
| CodeMirror 6 | **Adopt** | M6 / demo | MIT; exact pins for state, view, commands, language, autocomplete, search, lint and Python/C++/Java packages. First-party maintained editor; no CDN or wrapper. See ADR 0007. |
| Monaco Editor | **Removed** | Demo recovery | Replace the default asset preparation pipeline with CodeMirror; no optional editor until a demonstrated requirement warrants two implementations. |
| psutil 7.2.2 | **Adopt for local development execution** | Demo | BSD-3-Clause; bounded process-tree memory/PID/CPU observation on POSIX and process-list assertions on both platforms. Windows containment itself uses Job Objects. Production Docker execution does not import it. |
| LiteLLM | **Conditional** | M8 | Useful provider abstraction; hide behind Socrat `LLMGateway` and keep provider-native fallback. |
| Instructor | **Conditional** | M8 | Helpful Pydantic retry/validation ergonomics, but overlaps with provider-native JSON Schema + Pydantic. |
| Langfuse | **Adopt, deployment-gated** | M8 | Prompt/version/trace observability; Cloud only after privacy approval or self-host with dedicated ops. |
| gVisor | **Adopt** | M6 | Primary production container isolation layer for learner-code workers. |
| Firecracker | **Later** | Post-beta scale/security review | Strong microVM isolation but real host, kernel, KVM, image, and Jailer operations burden. |
| Taskiq | **Conditional** | M1/M6 | Fine for non-critical async work with Redis Streams, but its package classifies itself as alpha. |
| Alembic | **Adopt** | M1 | Standard SQLAlchemy migration tool; use expand/backfill/verify/contract migrations. |
| NetworkX | **Adopt, narrow** | M2 | Graph import/publish validation and authoring tooling only; do not put it in hot request paths. |
| Hypothesis | **Adopt** | M4/M5 | Property-test deterministic mastery/planning invariants. |
| GrowthBook | **Conditional** | M12 | Strong experiment analysis; select one flag/assignment owner and avoid overlapping PostHog flags. |
| Piston / nsjail | **MVP-only / reject for production** | M0 only | May accelerate a private pilot; cannot satisfy V1 sandbox requirements without owning hardening. |
| Judge0 CE | **Reject** | — | GPL-3.0 and an architectural/security fit mismatch for the planned isolated broker. |
| FSRS / ts-fsrs | **Later, use Python-compatible implementation** | After retention calibration | Good algorithm family; do not run a TypeScript scheduler as the source of truth for a FastAPI service. |
| catsim | **Reference / conditional research** | After calibrated item bank | CAT algorithms require calibrated item parameters; no V1 runtime dependency. |
| pyBKT / py-irt | **Reference** | After sufficient longitudinal data | Potential future modeling research, not a V1 mastery replacement. |
| tutor-agent / socratix | **Reference** | M8 design | Mine patterns only; custom policy ceiling and leakage tests remain authoritative. |
| Promptfoo | **Adopt** | M8 | CI-gated gold sets and red-team cases; run trusted configs in isolated CI. |
| DeepEval | **Later / choose one** | M8+ | Do not standardize both it and Promptfoo initially; add only for a demonstrated pytest-native gap. |
| DSPy | **Reference** | Post-beta | Offline prompt experimentation only; no runtime optimizer. |
| quizzer / AI Question Paper Generator | **Reference** | Content tooling research | Do not inherit their question quality, licensing, or scoring assumptions. |
| Dolos | **Later, adopt** | M9/project integrity | Similarity signal for human review, never an automatic cheating verdict. |
| JPlag | **Reject for V1** | — | GPL-3.0; Dolos covers the initial use case with a permissive license. |
| Auth.js | **Conditional** | M1 | Only if Next.js is intentionally the auth BFF; otherwise managed OIDC plus FastAPI validation is simpler. |
| Zitadel self-hosted | **Reject** | — | Current repository is AGPL-3.0; managed offering is a separate commercial/vendor decision. |
| Payload CMS | **Conditional** | M2/M7 | Consider only when editorial throughput justifies a second Node service; never source of runtime truth. |
| Strapi / Directus | **Do not select** | — | No need to evaluate while Payload/custom admin remains the decision path. |
| Locust | **Adopt** | M6/M11 | Python load tests for API/runner SLOs; use isolated test environments. |
| Schemathesis | **Adopt** | M1 onward | OpenAPI fuzz/property testing in CI and staging. |
| axe-core | **Adopt** | M1 onward | Automated accessibility regression checks; it complements, not replaces, manual testing. |
| Turborepo | **Conditional** | M1 | Useful for a growing TypeScript workspace; it does not orchestrate FastAPI/Python builds. |
| PostHog | **Adopt Cloud, privacy-gated** | M1/M12 | Product analytics; send derived events, never raw code or transcripts. |
| Sentry | **Adopt Cloud, privacy-gated** | M1 | Error tracking; use SDK/service, not self-hosted source-available Sentry. |
| pgvector | **Later / enable-ready** | M8+ | Optional approved-content retrieval only; PostgreSQL queries and ACLs remain the source of truth. |
| Nhost | **Reject** | — | Replaces the FastAPI/PostgreSQL architecture instead of complementing it. |
| LangGraph / multi-agent frameworks | **Reject** | — | Adds workflow complexity without a V1 decision problem that needs autonomous orchestration. |

## Detailed assessments

### 1. CodeMirror 6 — Adopt at M6

The default coding workspace now uses locally bundled, pinned CodeMirror 6 modules for Python, C++ and Java. The shared editor interface preserves autosave, resume, readonly attempts, keyboard controls, contrast and real compiler diagnostics. Independent and assessment modes disable autocomplete.

Monaco has been removed. The paired production browser measurements found a 76.4% reduction in downloaded JavaScript, but CodeMirror's measured three-run median was slower (1,062 ms versus 570 ms). See [ADR 0007](adr/0007-code-editor.md) for the method and limits. This editor is for one source file; execution remains server-side and there is no embedded terminal or package installer.

### 2. LiteLLM — Conditional at M8

**Fit:** It can centralize model routing, credentials, spend tracking, retries, fallbacks, and observability. Its active release cadence also means an unpinned deployment is a risk, not a benefit.[^litellm]

**Decision:** Use only through a thin internal `LLMGateway` interface. The rest of Socrat calls methods such as `request_socratic_hint()` and `request_selection_advice()`, never LiteLLM directly. Define provider-native fallback for every production capability.

**Required controls:** pinned image/package; allow-listed models/providers; per-capability tool/prompt budget; request redaction; typed structured response validation after the gateway; retry ceilings; circuit breaker; provider-outage fallback to curated hints or deterministic selection; monthly upgrade review.

**Reject if:** it forces the product to expose a generic proxy to clients, complicates data residency, or cannot meet p95 latency/cost budgets in a spike test.

### 3. Instructor — Conditional at M8

**Fit:** Instructor is MIT-licensed, Pydantic-based, and supports multiple providers, including LiteLLM paths.[^instructor]

**Decision:** Run a two-day proof of concept. Compare it with direct provider-native JSON Schema/function calling plus Pydantic validation. Adopt only if it materially reduces provider-specific parsing/retry code without weakening observability or error handling.

**Boundary:** Valid JSON is not a correct curriculum, hint, or rubric. Instructor validates shape; Socrat validates allowed IDs, citations, policy, candidate envelope, and domain constraints.

**Likely outcome:** Useful convenience library, but not a foundational architecture dependency. It should be easy to remove.

### 4. Langfuse — Adopt, deployment-gated at M8

**Fit:** Langfuse OSS is MIT except its `ee/` directory; it provides tracing, prompt/version workflows, datasets, and evaluation facilities. Its self-host guide states production self-hosting is an operational responsibility, and some enterprise features require a license.[^langfuse]

**Decision:** Adopt as the LLM observability plane, not as the learner data store or experiment-assignment authority. Start with Langfuse Cloud only after a DPA, retention, region, and redaction review. If learner code/tutor content cannot leave the chosen region, self-host with ClickHouse/Redis/object-storage operational ownership—or defer traces until that work is funded.

**Required controls:** hash or redact learner IDs; never trace hidden tests or raw assessment answers by default; trace prompt/model/config versions; retain a Socrat-owned audit record; disable self-host telemetry if policy requires it.

### 5. gVisor and Firecracker — Adopt gVisor; Firecracker later

**gVisor:** Adopt gVisor as the initial container runtime for isolated code-execution workers. It has maintained release channels and `runsc`/containerd integration.[^gvisor] It is not a complete sandbox by itself: workers still require no egress, a read-only image, unprivileged user, dropped capabilities, cgroups, seccomp, resource limits, signed jobs, and isolated cloud credentials.

**Firecracker:** Technically excellent but operationally expensive. Firecracker is Apache-2.0, uses KVM, and its own production guidance requires patched host/guest kernels, restrictive seccomp, and its Jailer or equivalent constraints.[^firecracker]

**Decision:** Build the execution broker against a runtime interface. Use gVisor in M6. Evaluate Firecracker only after the closed beta demonstrates a need for stronger tenant isolation, lower tail latency at high concurrency, or a workload profile gVisor cannot meet. Never attempt to run both runtimes in the first beta.

### 6. Taskiq — Conditional; managed queues preferred for critical work

Taskiq and its Redis integration are MIT-licensed and actively updated, but the package metadata still classifies core Taskiq as development status “Alpha.” The Redis Streams broker supports acknowledgements; its Pub/Sub and list alternatives do not provide the same durability.[^taskiq]

**Decision:** Taskiq may run best-effort or recoverable tasks—analytics fan-out, notification scheduling, resource refresh, offline evaluation, and non-critical cleanup. Do not make it the sole reliability boundary for execution jobs, assessment finalization, mastery updates, or payment events.

**Preferred architecture:** transactional outbox in PostgreSQL → managed durable queue (SQS/Pub/Sub/Cloud Tasks or equivalent) for critical commands. If Taskiq is retained in beta, use Redis Streams, idempotent consumers, dead-letter behavior, replay tests, and a clear replacement interface.

### 7. Alembic — Adopt at M1

Alembic is MIT-licensed and purpose-built for SQLAlchemy migrations.[^alembic] It aligns with the FastAPI/PostgreSQL architecture.

**Required practice:** revision review, expand/backfill/verify/switch/contract migration pattern, production-size rehearsal, lock/timeout analysis, and a restore-tested rollback plan. Do not auto-run destructive migrations at application startup.

### 8. NetworkX — Adopt narrowly at M2

NetworkX is BSD-3-Clause and production-stable.[^networkx] Use it in graph import/publishing checks for DAG validation, topological ordering, orphan detection, prerequisite reachability, and authoring previews.

**Boundary:** Store and query the graph in PostgreSQL. Do not construct arbitrary NetworkX graphs per learner request in the hot path; the deterministic planner consumes prevalidated graph snapshots.

### 9. Hypothesis — Adopt at M4/M5

Hypothesis is MPL-2.0 and designed to shrink failing property-based tests to a minimal counterexample.[^hypothesis]

**Use:** Test mastery bounds, idempotency, replay equivalence, no mastery from content views, prerequisite closure, no sequestered assessment selection, time-budget constraints, no plan oscillation, and recovery monotonicity.

**Boundary:** Property tests supplement explicit decision-table fixtures and end-to-end learning journeys. They never prove the pedagogy itself is effective.

### 10. GrowthBook — Conditional at M12

GrowthBook provides feature flags, targeting, experimentation, and statistical tooling, but it is open-core: some directories use a separate enterprise license.[^growthbook]

**Decision:** Use it only if its experiment governance and analysis improve on a lean backend assignment service plus warehouse analysis. It should be the single owner of flags/experiment assignment if adopted; do not independently assign a user in PostHog, GrowthBook, and application code.

**V1 recommendation:** Keep deterministic cohort assignment in Socrat for learning-critical experiments, emit immutable assignment events, and use GrowthBook for experiment configuration/analysis only after validating licensing and SDK behavior. A user must never switch cohorts mid-program.

### 11. Execution shortcuts: Piston, nsjail, and Judge0

**Piston / nsjail:** Acceptable only for a controlled concierge prototype with no sensitive production data and explicit limits. Neither is an authorization to ship a multi-tenant learning-code execution service. The prototype must still expire behind a feature flag and never accumulate an incompatible API contract.

**Judge0 Community Edition:** Reject for V1. The upstream repository states GPL-3.0, not AGPL-3.0.[^judge0] More importantly, adopting a full online-judge product would make its sandbox/process architecture a central dependency while the PRD requires a dedicated, auditable execution broker. A hosted vendor is a separate procurement/security decision; it is not an embedded OSS shortcut.

### 12. Spaced repetition: FSRS — Later, Python-owned

`ts-fsrs` is MIT-licensed and actively maintained, but it is a Node/TypeScript scheduler.[^tsfsrs] Socrat’s authoritative learner state and scheduler live in FastAPI/Python.

**Decision:** Keep the simple, versioned V1 retention scheduler until its calibration data says otherwise. Then evaluate a Python-compatible FSRS implementation or a stable binding under a parity-test suite. Store only Socrat’s canonical review events and scheduling state; never let a browser scheduler become the source of truth.

**Adoption gate:** sufficient review history by track, clear evidence that the current scheduler underperforms, offline replay against held-out retention outcomes, and exact cross-runtime parity tests if a non-Python core is used.

### 13. CAT and knowledge-tracing packages — Research only

`catsim` is BSD-3-Clause and offers item selection, ability estimation, and stopping methods for calibrated IRT item banks.[^catsim] `pyBKT` and `py-irt` are MIT-licensed tools for future BKT/IRT work.[^pybkt][^pyirt]

**Decision:** Do not call them from the V1 diagnostic or mastery hot path. Their mathematics assumes item parameters and data quality that V1 will not have. Continue with a transparent custom diagnostic and Beta-Bernoulli heuristic, log the data needed for later calibration, and use these projects to inform offline research.

**Upgrade gate:** at least several hundred clean attempts per relevant item, stable item difficulty/discrimination estimates, held-out predictive improvement over the current method, fairness review across tracks/languages, and a migration plan that preserves raw evidence.

### 14. Tutor and question-generator projects — Reference only

The small tutor-agent/socratix and quiz-generation repositories may contain useful interaction patterns, but their scope, maintenance, evaluations, and pedagogy are insufficient to inherit as product logic. The GPL-3.0 AI Question Paper Generator must not be copied into proprietary application code.

**Decision:** Read their prompt structures, hint-ladder ideas, and validation tests. Reimplement only the concepts that pass Socrat’s own gold set, leakage checks, policy constraints, and human review. Generated questions remain quarantined until executable validation and content review complete.

### 15. Promptfoo, DeepEval, and DSPy — one primary eval path

**Promptfoo:** Adopt for declarative gold-set, regression, and red-team CI. It is MIT-licensed, but its own security policy says config and referenced scripts are trusted code and are not sandboxed.[^promptfoo] Run it in isolated CI with scoped provider credentials; do not execute untrusted prompt packs or pull-request configs with production secrets.

**DeepEval:** Apache-2.0 and pytest-friendly.[^deepeval] Do not add it at the same time as Promptfoo. Add only if the team has a concrete Python-native assertion/reporting need that Promptfoo cannot cover. Gold data and pass/fail contracts belong in Socrat’s repository, not a vendor dashboard.

**DSPy:** Reference only for offline prompt optimization experiments. It must not tune prompts or select models dynamically in a learner session.

### 16. Dolos and JPlag — later integrity signal, not a verdict

**Dolos:** Adopt later for code-similarity triage in project assessment and any future supervised assessment workflow. It is MIT-licensed, supports multiple languages through Tree-sitter, and provides a CLI/library/API workflow.[^dolos]

**Rules:** Run it asynchronously on submit, compare only against allowed corpora, exclude starter/template code, scope the corpus by language/problem/version, secure the code retention path, and present similarity to trained reviewers as a signal. Never automatically fail, accuse, or alter mastery solely from Dolos.

**JPlag:** Reject for V1. It is GPL-3.0. An internal service boundary may change operational exposure but does not eliminate legal review or make it necessary when Dolos satisfies the first requirement.

### 17. Authentication: Auth.js and Zitadel

**Auth.js:** ISC-licensed, but its own repository recommends Better Auth for new projects except where its specific stateless-session capability is required.[^authjs] Since Socrat’s core API is FastAPI, adding Auth.js can introduce a second session and identity boundary.

**Decision:** Start with a managed OIDC provider using Authorization Code + PKCE and validate sessions/tokens consistently in FastAPI and the web layer. Evaluate Auth.js only if Next.js explicitly becomes the authentication BFF and the team documents one authoritative session/token model.

**Zitadel:** The current repository is AGPL-3.0, following its 2025 licensing change.[^zitadel] Do not self-host it for V1 without legal approval and a strong reason. Its managed cloud is a separate vendor review, not a consequence of the OSS repository license.

### 18. Payload CMS, Strapi, and Directus — conditional editorial tooling

Payload has a practical editorial feature set—PostgreSQL support, drafts, versioning, autosave, and publishing workflows.[^payload]

**Decision:** Do not introduce it in M1. A focused custom admin interface backed by the same Socrat content schema is lower risk while the skill-pack contract is changing. Evaluate Payload at M7 if more than two non-engineer authors need concurrent draft/review/publish workflows or if custom admin work demonstrably blocks content production.

If adopted, Payload is an **editorial source** that exports a validated, signed, immutable skill-pack artifact to the core service. It never writes live learner data, mastery, assessment exposure, or published graph state directly. Do not adopt Strapi/Directus merely because they are alternatives; no current V1 requirement needs another CMS evaluation.

### 19. Locust, Schemathesis, and axe-core — adopt as quality gates

- **Locust:** MIT-licensed, Python-native, and appropriate for API/runner load tests.[^locust] Use it for p95 runner latency, queue saturation, submission spikes, and scheduled-assessment start simulations. Do not point it at production without a written test window and rate controls.
- **Schemathesis:** MIT-licensed, OpenAPI/GraphQL property-based API testing.[^schemathesis] Generate tests from FastAPI’s published OpenAPI spec in CI/staging, with authenticated/unauthenticated and authorization-negative cases.
- **axe-core:** MPL-2.0, maintained automated accessibility engine.[^axe] Run it through Playwright on onboarding, diagnostic, workspace, assessment, dashboard, and recovery flows. Manual keyboard/screen-reader review remains mandatory.

### 20. Turborepo — Conditional at M1

Turborepo is MIT-licensed and useful for the Next.js application plus shared TypeScript UI/API-client packages.[^turborepo]

**Decision:** Adopt only if the JavaScript/TypeScript side has at least two deployable packages or three shared packages. It will not manage FastAPI/Python dependency locking, migrations, or worker images. A simple root task runner combining `pnpm` and `uv` is sufficient initially; do not make Turborepo a false whole-repo build system.

### 21. PostHog, Sentry, and pgvector

**PostHog:** Adopt its cloud service only after privacy approval. PostHog’s docs characterize its self-hosted OSS option as hobbyist-oriented and recommend Cloud for most companies; its SDK licensing varies by package, so record the exact SDK used.[^posthog]

**Use:** activation, retention, experiment exposure, and derived product events. Never transmit raw code, tutor transcripts, hidden-test data, assessment responses, access tokens, or direct identifiers where a pseudonymous ID will do.

**Sentry:** Adopt the managed service/SDK under its commercial terms after the same privacy review. Do not call the self-hosted Sentry project open source: it uses a Functional Source License with a future Apache license.[^sentry]

**pgvector:** Enable-ready but defer use. Its PostgreSQL license is permissive.[^pgvector] Use only for retrieval over approved, versioned explanations/resources after lexical and relational retrieval prove insufficient. It cannot determine prerequisite satisfaction or access control.

### 22. Nhost, LangGraph, and multi-agent frameworks — reject for V1

Nhost is a capable MIT-licensed backend-as-a-service built around PostgreSQL, Hasura/GraphQL, auth, storage, and functions.[^nhost] That is precisely why it conflicts with the PRD’s FastAPI modular monolith: it replaces rather than accelerates the data/API/security model.

LangGraph itself is MIT-licensed and technically capable, but its value is orchestrating long-running stateful agent workflows.[^langgraph] Socrat V1 does not need autonomous agents. The product has bounded model calls and deterministic services. Adding a workflow/agent framework would create a second state machine beside the curriculum/session state machines and weaken auditability.

## Recommended implementation bundle by milestone

| Milestone | Adopted bundle | Explicit exclusions |
|---|---|---|
| M0–M1 Foundation | Alembic, Schemathesis, axe-core, Sentry Cloud (privacy-gated), PostHog Cloud (privacy-gated); optional Turborepo | Nhost, self-hosted Zitadel, CMS, task queue framework |
| M2 Skill packs | NetworkX, Hypothesis, custom admin/import contract | Payload until editorial need is proven |
| M4–M5 Deterministic learning | Hypothesis, catsim/BKT/IRT only in notebooks/offline research | Runtime CAT/BKT/IRT dependency |
| M6 Execution | CodeMirror 6, gVisor, Locust, Schemathesis | Piston/nsjail/Judge0 as production runtime; Firecracker unless separate scale gate passes |
| M8 AI assistance | Langfuse, Promptfoo, LiteLLM/Instructor only if POCs pass | LangGraph, DSPy runtime, untrusted Promptfoo configs |
| M9–M10 Assessment/integrity | Dolos, later Python-compatible FSRS only with evidence | JPlag as embedded dependency; automatic cheating labels |
| M12 Experimentation | GrowthBook only if it becomes sole experiment/flag authority | Split assignment ownership across tools |

## Proof-of-concept scorecards

### LiteLLM / Instructor POC

Run 200 representative structured requests for each bounded capability across primary and fallback providers.

- 100% schema failures become safe application errors, never learner-state writes.
- Provider fallback preserves request IDs, tracing, budgets, and model/prompt versions.
- P95 latency and cost are within the M8 budget.
- Removing Instructor leaves a straightforward provider-native path.
- Invalid candidate IDs, unsupported concepts, citations, or hint levels are rejected by Socrat validation.

### Taskiq POC

- Redis Streams only; never Pub/Sub or unacknowledged list queues for durable work.
- Kill workers mid-task and prove no duplicate mastery/assessment event survives idempotency handling.
- Simulate Redis outage, delayed acknowledgement, dead-letter/retry, and replay.
- Demonstrate replacement of the queue adapter with a managed queue without changing domain handlers.

### Payload POC

- Editorial users can draft, review, and schedule a skill-pack component.
- Publishing emits a validated immutable artifact; no direct write reaches core published tables.
- Graph version, exercise-language variant, rubric, and assessment policies pass the same validation as CLI imports.
- Disabling Payload does not prevent the learning API from serving published content.

### Firecracker POC

- Demonstrate Jailer, patching process, immutable image build, KVM host hardening, network denial, cgroup limits, cold-start/tail latency, and secure credential isolation.
- Compare cost, p95/p99 latency, density, and incident operations against gVisor under representative Python/C++/Java workloads.
- Adopt only if the measured security/performance advantage outweighs the operations ownership.

### FSRS POC

- Replay existing Socrat review logs without losing versioned events.
- Compare calibration and held-out retention accuracy with the custom scheduler.
- Confirm scheduler choice does not alter mastery without new evidence.
- Keep migration reversible and per-skill-pack configurable.

## Reassessment cadence

- Recheck licenses, security advisories, release support, and maintainer health before first introduction and at every major upgrade.
- Reassess Conditional dependencies at the milestone where they are needed; absence of proof means “do not adopt,” not “ship anyway.”
- Review SaaS data processing annually and before collecting new classes of learner data.
- Maintain `THIRD_PARTY_NOTICES`, SBOM, dependency owner, version, decision, renewal/upgrade date, and removal plan in the repository.

## Sources

[^monaco]: [Monaco Editor repository](https://github.com/microsoft/monaco-editor).
[^litellm]: [LiteLLM releases](https://github.com/BerriAI/litellm/releases).
[^instructor]: [Instructor project metadata](https://github.com/567-labs/instructor/blob/main/pyproject.toml) and [provider support](https://github.com/567-labs/instructor/blob/main/docs/index.md).
[^langfuse]: [Langfuse license statement](https://github.com/langfuse/langfuse/blob/main/CONTRIBUTING.md), [self-hosting guide](https://github.com/langfuse/langfuse-docs/blob/main/content/self-hosting/index.mdx), and [enterprise license notes](https://github.com/langfuse/langfuse-docs/blob/main/content/self-hosting/license-key.mdx).
[^gvisor]: [gVisor installation and release guidance](https://github.com/google/gvisor/blob/master/g3doc/user_guide/install.md).
[^firecracker]: [Firecracker FAQ/license](https://github.com/firecracker-microvm/firecracker/blob/main/FAQ.md) and [production-host guidance](https://github.com/firecracker-microvm/firecracker/blob/main/docs/prod-host-setup.md).
[^taskiq]: [Taskiq project metadata](https://github.com/taskiq-python/taskiq/blob/master/pyproject.toml) and [Taskiq Redis broker durability notes](https://github.com/taskiq-python/taskiq-redis).
[^alembic]: [Alembic repository](https://github.com/sqlalchemy/alembic).
[^networkx]: [NetworkX project metadata](https://github.com/networkx/networkx/blob/main/pyproject.toml).
[^hypothesis]: [Hypothesis license](https://github.com/HypothesisWorks/hypothesis/blob/master/LICENSE.txt).
[^growthbook]: [GrowthBook repository and licensing](https://github.com/growthbook/growthbook).
[^judge0]: [Judge0 repository and GPL-3.0 license](https://github.com/judge0/judge0).
[^tsfsrs]: [ts-fsrs repository](https://github.com/open-spaced-repetition/ts-fsrs) and [MIT license](https://github.com/open-spaced-repetition/ts-fsrs/blob/main/LICENSE).
[^catsim]: [catsim repository](https://github.com/douglasrizzo/catsim).
[^pybkt]: [pyBKT repository](https://github.com/CAHLR/pyBKT).
[^pyirt]: [py-irt repository](https://github.com/nd-ball/py-irt).
[^promptfoo]: [Promptfoo repository](https://github.com/promptfoo/promptfoo) and [security model](https://github.com/promptfoo/promptfoo/blob/main/SECURITY.md).
[^deepeval]: [DeepEval repository](https://github.com/confident-ai/deepeval).
[^dolos]: [Dolos repository](https://github.com/dodona-edu/dolos).
[^authjs]: [Auth.js repository](https://github.com/nextauthjs/next-auth).
[^zitadel]: [Zitadel repository](https://github.com/zitadel/zitadel) and [v3 license-change discussion](https://github.com/zitadel/zitadel/discussions/9529).
[^payload]: [Payload versioning/draft documentation](https://github.com/payloadcms/payload/blob/main/docs/versions/overview.mdx).
[^locust]: [Locust repository](https://github.com/locustio/locust).
[^schemathesis]: [Schemathesis project metadata](https://github.com/schemathesis/schemathesis/blob/master/pyproject.toml).
[^axe]: [axe-core repository](https://github.com/dequelabs/axe-core).
[^turborepo]: [Turborepo repository](https://github.com/vercel/turborepo).
[^posthog]: [PostHog self-host disclaimer](https://github.com/PostHog/posthog.com/blob/master/contents/docs/self-host/open-source/disclaimer.mdx) and [support/options](https://github.com/PostHog/posthog.com/blob/master/contents/docs/support-options.md).
[^sentry]: [Sentry self-hosted license](https://github.com/getsentry/self-hosted/blob/master/LICENSE.md).
[^pgvector]: [pgvector license](https://github.com/pgvector/pgvector/blob/master/LICENSE).
[^nhost]: [Nhost repository](https://github.com/nhost/nhost).
[^langgraph]: [LangGraph project metadata](https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/pyproject.toml).
