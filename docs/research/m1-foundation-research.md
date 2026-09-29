# M1 foundation research and decisions

**Reviewed:** 2026-09-29  
**Purpose:** Record the primary sources used before implementing the platform foundation.

## Decisions

| Area | Decision | Evidence and interpretation |
|---|---|---|
| Web boundary | Next.js App Router with a small client component only where state and browser interaction are required | [Next.js server/client components](https://nextjs.org/docs/app/getting-started/server-and-client-components) recommends Server Components by default and Client Components for state, effects, and event handlers. |
| Design system | Tailwind CSS 4 with daisyUI 5 and the monochrome `wireframe` theme | [daisyUI Next.js installation](https://daisyui.com/docs/install/nextjs/) documents the PostCSS and CSS plugin integration used here. |
| API lifecycle | FastAPI lifespan plus explicit migration release step | [FastAPI lifespan events](https://fastapi.tiangolo.com/advanced/events/) provide resource lifecycle handling; schema migration remains separate from application startup. |
| Identity | Managed OpenID Connect authorization-code flow with state/nonce validation; local login is development/test only | [Authlib Starlette client](https://docs.authlib.org/en/v1.6.9/client/starlette.html) documents discovery, redirect, token exchange, and parsed OpenID user information. A real provider must still be selected and integration-tested. |
| Database evolution | SQLAlchemy models with reviewed Alembic revisions | [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html) establishes the migration environment and revision workflow. |
| Service startup | Database health check, one-shot migration, then API/worker/web dependencies | [Docker Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/) documents health and completion conditions; Compose is local/rehearsal infrastructure, not proof of cloud staging. |
| Outbox concurrency | PostgreSQL row locking with `SKIP LOCKED`, transactional delivered markers, and bounded batches | [PostgreSQL locking clause](https://www.postgresql.org/docs/17/sql-select.html) defines the locking behavior. External brokers are deferred until measured throughput or integration needs justify one. |
| Restore | Custom-format `pg_dump` and isolated `pg_restore` smoke validation | [PostgreSQL 17 pg_restore](https://www.postgresql.org/docs/17/app-pgrestore.html) documents portable archive restoration and its trust warning. Only trusted Socrat-produced backups may be restored. |
| Infrastructure as code | OCI provider-specific Terraform for India South (Hyderabad), with a free-first single-node private staging profile and a USD 55 ceiling | [OCI regions](https://docs.oracle.com/en-us/iaas/Content/General/Concepts/regions.htm) identifies Hyderabad as `ap-hyderabad-1`; [OCI Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) documents home-region eligibility, A1 limits, and possible capacity shortages; [OCI Resource Manager](https://docs.oracle.com/en-us/iaas/Content/ResourceManager/Concepts/resource-manager-and-terraform.htm) supplies managed Terraform state and locking. |
| Staging runtime | A production Compose overlay with explicit image digests, health-gated dependency order, file-mounted secrets, private back-end network, and a single TLS ingress | [Docker's production guidance](https://docs.docker.com/compose/how-tos/production/), [startup-order contract](https://docs.docker.com/compose/how-tos/startup-order/), and [Compose secrets guidance](https://docs.docker.com/compose/how-tos/use-secrets/) define the implemented boundary. |
| Release artifacts | Publish `linux/amd64` and `linux/arm64` API/web images to GHCR only after `main` verification, then attach registry-backed build provenance | [GitHub's container publishing guidance](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images) and [artifact-attestation guidance](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations) support digest-addressed images and attestations. All actions are pinned to commit SHAs. |
| Telemetry | Private Prometheus plus loopback-only Grafana, bounded local retention, provisioned dashboard, and runbook-linked alerts | [Prometheus alerting configuration](https://prometheus.io/docs/alerting/latest/configuration/) defines rule and routing behavior. A human notification receiver remains an explicit external decision. |
| OCI CI identity | Prefer GitHub OIDC token exchange into OCI over long-lived API keys when the tenancy identity domain is available | [OCI workload identity federation](https://docs.oracle.com/en-us/iaas/Content/Identity/api-getstarted/token_exchange_grant_type_workload_id-federation.htm) documents GitHub Actions JWT exchange for a resource principal session token. Tenancy-side configuration and least-privilege policy require administrator approval. |

## Explicitly unresolved

- OCI tenancy/compartment identifiers, account entitlement confirmation, and DNS ownership;
- managed PostgreSQL, OIDC, secrets, telemetry, and artifact-registry vendors;
- privacy/DPA approval and retention for each vendor;
- protected deployment environment and OCI workload identity (branch quality checks are now hosted and passing);
- production RPO/RTO proof and staging deploy/rollback evidence.

These are external decisions and exercises, not implementation details to silently guess. The local foundation fails closed when their required configuration is absent.
