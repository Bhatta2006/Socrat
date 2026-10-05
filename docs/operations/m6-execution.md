# M6 execution operations

Keep `SOCRAT_EXECUTION_ENABLED=false` until the [M6 gate](../delivery/milestones/m6-gate.md) passes. Staging Compose intentionally fixes it to false; enabling requires a reviewed deployment overlay with private worker ingress and secret mounts. Upgrade to schema `0006` before enabling. Disable the flag for rollback; retain jobs, drafts, evidence, and the additive schema.

## Runtime provisioning

Provision a dedicated Linux execution host with local Docker, gVisor `runsc`, cgroup v2 CPU/memory/PID controllers, a reviewed Docker seccomp/AppArmor policy, private HTTPS access to the broker, and cosign. Do not share the application/database host. The driver explicitly targets the local Unix Docker socket and reads that host's cgroup accounting; remote Docker contexts are not supported. Do not mount the Docker socket inside learner containers.

Build `services/execution/runtime/python.Dockerfile`, `cpp.Dockerfile`, and `java.Dockerfile` from reviewed immutable upstream digest references. Supply `PYTHON_BASE` for all; `CPP_BASE` (GNU C++20 capable) and `JAVA_BASE` (Java21) for their recipes. Python and compiled-language base distributions must have compatible libc/shared libraries. Before signing, verify the helper, Python libraries, compiler/JDK versions, reference/starter solutions, SBOM and vulnerabilities under actual gVisor. No concrete production runtime digest is supplied by synthetic fixtures.

Example build shape (replace reviewed references locally):

```sh
docker build -f services/execution/runtime/cpp.Dockerfile \
  --build-arg PYTHON_BASE="$REVIEWED_PYTHON_DIGEST" \
  --build-arg CPP_BASE="$REVIEWED_CPP_DIGEST" -t "$CPP_RUNTIME_TAG" .
```

Publish/sign only through the approved release process. Each API/worker profile has `id`, `language` (`python`, `cpp`, `java`), `image` (`registry/name@sha256:...`), `attestation_reference`, and `limits`. Profiles must match the released exercise variant's `runtime_ref`. Default limits: CPU2s, wall5s, memory256MB, PID64, output10MB, disk10MB, compile15s. Java requires a separately reviewed memory/startup profile. Aggregate CPU includes startup/compiler cost; insufficient overhead calibration must withhold a runtime rather than score learner inefficiency.

The API needs `SOCRAT_EXECUTION_PROFILES` (JSON), distinct strong `SOCRAT_EXECUTION_SIGNING_SECRET_FILE` and `SOCRAT_EXECUTION_WORKER_SECRET_FILE` (48+ random characters), and explicit feature enablement. Daily user quota defaults 100, user pending 4, IP daily 500, global pending 100. IP quota hashes the trusted request peer; configure forwarding only from approved proxies and keep the API unreachable from public direct clients. Shared proxy addresses conservatively share the quota.

## Worker deployment

Install repository dependencies on the trusted dedicated host. Set `PYTHONPATH=/opt/socrat-execution/services/api/src:/opt/socrat-execution/services/execution/src`. The systemd template is `infra/execution/worker.service`; its Docker group membership is a trusted host-control privilege.

Provision a root-owned mode0600 `/etc/socrat-execution/worker.env` containing `PYTHONPATH`, private `SOCRAT_EXECUTION_API_URL` (HTTPS), `SOCRAT_PUBLIC_ORIGIN` (canonical application origin), unique `SOCRAT_EXECUTION_WORKER_ID`, `SOCRAT_EXECUTION_PROFILES`, `SOCRAT_EXECUTION_COSIGN_PUBLIC_KEY` (verification-key path), and the two distinct `SOCRAT_EXECUTION_SIGNING_SECRET` / `SOCRAT_EXECUTION_WORKER_SECRET` values from the secret manager. These secrets never enter runtime Dockerfiles, source payloads, or sandbox environment. Private ingress must preserve Origin and deny public access to worker routes; staging Caddy already denies them on its public endpoint.

Run `python -m runner.worker`. Preflight verifies each immutable image before heartbeats/claims. Capability leases last 30s; job leases expire after 600s and cannot be replayed by another worker. A poll reaps expired jobs into unscored failures. Repeated long bundles may outlast heartbeat freshness: measure this during soak and size the worker pool accordingly before rollout. Callback transport retries keep the exact signed envelope. Drain workers before key rotation; retain old job audit facts.

## API boundary

Owned learner endpoints: `POST/GET /api/v1/goals/{goal_id}/code-attempts`, `GET /api/v1/attempts/{id}`, `PATCH /api/v1/attempts/{id}/draft`, `POST /api/v1/attempts/{id}/runs`, `POST /api/v1/attempts/{id}/submit`, `GET /api/v1/attempts/{id}/runs`, `GET /api/v1/code-runs/{id}`. Mutations require session, Origin, CSRF; attempts/jobs require idempotency keys. Drafts require `expected_revision`; jobs require `draft_revision`. Custom stdin is allowed only on Run. A healthy Submit finalizes one independent attempt; operational failures can be retried with a fresh job key. M7 owns additional session lifecycle UX.

Private authenticated worker endpoints: `/api/v1/execution/worker/heartbeat`, `/claim`, `/result`. Claim returns a signed source/test envelope; result requires a signed, leased, pinned fact schema. Schemas live in `contracts/schemas/execution-*.schema.json`; regenerate using `scripts/validation/export-m6-contracts.py`.

## Dedicated-host validation

Only on the dedicated execution host with reviewed/signed images:

```sh
export SOCRAT_EXECUTION_GATE=true
export SOCRAT_EXECUTION_GATE_PROFILE_FILE=/etc/socrat-execution/profiles.json
export SOCRAT_EXECUTION_COSIGN_PUBLIC_KEY=/etc/socrat-execution/cosign.pub
uv run pytest services/api/tests/test_execution_sandbox.py -q
uv run python scripts/validation/execution-load.py \
  --profiles "$SOCRAT_EXECUTION_GATE_PROFILE_FILE" \
  --cosign-key "$SOCRAT_EXECUTION_COSIGN_PUBLIC_KEY" \
  --beta-concurrency "$APPROVED_BETA_CONCURRENCY" \
  --jobs-per-language 100 --output .cache/m6-load.json
```

The first command tests all languages for CPU/memory/output/disk/fork/timing and network/filesystem/environment/subprocess containment, followed by a clean-job probe; it also tests cross-language integer semantics. The load script measures dedicated-host service time at 2× declared concurrency. It fails below 99.5% success or p95 ≥4s per language; it does not replace end-to-end queue/load/soak proof. Extend the corpus after external review and retain machine results with host, image, policy, scan, and beta-load references.

Monitor authenticated API HTTP errors, job states/expiry/backlog, signed operational outcomes, capability freshness, per-runtime availability, queue/service latency and sandbox teardown. Existing HTTP metrics alone do not prove execution SLOs. Never export source, hidden inputs, or bearer tokens to monitoring. A runner incident: disable execution, stop claims, kill/reap all `socrat-*` sandboxes on the dedicated host, preserve restricted audit facts, rotate affected credentials, review evidence from the affected worker/time window, and rerun security/restore gates before enabling. No fallback to ordinary containers.
