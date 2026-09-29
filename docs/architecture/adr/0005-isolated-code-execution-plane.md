# ADR-0005: Isolate learner code in a separate execution plane

- **Status:** Proposed
- **Date:** 2026-09-29
- **Decision owners:** Security, Platform, Engineering
- **Review by:** M0 gate; design re-review before M6

## Context

Socrat executes adversarial Python, C++, and Java submissions. Language-level sandboxes and ordinary application containers are not a sufficient boundary. Execution must preserve hidden tests, avoid cross-job leakage, constrain resources, and distinguish infrastructure from learner failure.

## Decision

Use a dedicated execution broker and ephemeral, non-root, gVisor-class sandbox workers on isolated worker infrastructure. Workers have:

- no outbound network or metadata access;
- no cloud/application credentials;
- no host or shared writable mounts;
- pinned signed runtime image and immutable test bundle;
- CPU, wall, memory, PID, disk, output, and compile limits;
- one job security context and guaranteed teardown;
- a signed, expiring job manifest with nonce and idempotency key;
- a narrow sanitized result schema that reports execution facts, not mastery.

The application API never executes learner code. Firecracker remains a later defense-in-depth/scale option after the gVisor path is proven.

## Consequences

- This is the largest V1 security/operations investment and receives an external review before exposure.
- Run latency and infrastructure cost will exceed an in-process executor.
- Runtime images, broker protocol, malicious corpus, and incident response become owned products.
- Package installation, arbitrary networking, and user-supplied binaries remain out of scope.

## Rejected alternatives

- `eval`, subprocess, language sandbox, or nsjail alone in the API environment: inadequate containment.
- Embedding a complete online judge: creates central architectural/license/process dependency without removing security ownership.
- Firecracker first: stronger isolation potential but higher initial operational complexity for the small team.

## Verification

- Malicious fixtures cannot access network, metadata, secrets, host, hidden tests, or another job.
- Resource attacks terminate within declared bounds and workers are reaped.
- Results with altered manifest/image/test hashes are rejected.
- External security review and compromise game day pass before beta use.

