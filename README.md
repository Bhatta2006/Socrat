# Socrat

Socrat is a deterministic-first personalized learning platform. V1 delivers Data Structures and Algorithms preparation for complete beginners, interview learners, and competitive programmers in Python, C++, and Java. The core platform is designed to support additional skill packs after V1 without rewriting learner state, planning, assessment, or analytics.

## Repository status

M0 product validation remains in progress. The product owner closed M1 on 2026-09-30 and authorized M2 work, deferring the server-dependent staging and operational checks recorded in the [M1 gate](docs/delivery/milestones/m1-gate.md). The repository-side M1 foundation and hosted quality gates are implemented; deferred checks are not claimed as verified.

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
│   ├── content/               # Draft skill-pack fixtures and schema generator
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

## Validate the M2 kernel

From the repository root, with the locked Python environment installed:

```powershell
.\.venv\Scripts\python.exe -m pytest services/api/tests/test_skill_packs.py -q
.\.venv\Scripts\python.exe -m ruff check services/api/src services/api/tests scripts/content/build_sample_packs.py
.\.venv\Scripts\python.exe -m mypy services/api/src
```

The [M2 content operator guide](docs/operations/m2-content-admin.md) describes the role-gated import, review, publish, and quarantine workflow. The checked-in sample packs are draft fixtures, not launch content.
