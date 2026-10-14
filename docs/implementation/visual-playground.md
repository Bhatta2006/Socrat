# AI visual playground

The playground generates a self-contained HTML/CSS/JavaScript learning app from the learner's
request and embeds it inside `/playground`. There is no concept allowlist, preset lesson, supplied
sample input, algorithm dispatcher, or model-generated numeric snapshot schema. The learner's
request, language preference and explanation depth are the only generation inputs. The model
chooses the visual, controls and initial example, and computes interactive state in its generated
JavaScript. It can explain concepts outside the enrolled course without exposing course resources.

This implements the implementation guide's free-form sandbox path, following the user's explicit
request for AI-generated visuals for any concept. The guide's deterministic template launch wedge
is not the default experience. Generated material is labelled as not verified for factual accuracy.

## Pipeline

1. The server checks session, CSRF, active enrollment, independent-work/assessment restrictions,
   quotas, one outstanding generation per learner, and the request's idempotency identity.
2. The configured assistant provider generates a complete document. SSE reports generation,
   browser checking and repairs; partial HTML is never sent to the canvas.
3. Python validates bounded, balanced markup. External resources, navigation, nested browsing
   contexts, forms, inline handlers and model-supplied script nonces are rejected.
4. A separate Node/Playwright checker parses every model script with Acorn, rejects forbidden
   capabilities and known unbounded loops, then opens the document in a fresh opaque-origin
   browser frame with no session or credentials. It checks a nonblank canvas, labelled controls,
   state descriptions, initial/intermediate/final steps, input interaction and reset. Up to three
   repair attempts receive the actual validation failure. A separate AI review reads the learner's
   exact request, generated source and bounded rendered-state observations for wrong subjects, contradictions, incorrect computations,
   fake interactions and missing visual labels. Material findings use the same bounded repair loop;
   no prescribed examples or subject-specific answers are supplied to either model call.
5. Accepted source and metadata are saved privately in the existing assistant-message store.
   The browser receives metadata and a signed, expiring frame URL, not HTML inserted into React.
6. The canvas uses `sandbox="allow-scripts"`, without `allow-same-origin`, and a response CSP with
   script nonces, no network/resource loading, no forms, no nested frames and no dynamic evaluation.
   An intersecting inline-only script policy blocks external scripts even if generated code copies
   its own nonce; DNS prefetching is disabled on frame responses.
   Header-level sandboxing also applies if somebody opens the frame URL directly.
7. A small trusted bridge accepts only bounded state/heartbeat messages from the exact frame,
   opaque origin and artifact identity. The parent sends only theme tokens and timeline commands.
   It never sends a session token, API key, learner profile or problem data. An unresponsive frame
   is removed. Theme updates, reduced motion, playback, timeline scrubbing, reset and expanded view
   stay inside the dashboard UI. The generated interface reports `currentStep` so experiment
   changes keep the outer timeline synchronized with the actual visual state.

Static checks are an additional filter, not proof that arbitrary JavaScript is safe. The isolation
boundary is the sandbox plus CSP and separate production domain. Browser checks establish working
interaction, not mathematical or pedagogical correctness. Reporting quarantines that saved visual
and stores the feedback. Viewing and interacting never alter mastery or complete course lessons.

## Local development

The native demo uses the already-installed Node runtime and Edge/Playwright for render checking.
Checker subprocesses receive a minimal environment without provider keys or database credentials.
The frame is served from `http://127.0.0.1:8000`, while the dashboard uses `http://localhost:3000`.
Use `SOCRAT_EXPLAINER_BROWSER_CHANNEL` to select another installed Playwright browser if needed.
There is no second API key: generation uses the configured assistant provider, including Nebius.
`SOCRAT_EXPLAINER_MODEL` can select a model without changing the main tutor model. The verified
local configuration uses `Qwen/Qwen3.8-27B` with `SOCRAT_EXPLAINER_CHAT_TEMPLATE_KWARGS={"enable_thinking":false}`.
These optional OpenAI-compatible provider controls apply only to the playground; leave the map
empty for providers that do not support them. The main tutor retains its existing model and controls.

## Production deployment

Set `SOCRAT_EXPLAINER_SANDBOX_ORIGIN` to an HTTPS origin on a separate registrable domain from the
dashboard. Route only `/api/v1/playground/artifacts/*/frame` on that host to the API, preserving Host
and protocol. Do not expose dashboard/auth routes on the sandbox domain. Tokens expire after an
hour; authenticated history/detail requests issue fresh links, and frame loads recheck ownership,
quarantine and independent-work policy.
Omit query strings from sandbox access logs because frame URLs contain short-lived capability tokens.
The API image and native launcher disable Uvicorn's raw access log; the application retains its
structured request records with route templates, status and request identity.

Build the web image with `NEXT_PUBLIC_EXPLAINER_SANDBOX_ORIGIN` set to that same public origin;
the build uses it for the `frame-src` CSP. Run `services/explainer/Dockerfile` as a dedicated browser
checker with CPU/memory limits, no API/database credentials, and an unprivileged Chromium sandbox.
The container host must support Chromium's unprivileged sandbox; do not disable it to bypass a host
configuration failure. Use an internal checker URL and a strong shared checker secret, configured
as `SOCRAT_EXPLAINER_CHECKER_URL` and `SOCRAT_EXPLAINER_CHECKER_SECRET` on the API and checker.
The local Compose file includes the checker with development-only credentials.

Production generation fails closed if the separate sandbox or checker is missing. The global
`SOCRAT_EXPLAINER_ENABLED` switch disables generation and frame loading. Generation has a total
300-second deadline including AI review and repairs; browser checks have an 18-second process budget, and malformed output is
bounded to 300 KB. Failed generations preserve the learner's request and never substitute content.
The default visual quota is 20 generations per learner per day, in addition to the shared assistant
quota, with one pending request per learner and four simultaneous generations per API process.

## Checks

- `python -m pytest services/api/tests/test_explainer.py`: markup/security boundaries, real browser
  preflight, exact request forwarding, repair, persistence, ownership, idempotency, mode and quota.
- `node --test scripts/explainer/check-artifact.test.mjs`: nested script capability restrictions.
- `playwright test tests/e2e/learning-scope.spec.ts`: embedded interaction, input edits, timeline,
  iframe isolation, dashboard themes, reduced motion, accessibility, error recovery and reporting.

These are the requested playground implementation checks; learner-submission debugging, reviewed
deterministic templates, template promotion, and learning-effectiveness experiments are separate
features from the guide's phased roadmap.
