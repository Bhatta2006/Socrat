# M0 gate — Product proof and specifications

**Decision:** NOT YET PASSED  
**Reason:** The specification package exists, but representative learner validation and accountable sign-off require real people and have not occurred.  
**Next review:** After 15 valid pilot sessions and disposition of all critical findings.

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
| Testable concierge prototype | Goal, routing, diagnostic adaptation, daily plan, assistance classification, evidence explanation, and missed-day recovery | Pass — 13/13 model tests, 116/116 contract checks, browser golden journey; see validation report |
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
| Controlled progression | The product owner authorized M1 foundation engineering on 2026-09-29, then closed M1 and authorized M2 work on 2026-09-30 while retaining all human M0 gates as pending | Exceptions recorded — do not convert M0 to PASS |

## Required sign-off

Names cannot be replaced by tool output or an AI-generated approval.

| Role | Accountable decision | Name | Date | Decision |
|---|---|---|---|---|
| Product owner | Problem, scope, goals, metrics, pilot result | — | — | Pending |
| Engineering owner | Feasibility, architecture, delivery risks | — | — | Pending |
| Learning-design owner | Competencies, evidence, content/assessment validity | — | — | Pending |
| Security/privacy owner | Threat model, data boundaries, risk acceptance | — | — | Pending |
| Design/accessibility owner | Critical journey comprehension and accessibility plan | — | — | Pending |

## Stop conditions

Under the ordinary milestone sequence, do not enter the next engineering milestone if any condition is true:

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
7. Ordinarily start engineering milestones only after the final M0 gate result is `PASS`. The product owner authorized scoped M1 work on 2026-09-29 and M2 progression on 2026-09-30. These decisions do not waive learner validation, accountable sign-off, or any production-launch gate.
