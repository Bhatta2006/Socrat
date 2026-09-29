# ADR-0004: Append-only evidence with deterministic projections

- **Status:** Proposed
- **Date:** 2026-09-29
- **Decision owners:** Engineering, Learning Design, Data
- **Review by:** M0 gate

## Context

Mastery and curriculum decisions can materially affect a learner. Scoring bugs, invalid content, policy changes, duplicate delivery, and operational failures must be repairable without losing history or silently rewriting why a decision occurred.

## Decision

Store immutable source attempts, assistance/exposure state, operational validity, scoring results, and evidence events. Derive mastery, confidence, misconception, curriculum, and progress read models through versioned deterministic projectors.

Every event has a globally unique ID, aggregate sequence/idempotency semantics, schema version, relevant content/policy/model versions, and recorded time. Cross-boundary publication uses a transactional outbox. Corrections add compensating/repair events; they do not edit historical facts.

Snapshots may accelerate reads but are disposable and reproducible from retained authoritative events plus versioned configuration.

## Consequences

- Exact replay, audit, and learner-impact analysis become possible.
- Storage and projector/migration discipline are more complex than mutable score columns.
- Privacy deletion needs a designed separation between personal identifiers and required non-identifying audit facts.
- Event schema compatibility and ordering/idempotency tests are release gates.

## Rejected alternatives

- Mutable mastery-only records: cannot explain or safely repair prior decisions.
- Full general-purpose event sourcing for every UI action: unnecessary complexity; only decision-bearing domain evidence is authoritative.

## Verification

- Duplicate and reordered delivery cannot produce more than one evidence effect.
- Rebuilding projections from the same event/config versions yields byte-equivalent canonical state.
- A quarantined item repair identifies and recomputes every affected learner decision.

