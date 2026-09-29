# OCI staging infrastructure

This Terraform stack describes a cost-bounded M1 staging foundation in OCI India South (Hyderabad), region `ap-hyderabad-1`. It does not deploy automatically and contains no credentials.

## Cost and reliability profile

- one `VM.Standard.A1.Flex` instance capped at 2 OCPUs and 12 GB memory;
- one 50 GB boot volume;
- one VCN, public subnet, internet gateway, and restrictive network security group;
- one private, versioned Object Storage bucket for staging backups;
- a USD 55-equivalent monthly compartment budget with 50%, 80%, forecast-80%, and 100% alerts.

OCI budgets alert but do not stop spend. The module therefore also caps compute inputs and creates no load balancer, managed database, Kubernetes cluster, NAT gateway, or paid observability service. Confirm every resource is marked Always Free-eligible in the account before applying; availability and account entitlements remain OCI-controlled.

This single-node topology is suitable for private M1 staging and operational drills. It is not the V1 production topology: PostgreSQL shares the host, the region has one availability domain, and there is no high availability.

## Authentication and secrets

Prefer OCI Resource Manager or short-lived workload identity. Do not commit `terraform.tfvars`, OCI API private keys, database credentials, OIDC secrets, or application environment files. Terraform provisions the host baseline only. A separate protected release workflow installs images and runtime secrets.

## Validate without provisioning

```powershell
terraform -chdir=infra/oci/environments/staging fmt -check -recursive
terraform -chdir=infra/oci/environments/staging init -backend=false
terraform -chdir=infra/oci/environments/staging validate
terraform -chdir=infra/oci/modules/staging-foundation init -backend=false
terraform -chdir=infra/oci/modules/staging-foundation test
```

`plan` and `apply` require an OCI account plus the variables shown in `terraform.tfvars.example`. Applying this stack creates billable-capable cloud resources and requires explicit authorization.

## Domain boundary

The instance initially exposes an ephemeral IP. An owned staging hostname and approved certificate strategy are required before enabling staging OIDC, `Secure` browser sessions, or claiming the M1 HTTPS gate. Ports 80 and 443 are reserved for the later reverse proxy; the API and database are never exposed directly.

The final brand domain is not required for M1. Any deliberately selected, owned staging hostname is sufficient if DNS control, TLS issuance, OIDC callbacks, and later migration are documented. Runtime deployment and rollback are governed by the [M1 staging runbook](../../docs/operations/m1-staging-runbook.md).
