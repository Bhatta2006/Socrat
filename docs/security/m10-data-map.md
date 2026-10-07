# M10 learning data and erasure map

| Data | Storage | Export | Erasure / retention |
|---|---|---|---|
| Identity/profile | users, login_sessions | Own identity identifiers and profile fields; never session/CSRF secrets or OIDC credentials | Revoke sessions at request; remove identity/profile at worker erasure |
| Goals/plans | learner_goals, curriculum_* and planning_commands | Public goal, schedule, feasibility and milestones | Owned rows and dependent commands removed |
| Sessions | learning_sessions, session_commands | Owned local-day/status history, saved answers and reflections | Owned rows/commands removed; participation never changes mastery |
| Code | code_attempts, code_drafts, code_runs, code_run_sources, submit_assistance | Learner code and safe run metadata; no private execution manifest/tests/signatures | Owned graph removed; raw drafts and terminal run sources expire after 365 days. Active job sources remain until termination |
| Tutor/advisor | tutor_turns, tutor_artifacts, advisor_shadows | Learner reasoning and tutor response; no provider secrets/context envelopes | Owned graph removed; raw tutor artifacts expire after 365 days |
| Diagnostics | diagnostic_sessions/attempts/responses/answers | Owned answers and result summary; no private scoring keys | Owned graph removed |
| Assessments | assessment_sessions/items/responses/answers/reviews/disputes/deferrals | Owned answers, result summary, disputes and deferrals; no form/rubric answer keys or reviewer identity | Owned graph removed, including another operator's review of this learner's answers |
| Evidence | learning_evidence, learner_states, mastery_events, learning_policy_reviews | Owned scoring/projection facts | Immutable during normal operation; DELETE allowed only when an erasing request resolves to the same learner inside the transaction |
| Reminders/preferences | user_preferences, reminders | Consent, quiet hours and safe reminder history | Owned rows removed; consent revocation closes outstanding inbox entries |
| Audit/outbox | audit_events, outbox_events, delivered_events | Own audit kind/time only | Owned audit and outbox messages referencing erased resources removed, including delivered inbox acknowledgements |
| Published editorial lineage | skill_pack_versions, content_reviews and reviews/policy operations on another learner | Not part of learner export | Shared content preserved. Referencing author/reviewer shell has identity and profile cleared; separate editorial privacy review required before receipt completion |
| Erasure receipt/context | privacy_requests | Private receipt token returned once; bearer-protected status | No learner ID in public receipt. Restricted cleanup context contains opaque IDs and review window only; removed after all cleanup receipts |
| Backups/replicas/host logs | Deployment-owned stores | Private operator workflow | Never assumed deleted by database cleanup. Operator purges/expires stores, reapplies a private erasure manifest on restore and records evidence |
| Model/provider stores | Approved gateway/provider | Contract-specific operator workflow | Existing adapters request no storage where supported; this does not certify provider log deletion. Operator confirms provider/region/retention terms and deletion capability |

The repository has no learner object-store implementation, email address store or push subscription store. Any deployment adding these must extend this map, export, erasure and restore checks before release. No raw provider payload, learner code, receipt token or private manifest belongs in analytics, metrics, public documentation or version control. Separate consent is required before general-model training on learner content.
