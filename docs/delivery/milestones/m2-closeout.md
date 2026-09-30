# M2 closeout handoff

M2 is the skill-pack **kernel**. Its PRD exit test is a sample DSA pack and a tiny non-DSA fixture through the same import path, strict graph/schema checks, immutable publishing, and a demonstrated bad-content rollback. It does not require the complete DSA curriculum, learner assignment, or Python/C++/Java execution platform. Those are later milestones.

## What the product owner needs to provide

1. **Staging access when ready.** Provide the owned staging hostname, a deployed PostgreSQL-backed environment, and a safe way for us to run the operator workflow. The M1 staging runbook describes the infrastructure and identity setup. Keep passwords and private keys out of chat and the repository. This step is deferred at the product owner's request; it remains open rather than being marked passed.
2. **Named independent reviewers.** Name people for domain correctness, learning design, accessibility/copy, rights, language coverage where applicable, and assessment separation. One person may hold several qualified roles, but the author cannot approve their own version or publish it. Reviewers must actually inspect the linked evidence before approving.
3. **If you want learner-eligible DSA content released during M2:** identify its accountable author and confirm original-work ownership or provide source terms permitting the intended use. The PRD's M2 kernel gate does not require this release; the checked-in DSA sample can remain draft. The eight external DSA sources are a draft link/metadata pool and are not presumed licensed for copying.

The first two inputs are needed to close the M2 PRD gate. The third is only needed if M2 also ships learner-eligible DSA content. Independent approval and a real staging run cannot be supplied by an automated test or by this agent.

## What engineering can complete before those inputs

- Validate a domain-neutral contract, explicit released/unavailable track-language cells, and mappings for removed/renamed concepts between versions.
- Keep the sample DSA and non-DSA manifests as drafts; import both through the same API and reject malformed graphs and coverage.
- Bind release candidates to evidence references for rights, accessibility, concept/exercise quality, assessment separation, language coverage where released, and a prepublication staging canary. Each reference has a location, SHA-256 digest, and plain-English summary. A reference alone does not prove that its contents were reviewed.
- Exercise role separation, immutable hashes, pinned old versions, quarantine, rollback, and audit/outbox creation in local and hosted automated checks.
- Prepare the operator review instructions and a staging rehearsal checklist. Report actual results; never enter placeholder evidence into a real candidate.

## Final M2 rehearsal when staging and reviewers are ready

1. Deploy a reviewed build and migrate a PostgreSQL staging database. Confirm health and the real identity path.
2. Sign in with separate named author, reviewer, and release-owner accounts. Import the DSA sample and non-DSA fixture through the same API.
3. Record the candidate evidence bundle and reviewers' decisions. Verify that a missing or rejected review blocks publication.
4. Run the candidate canary against the staging contract. Publish a valid sample version. Confirm its digest and released coverage, and reload a pinned earlier version.
5. Introduce a controlled bad-content version, quarantine it, and confirm the previous good release becomes active. Confirm audit and outbox delivery, then save the logs, identities, timestamps, and digests in the M2 validation report.

M2 is complete only after this rehearsal satisfies the PRD gate. Full DSA content review, cross-language execution tests, and learner routing remain tracked under M6–M9.
