# Socrat

Socrat is a deterministic-first personalized learning platform. V1 delivers Data Structures and Algorithms preparation for complete beginners, interview learners, and competitive programmers in Python, C++, and Java. The core platform is designed to support additional skill packs after V1 without rewriting learner state, planning, assessment, or analytics.

## Repository status

M0 product validation remains in progress. The product owner authorized a scoped M1 engineering start while retaining the unpassed learner-pilot and human sign-off gates. The repository-side M1 foundation and hosted quality gates are implemented; cloud staging and operational proof remain pending in the [M1 gate](docs/delivery/milestones/m1-gate.md).

On 2 October 2026, the owner chose Google sign-in and deferred the remaining M1 operational work to proceed with [M2 skill-pack engineering](docs/delivery/milestones/m2-index.md). The kernel includes declarative schemas, graph validation, immutable versioning, editorial review/release/quarantine APIs, and DSA/non-DSA fixtures. M0, M1, and the M2 staging/human gates remain unpassed.

M3 onboarding and deterministic routing is implemented locally: reviewed goals, explicit target/language coverage, beginner bridges, version-pinned confirmation, and atomic funnel events. See the [M3 index](docs/delivery/milestones/m3-index.md) and [gate](docs/delivery/milestones/m3-gate.md). Onboarding is enabled in local Compose and defaults off in staging. No real launch content or completed hosted/staging M3 gate is claimed.

M4 adds resumable objective diagnostics, append-only evidence, deterministic learner-state projections, retention/misconception rules, and protected replay/correction/policy/calibration operations. Diagnostics are enabled in local Compose and default off in staging. Implementation-based placement awaits M6; live content and operational/human approvals remain in the [M4 gate](docs/delivery/milestones/m4-gate.md). See the [operations guide](docs/operations/m4-diagnostics.md).

M5 implements the deterministic curriculum and fourteen-day planner, with prerequisite-safe practice selection, immutable decisions/replay, confirmation, feasibility, workload controls, and missed-day recovery. Local Compose enables planning; staging defaults off. Code practice awaits M6 and full learning sessions await M7. See the [M5 index](docs/delivery/milestones/m5-index.md), [gate](docs/delivery/milestones/m5-gate.md), and [operations guide](docs/operations/m5-planning.md).

M6 adds self-hosted Monaco, autosave/resume, a durable signed execution broker, quotas, and separate gVisor-only Python/C++20/Java21 workers. Verified Submit results feed learning evidence and diagnostics; Run never changes mastery. Execution stays disabled until attested runtime images, dedicated-host security/load tests, and external review pass. See the [M6 index](docs/delivery/milestones/m6-index.md), [gate](docs/delivery/milestones/m6-gate.md), and [operations guide](docs/operations/m6-execution.md).

M7 implementation includes durable Today sessions, pinned language/track lessons, private objective checks, mixed Competitive timed/upsolve practice, configurable practice penalties, reviewed structural-repair mappings, saved history/local-day expiry, and owned participation/duration exports. A nine-cell content audit gates publication of packs declaring session content. Actual independently reviewed launch content, calibration, and deployed acceptance remain pending. Local Compose enables sessions; staging defaults off. See the [M7 implementation status](docs/delivery/milestones/m7-index.md) and [gate](docs/delivery/milestones/m7-gate.md). Deferred M6 gVisor tests remain open.

## Repository map

```text
Socrat/
├── contracts/                 # Machine-readable product and interface contracts
│   ├── product/
│   └── schemas/
├── docs/
│   ├── architecture/          # System decisions, ADRs, dependency evaluation
│   ├── delivery/              # Milestone gates and execution status
│   ├── product/               # PRD, language, goals, policies, metrics, content rules
│   ├── research/              # User-research protocols and evidence
│   └── security/              # Threat models and security/privacy design
├── prototypes/
│   └── concierge/             # Disposable M0 learner-research prototype
├── apps/web/                  # Next.js learner-facing web application
├── services/api/              # FastAPI modular monolith and worker
├── tests/e2e/                 # Desktop/mobile browser acceptance journeys
├── infra/oci/                 # Validated OCI Hyderabad staging infrastructure
├── .github/                   # CI and dependency-maintenance policy
├── scripts/
│   ├── operations/            # Backup and restore smoke tooling
│   └── validation/            # Deterministic repository/contract checks
├── compose.yaml               # Reproducible local PostgreSQL topology
└── README.md
```

Future learning capabilities remain disabled until their milestone contracts and tests exist.

## Start here

1. [Documentation index](docs/README.md)
2. [V1 product requirements](docs/product/v1-product-requirements.md)
3. [M0 milestone index](docs/delivery/milestones/m0-index.md)
4. [M0 gate](docs/delivery/milestones/m0-gate.md)
5. [M1 platform foundation](docs/delivery/milestones/m1-index.md)
6. [M2 skill-pack kernel](docs/delivery/milestones/m2-index.md)
7. [M3 onboarding and routing](docs/delivery/milestones/m3-index.md)
8. [M4 diagnostic and learner-state implementation plan](docs/delivery/milestones/m4-index.md)

## Run the M1 foundation

With Docker available:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open `http://localhost:3000`. The local login exists only in development/test. Staging and production settings fail closed unless HTTPS, PostgreSQL, managed OIDC, strong session/metrics secrets, and disabled developer login are configured.

## Validate M0

From the repository root:

```powershell
node --test prototypes/concierge/model.test.mjs
powershell -ExecutionPolicy Bypass -File scripts/validation/test-m0-contracts.ps1
```

Passing automated checks confirms document/contract consistency only. It does not substitute for learner pilots or accountable human sign-off.
