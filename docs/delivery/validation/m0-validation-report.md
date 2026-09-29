# M0 automated and prototype validation report

**Date:** 2026-09-29  
**Scope:** Authored M0 contracts and disposable concierge prototype  
**Overall automated result:** PASS  
**M0 milestone result:** NOT YET PASSED — learner pilots and accountable sign-off remain external gates

## Automated product-model tests

Command:

```powershell
node --test prototypes/concierge/model.test.mjs
```

Result: **13 passed, 0 failed** on Node.js v24.21.0.

Covered:

- exact three-language and three-track launch scope;
- acceptance of a zero-baseline Foundations learner;
- Foundations bridge for low-readiness Interview and Competitive learners;
- unsupported-language and unreleased-coverage waitlists;
- minimum-commitment and adult-confirmation rejection paths;
- malformed-input fail-closed behavior;
- deterministic plans for all 15 track × time-budget combinations;
- exact time-budget composition and independent-action invariant;
- hint-level evidence weights;
- diagnostic reason codes;
- capacity-bounded missed-day recovery with zero backlog;
- deterministic repeatability.

## Contract, document, and repository validation

Command:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/validation/test-m0-contracts.ps1
```

Result: **126 passed, 0 failed** after limiting the scan to governed source artifacts rather than generated dependencies.

Covered:

- required artifact presence and professional domain-oriented layout;
- no legacy `docs/m0` directory;
- machine contract version/status and exact launch enums;
- goal/routing/metric uniqueness and required fields;
- deterministic mastery authority and LLM prohibitions/fallback;
- six independently reviewable ADRs with decisions, consequences, and verification;
- 28 unique threat-register entries and critical sandbox invariants;
- honest M0 gate state and five-users-per-track requirement;
- all nine required concierge screens;
- accessibility/data-limit disclosures;
- UI use of the tested deterministic model;
- local Markdown link integrity;
- absence of unresolved placeholder tokens in governed artifacts.

## Browser golden journey

Verified in the Codex in-app browser against the localhost prototype:

1. Start screen disclosed research status and no data storage.
2. Interview goal selected with C++ and syntax-only experience.
3. Routing produced `accepted_with_bridge` and `foundation_prerequisites_required`.
4. Correct diagnostic reasoning produced `clean_reasoning_observed`.
5. Today plan contained four blocks totaling exactly 45 minutes.
6. An approach plus two hints produced `assisted` evidence with 65% candidate weight.
7. Three missed days produced zero backlog and preserved the 45-minute capacity.
8. Completion screen confirmed no response was stored.
9. Browser console contained zero errors or warnings.

Keyboard activation was used throughout the walkthrough. The current narrow viewport also exercised the responsive single-column layout.

## Non-automatable gates

These are deliberately not marked passed:

- 15 valid real-learner sessions, with five per track and all nine track-language cells represented;
- pilot comprehension/problem thresholds;
- disposition and retest of Critical/High findings;
- named Product, Engineering, Learning Design, Security/Privacy, and Design/Accessibility sign-off;
- actual entity/jurisdiction/privacy notice, retention schedule, vendor/region decisions, and named risk owners;
- external security review, which belongs before sandbox exposure rather than M0 prototype use.

Automated green checks prove consistency and expected prototype behavior. They do not prove product demand, learning efficacy, legal compliance, accessibility conformance, or production security.
