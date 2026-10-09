# M11 release gate

Status: automated local validation passed; human testing deferred and hosted acceptance pending. M11 is not closed by passing local tests.

| Requirement | Automated evidence | Remaining acceptance |
|---|---|---|
| At least 200 complete synthetic journeys | Fresh-database API lifecycle suite across nine track/language cells | Deployed representative journeys with actual content, identity and runner integrations |
| At least 30 human journeys | No human results recorded | Deferred by owner; staff/invited alpha still required |
| Zero Sev1/2 issues | Record failures and fixes in automated validation | Review observed incidents and open defects; test success alone cannot attest zero severe production issues |
| Healthy error budgets for seven days | Local concurrent-read measurements and monitoring contracts | Seven days of deployed SLO/error-budget evidence |
| Restore game day | SQLite saved-session/evidence restore and existing erasure replay | Hosted PostgreSQL backup restore, recovery time/data-loss measurement, erasure reconciliation |
| Queue outage game day | Worker transaction fault/retry and broker/concurrent delivery checks | Hosted worker interruption and durable queue backlog/recovery |
| Model outage game day | Existing timeout, rejection, budget and fallback tests | Deployed model-provider outage, alerting and operator response |
| Runner compromise game day | Existing signature/nonce/tamper rejection and startup failure tests | Attested dedicated gVisor security, containment and key-rotation rehearsal |
| Rollback game day | Existing release-controller failed deploy/rollback tests | Actual deployment rollback and service recovery |
| Admin replay/quarantine and support | Existing content/learner replay and quarantine regression | Operator acceptance, incident response and support workflow rehearsal |
| Inherited prerequisites | M0–M10 retain recorded gates | Accessibility, content, privacy/provider and runtime gates remain open as previously documented |

Human testing being deferred does not waive its exit criterion or the hosted operational evidence required before M12 beta.
