# Staging runtime

This directory is the reviewed single-host staging runtime. It is deliberately separate from the developer `compose.yaml`: application images are immutable GHCR digests, back-end services are private, secrets are mounted as files, migrations are one-shot, and ingress is health-gated.

Required non-secret release inputs are written by `scripts/operations/release.py`. The five files under `SOCRAT_SECRETS_DIR` are:

- `postgres_password`
- `session_secret`
- `oidc_client_secret`
- `metrics_token`
- `grafana_admin_password`

Each file must be owned by the deployment account, mode `0600`, and contain one non-empty line. Never place those values in an environment file, Compose file, command history, Terraform input, or Git.

Only Caddy publishes public ports. Grafana binds to host loopback and is reached through an authenticated SSH tunnel. PostgreSQL, the worker, web process, and Prometheus remain on the internal Docker network. The API also joins a dedicated bridge network for outbound OIDC discovery, token exchange, and signing-key retrieval; it publishes no host port. The bridge supplies outbound connectivity, not a destination allow-list. Security review and the real OIDC drill must verify the approved provider can be reached; the learner-code execution boundary remains separate.

See [the staging runbook](../../../docs/operations/m1-staging-runbook.md) for controlled deployment, evidence collection, backup restoration, rollback, and incident response. A valid Compose render is not evidence of a deployed environment.
