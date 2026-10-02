# M1 account setup checklist

**Updated:** 2026-10-02

**Status:** Owner inputs recorded; account setup and real deployment pending.

## Confirmed inputs

- Cloud: owner has an OCI account with Hyderabad home region (`ap-hyderabad-1`). Account persistence and entitlement have not been verified.
- Staging hostname: `socrat.dathcodes.dev`, supplied by the owner. DNS control and existing hosting remain to be checked.
- Error/spending alert recipient: `sathishdutt0@gmail.com`, approved by the owner.
- Engineering, Security/Privacy, and Operations approvals will be recorded privately.
- Managed sign-in provider: owner selected Google on 2026-10-02. The Google application, credentials, and Security/Privacy review remain pending.

## Account access and infrastructure

1. Confirm access to the OCI console, account entitlement, and Hyderabad Always Free capacity. Check whether a staging compartment or instance already exists before creating anything.
2. Use a dedicated staging compartment and restricted Resource Manager/workload access. Keep OCIDs and private operational details in local ignored configuration or restricted account settings; never paste API keys or private keys into chat.
3. Fill the non-secret infrastructure inputs in a private copy of `infra/oci/environments/staging/terraform.tfvars.example`: tenancy/compartment OCIDs, public SSH key, trusted administrator CIDR, and approved alert recipient. Use `socrat` as the proposed technical project key.
4. Plan the repository's existing Terraform stack in the authenticated account. Review region, shape/capacity, storage, network, budget currency, and projected charges. The 55 planning ceiling must be checked against the actual tenancy billing currency.
5. Obtain approval for that concrete plan before applying it, as required by the staging runbook. Account confirmation is not approval of an unseen plan. Do not silently switch to a paid shape if capacity is unavailable.
6. Provision only the reviewed stack, then record redacted resource references and the host's actual public IP. OCI budgets send alerts; they do not enforce a spending cap.

## DNS and TLS

Confirm who can edit `dathcodes.dev` DNS and whether `socrat.dathcodes.dev` already serves another application. Preserve existing use until a reviewed change is ready. Once the new host's IP is known, prepare the exact DNS record change and verify resolution before testing Caddy TLS. Do not invent an IP or claim domain verification from the owner's statement alone.

Read-only DNS lookup on 2 October 2026 found a CNAME from `socrat.dathcodes.dev` to `b706b9bea1758db4.vercel-dns-017.com`. This proves an existing Vercel-directed record, not what is hosted or who controls it. No DNS change has been made. Confirm existing use before planning a replacement or an alternative staging hostname.

## Managed sign-in

The application uses managed OpenID Connect authorization-code login. If Google is chosen:

- Create a dedicated Google Cloud OAuth web application for staging after review of its account, audience, privacy, and permitted test users.
- Register exactly `https://socrat.dathcodes.dev/api/v1/auth/callback` as its redirect URI.
- The expected issuer is `https://accounts.google.com`; use discovery metadata and the existing server-side Authlib integration.
- Store the client secret only in the staging secret file; the client ID is a non-secret release input. Do not request Google Drive or other unrelated access for sign-in.
- Exercise actual login, failed callback, expiry, two-user authorization, and local session logout/revocation. Local logout does not sign the user out of their Google account.

Google is selected, but its account/application configuration has not occurred. See [Google's OIDC setup](https://developers.google.com/identity/openid-connect/openid-connect) for credential and exact redirect requirements.

The owner deferred the remaining M1 work and directed M2 repository engineering on 2 October 2026. This does not approve a Terraform plan, replace existing DNS, or pass M1. Return to this checklist before any live deployment.

## Runtime and alert setup

Prepare the five service-scoped secret files through a secure process and authenticate release-image access. Use the exact commit/digests of a successful protected CI run; current local changes must be verified and published before deploying them. Set the runtime hostname to `socrat.dathcodes.dev` and certificate-contact email to the owner's approved address.

The approved email recipient is not a configured delivery route. OCI spending alerts and application-error alerts are separate: configure and test each. The current Prometheus rules have no notification receiver. Select an authenticated route and keep mail/service credentials outside Git. Do not send test messages until the operational drill and route are configured and authorized.

## Finish M1

Follow the [staging runbook](m1-staging-runbook.md) and fill the [evidence record](../delivery/validation/m1-staging-evidence.md) with observed results for identity, PostgreSQL concurrency, encrypted off-host backup/download/restore, deployment, rollback, live telemetry, delivered notifications, and private approvals. M1 remains open until these pass; M0's learner obligations remain pending.
