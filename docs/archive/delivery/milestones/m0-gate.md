# M0 gate — Product proof and specifications

**Decision:** NOT YET PASSED  
**Reason:** The specification package exists, but representative learner validation and accountable sign-off require real people and have not occurred.  
**Next review:** After 15 valid pilot sessions and disposition of all critical findings.

## Owner update — 2026-10-02

Sathish confirmed no learner sessions have happened yet. He will guide fifteen adults in India, targeting completion by 12 October 2026, with unpaid online/in-person sessions and written notes only. Private Google Drive records will be deleted 30 days after actual completion. Required track/language, beginner, and accessibility recruitment coverage was confirmed as achievable; the intended V1 scope was reconfirmed.

Reviews will happen with reviewer identities kept private. No completed approval has been supplied. See the [pilot plan](../../research/m0-pilot-plan.md) and [private review record](../../research/m0-private-review-record-template.md). Privacy approval of the prepared notice is still required before recruitment. Confirmed arrangements do not pass learner-evidence or sign-off gates.

## Entry criteria

| Criterion | Evidence | Result |
|---|---|---|
| V1 problem, audience, promise, and exclusions documented | `../../product/v1-product-requirements.md` §§1–7 | Pass |
| Three launch tracks and three languages fixed | `../../../contracts/product/m0-contracts.json` | Pass |
| Deterministic-first authority fixed | PRD §6 and machine contract | Pass |
| DSA-first, domain-neutral platform boundary fixed | PRD §§2, 7, 22–25 | Pass |

## Exit criteria

| Gate | Required evidence | Current result |
|---|---|---|
| Representative validation | Five valid sessions each for Foundations, Interview, and Competitive; all nine track-language cells represented; participant log and recordings/notes consented | Blocked — recruitment and sessions not performed |
| Testable concierge prototype | Goal, routing, diagnostic adaptation, daily plan, assistance classification, evidence explanation, and missed-day recovery | Pass — model/contract checks and recorded browser golden journey; see validation report |
| Problem proof | At least 12/15 participants demonstrate the planning/help/proof problem without being led; at least 10/15 prefer the proposed loop to their current self-study workflow | Pending pilot |
| Flow usability | At least 12/15 can state their confirmed goal and next action; at least 11/15 understand assisted vs independent evidence | Pending pilot |
| Scope freeze | Product, Engineering, and Learning Design approve V1 must-have and not-V1 boundaries | Awaiting accountable sign-off |
| Metric freeze | Primary outcome, experiment unit, exclusions, and guardrails approved; no vanity metric controls mastery | Candidate contract ready; awaiting sign-off |
| Domain glossary | No unresolved conflicting definition among goal, track, curriculum, plan, evidence, mastery, retention, assessment, assistance, and operational failure | Candidate ready; awaiting review |
| Goal templates | All three templates pass structured examples and produce measurable, non-promissory goals | Automated structure passes; human comprehension pending |
| Policy matrices | Routing is total for supported launch inputs and produces reason codes; safety fallbacks are explicit | Automated invariants prepared; scenario review pending |
| Threat model | Assets, boundaries, misuse cases, prioritized threats, owners, and verification are approved | Candidate ready; security review pending |
| Content standard | Concept, exercise, assessment, language variant, review, licensing, accessibility, and quarantine contracts approved | Candidate ready; learning-design review pending |
| Architecture decisions | ADR-0001 through ADR-0006 accepted, including consequences and revisit triggers | Candidate ready; engineering/security review pending |
| Critical risks owned | Every critical/high M0 risk has one accountable role and target milestone; no anonymous “team” owner | Candidate threat register ready; people not assigned |
| Controlled progression | The product owner explicitly authorized M1 foundation engineering on 2026-09-29 while retaining all human M0 gates as pending | Exception recorded — does not convert M0 to PASS |

## Required sign-off

Names cannot be replaced by tool output or an AI-generated approval.

Reviewer names may be held in a private register instead of this repository. Each approval must be attributable to an actual person and include date, decision, reviewed versions, and an opaque evidence reference accessible to authorized gate reviewers. Public rows remain pending until that evidence exists. Withholding names does not waive reviews.

| Role | Accountable decision | Name | Date | Decision |
|---|---|---|---|---|
| Product owner | Problem, scope, goals, metrics, pilot result | — | — | Pending |
| Engineering owner | Feasibility, architecture, delivery risks | — | — | Pending |
| Learning-design owner | Competencies, evidence, content/assessment validity | — | — | Pending |
| Security/privacy owner | Threat model, data boundaries, risk acceptance | — | — | Pending |
| Design/accessibility owner | Critical journey comprehension and accessibility plan | — | — | Pending |

## Stop conditions

Do not enter M1 if any condition is true:

- Fewer than five valid pilot sessions exist for any track.
- A participant can be routed to unsupported content without an explicit waitlist outcome.
- “Mastery,” “independent,” or “meaningful session” has multiple operational meanings.
- The tutor can access assessment solutions or write learner state.
- The application and untrusted code runner share a security boundary.
- A critical threat lacks a mitigation, verification method, or accountable owner.
- The primary learning outcome cannot be calculated from immutable events.
- The team cannot explain what is deliberately excluded from V1.

## Gate procedure

1. Run `powershell -ExecutionPolicy Bypass -File scripts/validation/test-m0-contracts.ps1` from the workspace root.
2. Attach the pilot evidence summary and participant coverage table.
3. Record every material finding as accept, change, defer, or reject with rationale.
4. Update affected contracts and rerun validation.
5. Obtain the five sign-offs above.
6. Change the machine contract status from `candidate` to `approved` and record the approved version.
7. Ordinarily start M1 only after the final gate result is `PASS`. The product owner authorized a scoped engineering exception on 2026-09-29; it permits reversible M1 foundation work but does not waive learner validation, accountable sign-off, or any production-launch gate.
