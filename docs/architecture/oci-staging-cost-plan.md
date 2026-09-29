# OCI staging cost and evolution plan

**Decision date:** 2026-09-29  
**Home region:** India South (Hyderabad), `ap-hyderabad-1`  
**Monthly planning ceiling:** USD 55 in the tenancy billing currency

## M1 private staging profile

| Resource | Initial choice | Cost control |
|---|---|---|
| Compute | One `VM.Standard.A1.Flex`, 2 OCPUs, 12 GB RAM | Terraform validation prevents a larger value; apply stops if Always Free capacity is unavailable rather than silently substituting a paid shape |
| Storage | 50 GB boot volume | No additional block volumes in the initial stack |
| Database | PostgreSQL container on the staging host | Suitable only for private staging; encrypted logical backups leave the host |
| Backup | Private, versioned OCI Object Storage bucket | 30-day application retention target; monitor stored bytes |
| Network | VCN, public subnet, internet gateway, network security group | No NAT gateway, paid egress architecture, or managed load balancer yet |
| Observability | OCI agent plus application metrics/logs | No paid third-party backend until alert volume and retention are budgeted |
| Budget | Compartment budget of 55 | Actual alerts at 50%, 80%, and 100%; forecast alert at 80% |

Alert amounts are approximately USD 27.50, USD 44, and USD 55 when the tenancy rate card is USD. OCI budgets notify; they are not spending circuit breakers. The owner must review the Cost Analysis page and all non-Always-Free labels before every apply.

## Why this is not the production topology

Hyderabad currently has one availability domain. A single VM also combines application and database failure domains. This is acceptable for an access-controlled staging environment used to prove migrations, backups, deploys, and rollbacks; it is not acceptable for public V1 availability or durable learner evidence.

Before public beta, move toward:

- independently deployable web/API/worker workloads;
- managed PostgreSQL or a separately operated database with point-in-time recovery;
- owned DNS, trusted TLS, managed OIDC, and a controlled ingress layer;
- tested off-host backup restoration and defined RPO/RTO;
- telemetry retention, alerts, and an incident route;
- a revised approved budget based on measured staging utilization.

## Stop conditions

Do not apply or expand the stack when:

- Hyderabad is not the tenancy home region;
- the selected shape or storage is not marked Always Free-eligible and the owner has not explicitly approved paid usage;
- the dedicated staging compartment and budget-alert recipients are absent;
- a plan creates resources outside `ap-hyderabad-1` or projects spending above USD 55;
- credentials, private keys, database passwords, or OIDC secrets appear in Terraform variables or state;
- the account is a temporary classroom lab that does not permit persistent Resource Manager state.
