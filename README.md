# Cloudify — Agentic Cloud Migration

Multi-agent automation that takes full-stack cloud migration from days to under
20 minutes via OpenAI + Anthropic Claude APIs and the Dedalus SDK. Built at
TartanHacks 2026.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Dedalus](https://img.shields.io/badge/powered%20by-Dedalus-purple.svg)

## Why

Migrating a Spring Boot + React app from a laptop to a production cloud target
usually takes a day or more of human work — IaC writing, dependency mapping,
Dockerfile authoring, datasource rewiring, secret rotation, and post-deploy
smoke tests. Cloudify decomposes that work into agent-callable skills and runs
them with deterministic guardrails: each agent owns a narrow phase, publishes
its result on an event bus, and Dedalus routes the underlying step to the
model best suited for it (GPT‑4.1 for code reasoning, Claude Opus for code
generation, GPT‑4.1‑mini for fast deploy actions).

## How it works

```
┌─────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR AGENT                        │
│         (Coordinates all agents via event bus)              │
└────────┬────────────────────────────────────────────────────┘
         │
    ┌────┴─────┬──────────┬──────────────┬──────────────┐
    │          │          │              │              │
┌───▼───┐  ┌──▼───┐  ┌───▼────┐  ┌──────▼─────┐  ┌────▼────┐
│ Code  │  │Infra │  │Database│  │  Backend   │  │Frontend │
│Analyze│─▶│Prov. │─▶│Migrat. │─▶│ Deployment │  │Deploym. │
└───────┘  └──────┘  └────────┘  └────────────┘  └─────────┘
                                         │              │
                                         ▼              ▼
                                   Cloud Run      Firebase
                                                   Hosting
```

- Agent orchestration via the [Dedalus SDK](https://dedaluslabs.ai/)
- OpenAI GPT-4.1 / GPT-4.1-mini and Anthropic Claude Opus 4.6 / Sonnet 4.5
  routed per task by a model-role registry in `agents/base_agent.py`
- Skill registry: code analysis, infrastructure provisioning, database
  migration, backend deployment, frontend deployment
- Event-driven publish/subscribe between agents (loose coupling, parallel
  deploy where safe)
- Deterministic guardrails: dry-run mode, interactive approvals, structured
  Dockerfile + datasource templates rather than free-form generation

### Agents

| Agent | Responsibility |
| --- | --- |
| Code Analyzer | Scans `pom.xml` / `build.gradle` / `application.properties` / React `package.json`. Detects Java + Spring Boot version, build tool, datasource, REST endpoints, CORS config. |
| Infrastructure | Provisions GCP resources via `gcloud`: Cloud Run service, Artifact Registry repo, Firebase project, IAM bindings. |
| Database Migration | Decides between keeping H2 (with warnings) or moving to Cloud SQL (Postgres / MySQL). Rewrites Spring datasource config. |
| Backend Deployment | Generates Dockerfile from template, builds, pushes to Artifact Registry, deploys to Cloud Run with env vars. |
| Frontend Deployment | Detects Vite vs CRA, rewrites the API base URL to the Cloud Run URL, builds, deploys to Firebase Hosting. |

## Supported stack configurations

Cloudify currently targets **Google Cloud Platform** (Cloud Run + Firebase
Hosting + Cloud SQL + Artifact Registry). The agents auto-detect the source
stack — you do not configure it manually. Honestly enumerated permutations:

1. React (Vite) + Spring Boot (Maven) + H2 → Cloud Run + Firebase
2. React (Vite) + Spring Boot (Maven) + Cloud SQL Postgres → Cloud Run + Firebase
3. React (Vite) + Spring Boot (Maven) + Cloud SQL MySQL → Cloud Run + Firebase
4. React (Vite) + Spring Boot (Gradle) + H2 → Cloud Run + Firebase
5. React (Vite) + Spring Boot (Gradle) + Cloud SQL Postgres → Cloud Run + Firebase
6. React (CRA) + Spring Boot (Maven) + H2 → Cloud Run + Firebase
7. React (CRA) + Spring Boot (Maven) + Cloud SQL Postgres → Cloud Run + Firebase
8. React (CRA) + Spring Boot (Gradle) + Cloud SQL MySQL → Cloud Run + Firebase

Java 17 and Java 21 are both detected by the Maven / Gradle scanner.

## Quickstart

```bash
git clone https://github.com/sanathmahesh/cloudify.git
cd cloudify

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in DEDALUS_API_KEY, ANTHROPIC_API_KEY (Claude fallback),
# GCP_PROJECT_ID, GOOGLE_APPLICATION_CREDENTIALS

gcloud auth login
gcloud auth configure-docker us-central1-docker.pkg.dev

python migration_orchestrator.py migrate \
  --source-path /path/to/your/app \
  --gcp-project your-project-id \
  --region us-central1
```

A `migration_config.yaml` template can be generated with
`python migration_orchestrator.py init` if you prefer config-file mode over
CLI flags.

### CLI

```
python migration_orchestrator.py migrate [OPTIONS]

  -s, --source-path PATH      Path to source application directory
  -c, --config PATH           Path to migration configuration file
  -p, --gcp-project TEXT      GCP project ID (overrides config)
  -r, --region TEXT           GCP region (default: us-central1)
  -m, --mode TEXT             Execution mode: interactive or automated
  -d, --dry-run               Preview changes without executing
  -v, --verbose               Enable verbose logging
```

## Demo

A 30-second walk-through of a full migration run lives in the project
submission; recorded captures will be added here.

## Project layout

```
agents/               # Per-phase agents (analyzer, infra, db, backend, frontend)
  base_agent.py       # Event bus, model-role registry, Dedalus integration
  orchestrator.py     # Top-level coordinator
  dedalus_tools.py    # Tool implementations exposed to Dedalus runner
templates/            # Dockerfile + cloudbuild.yaml templates
utils/                # GCP helpers, file ops, logging
tests/                # Unit + integration tests
migration_orchestrator.py   # CLI entry point
migration_config.yaml       # Config template
ARCHITECTURE.md             # Deeper architectural notes
```

## Development

Run unit tests:

```bash
pytest tests/unit -v
```

Run integration tests (require a real GCP project):

```bash
pytest tests/integration -v
```

## Built at TartanHacks 2026

Built by Anmol Sahu, Sanath Mahesh Kumar, Aritra Ray, Manav Somani and Anubhav Sharma

## License

MIT — see [LICENSE](LICENSE).
