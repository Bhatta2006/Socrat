# ADR-0002: Deterministic authority with bounded AI advice

- **Status:** Proposed
- **Date:** 2026-09-29
- **Decision owners:** Product, Engineering, Learning Design, Security
- **Review by:** M0 gate

## Context

Curriculum and exercise selection benefit from structured learner evidence and may occasionally benefit from interpreting unstructured context. LLMs are non-deterministic, provider-dependent, fallible, and susceptible to prompt injection. The product’s core trust claim requires reproducible safety, eligibility, mastery, and assessment decisions.

## Decision

Deterministic, versioned services own:

- eligibility, coverage, prerequisites, and exposure;
- diagnostic routing and early-stop constraints;
- mastery, confidence, retention, and evidence classification;
- the baseline curriculum, exercise ranking, workload, and difficulty;
- assessment separation, scoring finalization, and all state writes.

An LLM may parse optional goal text into a learner-confirmed proposal, phrase policy-bounded tutoring, propose qualitative feedback, or rank 3–8 preapproved curriculum candidates. The advisor starts disabled/shadow-only. Every output is schema-validated, version-checked, constrained to supplied IDs, deterministically revalidated, and logged beside the baseline. Failure uses the baseline or curated fallback.

No model identity receives database write credentials or assessment solutions.

## Consequences

- Core learning remains functional when models are disabled, slow, expensive, or wrong.
- Engineering must build a high-quality deterministic baseline before testing AI lift.
- AI cannot freely generate a curriculum, which reduces novelty but protects auditability and safety.
- AI complexity is accepted only after measured improvement in later independent performance.

## Rejected alternatives

- LLM-first autonomous tutor/planner: cannot meet reproducibility, security, or assessment-integrity requirements.
- No LLM capability ever: prematurely excludes useful language interpretation and bounded personalization experiments.

## Verification

- Kill all model access in tests; the complete non-chat core journey still succeeds.
- Feed hallucinated/stale/out-of-envelope IDs; none can change state.
- Replay the same deterministic inputs/version/seed; structural decisions match exactly.

