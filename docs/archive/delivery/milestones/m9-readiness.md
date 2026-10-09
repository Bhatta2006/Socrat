# M9 prerequisite review

## Subsequent repository authorization

The owner's later request on 6 October 2026 explicitly directs M9 implementation. Repository work proceeded under that authorization, with validation continuing on 7 October; see the [M9 index](m9-index.md). The earlier conditional decision below is a historical readiness assessment. Its external release gaps remain open and are carried into the [M9 gate](m9-gate.md). Implementation authorization does not supply independent content, human, provider, gVisor or deployment acceptance.

## Historical conditional review

Reviewed 6 October 2026 against the owner's condition: move to M9 only if its prerequisites are not pending.

**Decision: prerequisites remain pending; M9 implementation has not started.**

Later owner direction on 6 October 2026 authorizes M7/M8 preparation with assigned reviewers, zero initial practice penalty and Oracle/gVisor deployment acceptance deferred until after milestone implementations. The [completion coordination record](../../operations/m7-m8-completion.md) tracks this changed immediate scope. It does not retroactively pass M7/M8 or remove the readiness gaps recorded here.

The [V1 roadmap](../../product/v1-product-requirements.md#363-milestone-dependency-chain) explicitly makes M9 dependent on M7 and M8. Its engineering standard distinguishes a repository implementation from a completed milestone: staging, telemetry, rollback and exit criteria must also pass. Earlier scoped deferrals authorized repository work; they did not mark these gates complete.

| Dependency | Available evidence | Pending prerequisite |
|---|---|---|
| M7 learning experience | Session/content implementation, synthetic nine-cell journeys, local PostgreSQL validation | Reviewed and published coverage, protected diagnostic inventory, calibrated policy/duration evidence, staff dogfood, human accessibility review and staging acceptance; see [M7 gate](m7-gate.md) and [remaining work](m7-index.md#remaining-acceptance-and-content-work) |
| M8 bounded assistance | Curated fallback, assessment exclusion, structured provider adapters, atomic Submit help pins, automated tests and model kill switches; working regional GLM and central-region Qwen generation | Independent per-cell quality/leakage evaluation, dependable latency and production token settings, provider privacy/pricing acceptance, deployed alert/outage/rollback exercises and reviewer sign-off; see [M8 gate](m8-gate.md) and [actual validation](../validation/m8-validation-report.md) |
| M6 execution, inherited through M7 | Broker and evidence implementation; PostgreSQL and migration/restore checks | Attested runtimes, dedicated gVisor security/semantic/load tests and external security acceptance. Docker Desktop has no runsc; see [M6 gate](m6-gate.md) |
| Earlier evidence/content/platform gates | Implemented contracts and local regression evidence | Preserved external approvals, reviewed inventory and relevant staging acceptance remain as recorded in each milestone gate; local testing does not close them |

The Docker-enabled API run passed 344 tests with 92.57% coverage; all 18 PostgreSQL tests ran successfully. These checks establish repository regression and persistence evidence. They do not supply the missing human, content, runtime, provider or staging evidence.

Before proceeding under this condition, run genuine independently reviewed M8 evaluation and resolve latency/production settings; complete the M7 content/quality/accessibility/staging acceptance; complete the inherited execution and relevant earlier gates; then record accountable acceptance decisions in the existing milestone records and recheck readiness. Provider generation now works. No synthetic result, default-off feature flag or successful authenticated model listing substitutes for those decisions.

Latest model follow-up: the complete older-prompt baseline produced 502 proposals from 504 cases, with 18 local policy passes and provisional same-model opinions. Qwen on us-central1 passed nine matched revised-prompt cases, as did GLM on its nine-case candidate; these cover only first-step questions on one exercise across nine cells. Qwen met four seconds once and had sample p95 9,609 ms. This establishes usable integration for further evaluation, not broad correctness/leakage or release readiness. Generated reviews cover all 210 content tasks but do not constitute the named reviewers' independent approvals.

Oracle deployment and dedicated runtime acceptance remain owner-deferred. Preparing or implementing M9 under an explicitly changed development scope can preserve those pending gates without enabling deployment, model rollout or mastery from unreviewed assessments. Under the owner's existing requirement that M9 prerequisites not be pending, the readiness decision above remains unchanged.

M9's future scope remains baseline/weekly/final forms, deterministic scoring, qualitative review, mastery gates and operational spaced repetition. Parallel-form review, contamination checks, boundary-score review, outage invariance and clock-controlled seven-day retention verification belong to M9 itself, rather than being prerequisites that already-existing milestones must implement.
