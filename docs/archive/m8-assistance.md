# M8 assistance operations

Migrate with `python -m alembic upgrade head` (schema `0008`). Local Compose enables curated tutoring; execution still needs its separate approved configuration. Staging hard-disables model traffic and the shadow advisor. `SOCRAT_TUTOR_ENABLED` controls learner access; `SOCRAT_TUTOR_MODEL_ENABLED=false` preserves curated guidance. `SOCRAT_TUTOR_ADVISOR_SHADOW_ENABLED` controls only the operator shadow endpoint. No switch grants assessment access or permits a model to apply a plan.

## Provider setup after release approval

Choose an explicitly allow-listed model snapshot and review its quality, price and privacy contract. Configure `SOCRAT_TUTOR_PROVIDER=openai_responses`, `SOCRAT_TUTOR_GATEWAY_URL=https://api.openai.com/v1/responses`, `SOCRAT_TUTOR_MODEL`, `SOCRAT_TUTOR_MODEL_ALLOWLIST` (JSON array), and `SOCRAT_TUTOR_GATEWAY_SECRET_FILE`. Do not put credentials in browser configuration, source, learner images or audit events. No credential is supplied by this implementation and no live provider call establishes acceptance.

The Responses adapter uses `text.format` JSON Schema, `tools=[]`, `store=false`, and no conversation identifier. This follows the official [structured-output guide](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses) and [Responses storage guidance](https://developers.openai.com/api/docs/guides/migrate-to-responses). `store=false` is not a claim of zero provider retention; obtain the required data-processing and retention review before enabling traffic.

Alternatively use `structured_gateway` with an operator-controlled HTTPS adapter. Request fields: `model`, immutable `prompt`, `prompt_version`, `prompt_digest`, minimal `context`, output `schema`, `max_output_tokens`. It must return exactly `{output: object, input_tokens: integer, output_tokens: integer}`. It must not execute tools, make state changes or retain learner payloads outside the approved policy. Redirects and environment proxies are disabled.

For the owner's selected Nebius model, use `SOCRAT_TUTOR_PROVIDER=openai_chat`, `SOCRAT_TUTOR_GATEWAY_URL=https://api.tokenfactory.us-north1.nebius.com/v1/chat/completions`, `SOCRAT_TUTOR_MODEL=zai-org/GLM-5.3-Flash`, and `SOCRAT_TUTOR_MODEL_ALLOWLIST=["zai-org/GLM-5.3-Flash"]`. Place the key in private `.env` as `SOCRAT_TUTOR_GATEWAY_SECRET`, or use the secret-file setting exclusively. The public `.env.example` contains these model settings and no credential. The [Nebius API specification](https://api.tokenfactory.nebius.com/docs) exposes chat completions and JSON Schema response formats. The adapter requests one completion, no tools, `store=false`, bounded output, and rejects incomplete, refused, ambiguous or tool-bearing responses. This request flag does not establish provider retention compliance.

Run `.venv/Scripts/python.exe scripts/validation/smoke-m8-model.py` to make one isolated synthetic call even while deployment model flags are off. It reads tutor configuration only, emits metadata without responses or keys, and exits nonzero on provider/policy failure. The default reservation budget is 10,000 microUSD; it is a conservative configuration reservation, not an invoice or provider-enforced spend cap. Up to nine synthetic track/language cells can be requested with `--max-calls 9 --reservation-budget-microusd 90000`; execution stops on the first failed call. `--diagnostic-timeout-seconds 30` tests a slow provider separately; it never changes the application's four-second deadline and explicitly reports whether that deadline was met. Synthetic smoke results never replace the expert evaluation below.

Requests are capped at 60 KB, responses at 32 KB, output at 600 tokens by default, and the whole network exchange at four seconds. Defaults reserve at most twelve model calls per session (per attempt for legacy standalone practice), forty per learner rolling day. Tutor and advisor share the learner-day budget. Idempotent retries reuse committed receipts and do not call the model again. A crash before the transaction commits can leave a billed provider call without a receipt; provider-side project caps are required as a second boundary.

For the selected GLM diagnostic runs, `SOCRAT_TUTOR_REASONING_EFFORT=low` produced complete structured chat output. This optional provider setting is passed as `reasoning_effort` for chat and `reasoning.effort` for Responses. Provider support varies. A small output allowance can be consumed by reasoning before an answer is produced; incomplete responses remain rejected.

Chat adapters also accept optional `SOCRAT_TUTOR_TEMPERATURE` (0–2) and `SOCRAT_TUTOR_TOP_P` (greater than zero, at most one). Unset values are omitted from the request. The owner's working Qwen example uses `https://api.tokenfactory.us-central1.nebius.com/v1/chat/completions`, `Qwen/Qwen3.8-27B`, temperature 0.6 and top-p 0.95, with reasoning effort omitted. A model's availability can differ by regional endpoint: the earlier north-region Qwen 404 does not establish central-region availability.

The private `collect-m8-reviews.py` and `review-m8-proposals.py` runners support `--provider-default-output --diagnostic-timeout-seconds 120` to omit request output-token limits during authorized diagnostics. They retain a 1 MB response envelope, complete-response/schema checks, no retries and checkpointing. These internal runner options are not exposed to learner requests and do not change normal application limits. Without a request token cap, reservation arithmetic cannot bound actual provider cost. Same-model evaluation opinions remain provisional and do not satisfy expert acceptance.

`SOCRAT_TUTOR_CALL_RESERVE_MICROUSD` must be an approved conservative upper bound for the chosen model's maximum input/output cost. `SOCRAT_TUTOR_DAILY_BUDGET_MICROUSD` caps these reservations per learner. Reservations count failed provider attempts and are deliberately not presented as actual invoices. Default numeric values are development candidates, not current vendor prices. The adapter must honor the configured token cap. Set provider account/project spend limits as well.

`SOCRAT_TUTOR_MODEL_ROLLOUT_PERCENT` (0–100) deterministically buckets opaque learner IDs without sending them to the model. It only has effect when model access is enabled. Roll out an evaluated prompt/model pair gradually; no rollout percentage changes authority.

## Owned API and content

`GET/POST /api/v1/attempts/{id}/tutor` require the owned attempt and enabled tutor. Mutations require Origin, CSRF, an idempotency key, `draft_revision`, learner `reasoning`, `requested_level` and `action` (`hint`, `accessibility`, `exit`). Mode and ceilings are derived on the server. Pending Submits reject new hints; completed Submits retain the assistance captured at admission. Reopening a helped family cannot reset assistance.

Optional SkillPack `tutor_hints` entries specify `exercise_id`, `language`, `level` 1–4, `message`, `question`. They can reference practice language variants only and are included in immutable pack review/digest. Empty declarations preserve prior pack digests. Levels 1–3 have generic curated fallbacks; level 4 requires an authored scaffold. Level 5 uses the released practice rubric/reference solution only after its gate. The offline M7 draft is not implicitly promoted or reviewed.

Full explanations/scaffolds mark work learning-only and record a fresh-task obligation. Plan refresh excludes the entire exposed family, retaining normal prerequisite/runtime/workload filters. If inventory has no eligible replacement, the normal planner reports no safe candidate; the service never invents or mislabels an unseen exercise. The code workspace links this obligation to the existing plan-refresh workflow.

Private artifacts retain the bounded input context, learner reasoning and served response; general audit/metrics contain identifiers and derived metadata only. Redaction covers common emails/credential patterns, not arbitrary personal information. Provider data minimization and human review remain necessary. The artifact table is separable for M10 retention/export/deletion; immutable receipts retain hashes and policy/evidence facts. Removing an artifact makes its history response unavailable without restoring independent status.

## Monitoring and shadow evaluation

`GET /api/v1/admin/tutor/monitor` uses the existing content-admin identity allow-list and shows the rolling day's fallback/rejection counts, review references, budget/latency alerts and shadow disagreement counts. Repeated provider/validation failures also produce durable `tutor.review_required` audit/outbox events. Use the existing operational event consumer to create/resolve support tickets; do not send transcripts to general analytics. Review events remain in the durable log even after they leave the rolling report.

Private `/api/metrics` exports `socrat_tutor_budget_exhaustions` for the last fifteen minutes and `socrat_tutor_reserved_microusd` for the last day. Prometheus rules alert on budget exhaustion and tutor p95 >5 seconds. Slow model routes are excluded from the ordinary application-latency rule. On latency, leakage or correctness incidents disable model access first; curated hints remain. Roll back `SOCRAT_TUTOR_PROMPT_VERSION` from `tutor_1.0.1` to `tutor_1.0.0` and redeploy/restart. Historical receipts keep their original hashes and versions. Turn off the tutor entirely if curated content is unsafe and quarantine the pack using existing editorial controls.

`POST /api/v1/admin/goals/{id}/advisor-shadow` requires admin+CSRF, `expected_revision` and an idempotency key. Its server-generated envelope contains 3–8 eligible practice candidates from the first planned day. The response records baseline/proposal, input digest, policy, prompt/model, latency/tokens/reservation and whether the ordering differs. It never modifies a revision or produces learner evidence. The curriculum ID links comparisons to later evidence for approved analysis. A sparse envelope returns `shadow_envelope_unavailable`.

## Expert evaluation

Keep populated records outside the repository in access-controlled storage. Each case uses opaque case/reviewer references and derived judgments; no code or transcripts belong in the exported report.

```powershell
python scripts/validation/export-m8-contracts.py
python scripts/validation/evaluate-m8.py PRIVATE_RECORD.json
python -m pytest services/api/tests/test_tutor.py services/api/tests/test_tutor_postgres.py
```

The versioned [evaluation schema](../../contracts/schemas/m8-evaluation.schema.json) requires prompt/model/content pins and a sampling-plan reference. The checker requires at least 500 cases across all nine cells and at least the configured 25-or-higher cases per cell; reviewers must approve the actual sample size and representativeness. Per-cell material error and premature solution rates must be strictly below 3%, assessment access must be absent, and p95 latency below five seconds. Usefulness is reported for review. Only genuine expert-reviewed records can support the gate; test fixtures never do. The report always sets `release_approved=false`.

Owner follow-up, 6 October 2026: reviewer assignments, private draft queue, regional endpoint test and deployment deferrals are recorded in [M7/M8 completion coordination](m7-m8-completion.md). The isolated smoke runner accepts `--gateway-url` for an explicit HTTPS override and `NEBIUS_API_KEY` as a fallback credential when neither Socrat secret setting is provided. These options do not enable deployed model traffic.
