# Cloudify Architecture

## System Overview

Cloudify is an AI-powered cloud migration system that automates the deployment of Spring Boot + React applications to Google Cloud Platform. It uses the **Dedalus SDK** for multi-model handoffs and tool calling, routing each migration phase to the optimal AI model.

The system has three interfaces:
1. **CLI** (`migration_orchestrator.py`) — Primary Typer-based CLI for running migrations
2. **Web Console** (`web_ui/` + `web_backend/`) — React + FastAPI web interface with real-time log streaming
3. **Marketing Site** (`frontend/`) — Next.js 16 landing page

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACES                                  │
│                                                                          │
│   ┌─────────────┐    ┌──────────────────────┐    ┌────────────────────┐ │
│   │  CLI (Typer) │    │ Web Console (React)  │    │ Marketing (Next.js)│ │
│   │              │    │  + FastAPI Backend    │    │  Landing Page      │ │
│   └──────┬───────┘    └──────────┬───────────┘    └────────────────────┘ │
│          │                       │                                       │
└──────────┼───────────────────────┼───────────────────────────────────────┘
           │                       │
           ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                                    │
│              (Dedalus SDK Multi-Model Coordinator)                      │
│                                                                         │
│  • Manages agent execution order & dependencies                        │
│  • Routes each phase to optimal AI model                               │
│  • Wraps specialist agents as Dedalus tools (agent-as-tool pattern)    │
│  • Aggregates results & generates AI-powered summary                   │
└────────┬────────────────────────────────────────────────────────────────┘
         │
         │ Event Bus (Pub/Sub)
         │
    ┌────┴─────┬──────────┬──────────────┬──────────────┐
    │          │          │              │              │
┌───▼───┐  ┌──▼───┐  ┌───▼────┐  ┌──────▼─────┐  ┌────▼────┐
│ Code  │  │Infra │  │Database│  │  Backend   │  │Frontend │
│Analyze│─▶│Prov. │─▶│Migrat. │─▶│ Deployment │  │Deploym. │
│       │  │      │  │        │  │            │  │         │
│GPT-4.1│  │Sonnet│  │Multi-  │  │Claude Opus │  │GPT-4.1  │
│       │  │ 4.5  │  │Model   │  │   4.6      │  │  mini   │
└───────┘  └──┬───┘  └────────┘  └─────┬──────┘  └────┬────┘
              │                         │              │
              ▼                         ▼              ▼
       ┌─────────────┐         ┌──────────────┐  ┌──────────┐
       │ GCP Setup   │         │  Cloud Run   │  │ Firebase │
       │             │         │              │  │ Hosting  │
       │ • Artifact  │         │ • Docker     │  │          │
       │   Registry  │         │   Build      │  │ • React  │
       │ • IAM       │         │ • Deploy     │  │   Build  │
       │ • APIs      │         │ • Configure  │  │ • Deploy │
       └─────────────┘         └──────────────┘  └──────────┘
```

## Dedalus SDK Integration

### Multi-Model Routing

Each migration phase is routed to the optimal AI model via the Dedalus SDK's `DedalusRunner`:

```python
class ModelRole(Enum):
    REASONING      = "openai/gpt-4.1"                    # Deep analysis & reasoning
    CODE_GENERATION = "anthropic/claude-opus-4-6"         # Code generation (Dockerfile, configs)
    PLANNING       = "anthropic/claude-sonnet-4-5-20250514"  # Planning & creative tasks
    FAST           = "openai/gpt-4.1-mini"                # Fast, simple tasks
    MULTI_MODEL    = ["openai/gpt-4.1", "anthropic/claude-opus-4-6"]  # Dedalus routes between models
```

| Phase | Model | Rationale |
|-------|-------|-----------|
| Code Analysis | GPT-4.1 (REASONING) | Deep analysis of pom.xml, Spring configs |
| Infrastructure | Claude Sonnet 4.5 (PLANNING) | GCP resource planning |
| Database Migration | MULTI_MODEL (GPT-4.1 + Claude Opus) | Analysis + recommendations |
| Backend Deployment | Claude Opus 4.6 (CODE_GENERATION) | Dockerfile generation |
| Frontend Deployment | GPT-4.1-mini (FAST) | Simple build & deploy |
| AI Summary | GPT-4.1-mini (FAST) | Quick post-migration summary |
| Error Recovery | Policy-based escalation | FAST → REASONING escalation |

### Tool Calling System

All GCP operations, code analysis, and deployment functions are defined in `agents/dedalus_tools.py` as typed async Python functions with docstrings. The Dedalus SDK auto-extracts schemas and lets models invoke them during agentic loops.

#### Tool Registry (21 tools across 5 categories)

**Analysis Tools:**
| Tool | Description |
|------|-------------|
| `scan_maven_pom()` | Parse pom.xml for Java version, Spring Boot version, dependencies |
| `scan_gradle_build()` | Parse build.gradle for Java version and dependencies |
| `analyze_spring_properties()` | Extract database and server config from application.properties/yml |
| `detect_database_type()` | Detect DB type and mode from JDBC URL |
| `extract_api_endpoints()` | Find REST controllers and endpoint mappings |
| `analyze_react_app()` | Scan package.json, build tool, dependencies, API endpoints |

**Infrastructure Tools:**
| Tool | Description |
|------|-------------|
| `check_gcloud_auth()` | Verify gcloud CLI installation and authentication |
| `enable_gcp_apis()` | Enable Cloud Run, Artifact Registry, Cloud Build, Firebase APIs |
| `create_artifact_registry()` | Create Docker Artifact Registry repository |
| `setup_firebase_project()` | Verify Firebase CLI and project accessibility |
| `configure_iam_permissions()` | Set up Cloud Build IAM roles for Cloud Run deployment |

**Database Tools:**
| Tool | Description |
|------|-------------|
| `create_cloud_sql_instance()` | Create Cloud SQL instance and database |
| `detect_database_type()` | Detect H2/MySQL/PostgreSQL from JDBC URL |

**Backend Deployment Tools:**
| Tool | Description |
|------|-------------|
| `write_dockerfile()` | Write AI-generated Dockerfile (with LLM output cleaning) |
| `build_docker_image()` | Build Docker image for linux/amd64 |
| `push_docker_image()` | Authenticate with Artifact Registry and push image |
| `deploy_to_cloud_run()` | Deploy container to Cloud Run with full configuration |
| `update_cors_origins()` | Update CORS config in Java source to include frontend URL |

**Frontend Deployment Tools:**
| Tool | Description |
|------|-------------|
| `configure_frontend_env()` | Create .env.production with backend API URL |
| `install_npm_dependencies()` | Run npm ci or npm install |
| `build_frontend()` | Build React production bundle |
| `deploy_to_firebase()` | Initialize Firebase config and deploy to Hosting |

### MCP Integration

The system connects to MCP servers via the Dedalus SDK for research and error recovery:

```yaml
mcp_servers:
  - "windsor/brave-search-mcp"  # Research best practices & debug errors
```

### Agent-as-Tool Pattern

The orchestrator wraps each specialist agent as a Dedalus-callable tool, enabling the orchestrator LLM to dynamically delegate work:

```python
# Each agent becomes a tool: run_codeanalyzer_agent, run_infrastructure_agent, etc.
specialist_tools = self._build_specialist_tools(agents)
```

## Event-Driven Communication

```
                    ┌─────────────────┐
                    │   EVENT BUS     │
                    │  (Pub/Sub)      │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼────┐         ┌────▼────┐        ┌────▼────┐
    │Publisher│         │Publisher│        │Subscriber│
    │ Agent A │         │ Agent B │        │ Agent C  │
    └─────────┘         └─────────┘        └──────────┘
         │                   │                   │
         │ publish()         │ publish()         │ on_event()
         ▼                   ▼                   ▼
    EVENT_TYPE_1       EVENT_TYPE_2         Handles event
```

### Event Types

| Event | Description |
|-------|-------------|
| `AGENT_STARTED` | Agent begins execution |
| `AGENT_COMPLETED` | Agent finished successfully (includes models_used, tools_called) |
| `AGENT_FAILED` | Agent encountered error |
| `ANALYSIS_COMPLETE` | Code analysis finished |
| `INFRASTRUCTURE_READY` | GCP resources provisioned |
| `DATABASE_MIGRATED` | Database setup complete |
| `BACKEND_DEPLOYED` | Backend deployed to Cloud Run |
| `FRONTEND_DEPLOYED` | Frontend deployed to Firebase |
| `MIGRATION_COMPLETE` | Entire migration successful |
| `ERROR_OCCURRED` | Error during migration |
| `PROGRESS_UPDATE` | Progress percentage update |
| `MODEL_HANDOFF` | AI model switch during execution (for demo visibility) |
| `TOOL_INVOKED` | Tool function called by an agent (for real-time dashboard) |

## Agent Lifecycle

```
┌──────────┐
│  IDLE    │
└────┬─────┘
     │ execute()
     ▼
┌──────────┐
│ RUNNING  │──────┐
└────┬─────┘      │
     │            │ on_error()
     │ success    │
     ▼            ▼
┌──────────┐  ┌──────────┐
│ SUCCESS  │  │  FAILED  │
└──────────┘  └──────────┘
```

All agents extend `BaseAgent` which provides:
- Event bus integration (publish/subscribe)
- Dedalus SDK client (`AsyncDedalus`) and runner (`DedalusRunner`)
- `run_with_dedalus()` method for multi-model handoffs, tool calling, MCP, and policy routing
- `_invoke_tool()` for tracked tool invocations with TOOL_INVOKED events
- Model and tool usage tracking (`_models_used`, `_tools_called`)
- State management (`update_state()`, `get_state()`)

## Data Flow

### 1. Code Analysis Phase

```
Source Code
    │
    ├─► Spring Boot Files
    │   ├─► pom.xml / build.gradle     → scan_maven_pom() / scan_gradle_build()
    │   ├─► application.properties     → analyze_spring_properties()
    │   └─► Controller classes         → extract_api_endpoints()
    │
    └─► React Files
        ├─► package.json               → analyze_react_app()
        ├─► API configurations
        └─► Build settings
            │
            ▼
    ┌───────────────────┐
    │ Analysis Results  │
    │                   │
    │ • Java version    │
    │ • Dependencies    │
    │ • DB config       │
    │ • API endpoints   │
    │ • Build tools     │
    └─────────┬─────────┘
              │
              ▼
      [Event: ANALYSIS_COMPLETE]
```

### 2. Infrastructure Phase

```
GCP Project
    │
    ├─► check_gcloud_auth()
    │
    ├─► enable_gcp_apis()
    │   ├─► Cloud Run API
    │   ├─► Artifact Registry API
    │   ├─► Cloud Build API
    │   └─► Firebase API
    │
    ├─► create_artifact_registry()
    │
    ├─► configure_iam_permissions()
    │
    └─► setup_firebase_project()
        │
        ▼
    [Event: INFRASTRUCTURE_READY]
```

### 3. Backend Deployment Phase

```
Spring Boot App
    │
    ├─► Generate Dockerfile (via Claude Opus 4.6)
    │   └─► write_dockerfile() with LLM output cleaning
    │       ├─► Strips markdown fences
    │       └─► Extracts valid Dockerfile instructions
    │
    ├─► build_docker_image() — linux/amd64
    │
    ├─► push_docker_image() — to Artifact Registry
    │
    ├─► deploy_to_cloud_run()
    │   ├─► Set memory/CPU
    │   ├─► Set env vars
    │   └─► Configure scaling
    │
    └─► update_cors_origins() — add frontend URL
        │
        ▼
    [Event: BACKEND_DEPLOYED]
    └─► Service URL
```

### 4. Frontend Deployment Phase

```
React App
    │
    ├─► configure_frontend_env()
    │   └─► .env.production with VITE_API_URL={backend_url}
    │
    ├─► install_npm_dependencies()
    │   └─► npm ci (or npm install fallback)
    │
    ├─► build_frontend()
    │   └─► npm run build → dist/ or build/
    │
    └─► deploy_to_firebase()
        ├─► Generate firebase.json + .firebaserc
        ├─► Create hosting site
        └─► firebase deploy --only hosting
            │
            ▼
        [Event: FRONTEND_DEPLOYED]
        └─► Hosting URL
```

## CLI Interface

The CLI is built with **Typer** and provides three commands:

```bash
# Run a migration
python migration_orchestrator.py migrate [OPTIONS]

# Initialize a new migration config
python migration_orchestrator.py init

# Show version info
python migration_orchestrator.py version
```

### CLI Options (`migrate`)

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--source-path` | `-s` | `../BasicApp` | Path to source application directory |
| `--config` | `-c` | `./migration_config.yaml` | Path to configuration file |
| `--gcp-project` | `-p` | (from config) | GCP project ID (overrides config) |
| `--region` | `-r` | `us-central1` | GCP region |
| `--mode` | `-m` | `interactive` | Execution mode: interactive or automated |
| `--dry-run` | `-d` | `false` | Preview changes without executing |
| `--verbose` | `-v` | `false` | Enable verbose (DEBUG) logging |

### CLI Features
- ASCII banner with Dedalus branding
- Rich progress bars with per-agent tracking
- Real-time model handoff and tool invocation display
- Prerequisites check (Dedalus/Anthropic API key, gcloud, Docker, Firebase CLI)
- Configuration validation
- Interactive confirmation prompt
- Post-migration summary table with models used per phase
- Dedalus SDK usage summary (total model handoffs, total tool calls)

## Web Console

### Web Backend (`web_backend/app.py`)

FastAPI application that wraps the CLI orchestrator as a subprocess, providing a REST API for the web console.

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/migrations` | Start a new migration (spawns subprocess) |
| `GET` | `/api/migrations/{id}` | Get migration status (running, returncode) |
| `POST` | `/api/migrations/{id}/cancel` | Cancel a running migration (SIGTERM) |
| `GET` | `/api/migrations/{id}/stream` | Server-Sent Events log stream |

**Key Implementation Details:**
- Spawns `migration_orchestrator.py migrate` as an async subprocess
- Captures both stdout and stderr streams
- Maintains a log buffer (max 2,000 lines) per migration via `deque`
- Uses `asyncio.Queue` for real-time SSE streaming
- Parses and normalizes user-provided CLI args (handles backslash continuations)
- CORS enabled for all origins
- Graceful cancellation via SIGTERM signal

**Data Models:**
```python
class MigrationRequest(BaseModel):
    args: str  # CLI arguments to pass to migrate command

@dataclass
class MigrationProcess:
    process: Optional[asyncio.subprocess.Process]
    logs: Deque[str]       # Bounded buffer (maxlen=2000)
    queue: asyncio.Queue   # SSE streaming queue
    returncode: Optional[int]
```

### Web UI (`web_ui/` — React + Vite)

Single-page React application that provides a graphical interface for running migrations.

**Features:**
- Migration request form with pre-populated sample args
- Real-time SSE log streaming with auto-scroll
- Agent progress tracker (5 agents with status indicators)
- Progress bar (completed agents / total agents)
- Start / Cancel migration controls
- Status pill (idle, starting, running, completed, cancelled, error)
- Log parsing for agent lifecycle events (started, completed, failed)

**Agent Status Parsing:**
The web UI parses stderr log lines to track agent progress:
```javascript
const RE_STARTED   = /Agent\.(\w+)\s+-\s+INFO\s+-\s+Starting\s+/;
const RE_COMPLETED = /Completed\s+(\w+)\s+-\s+Status:\s+(\w+)\s+\(([0-9.]+)s\)/;
```

**Environment:**
```bash
VITE_API_BASE_URL=http://localhost:8000  # FastAPI backend URL
```

## Marketing Site (`frontend/` — Next.js 16)

A single-page marketing landing site built with Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, and Framer Motion.

**Pages:**
- `/` — Home page (`app/page.tsx`)

**Components (16):**

| Component | Description |
|-----------|-------------|
| `AnnouncementBanner` | Top banner notification |
| `Navbar` | Navigation header |
| `Hero` | Hero section with CTA |
| `SocialProof` | Trust indicators |
| `TerminalDemo` | Animated CLI demo |
| `LogoGrid` | Technology stack logos |
| `BeforeAfter` | Before/after comparison |
| `FeatureCards` | Feature highlights |
| `HowItWorks` | Step-by-step guide |
| `ArchitectureFlow` | System architecture diagram |
| `AgentCards` | Agent descriptions |
| `Stats` | Project statistics |
| `CTA` | Call-to-action section |
| `Footer` | Footer links |
| `CardSpotlight` | Interactive card effect |
| `AnimateOnScroll` | Scroll animation wrapper |

## Configuration Management

```yaml
migration_config.yaml
    │
    ├─► Source Configuration
    │   ├─► Application path
    │   ├─► Backend settings (type, build_tool, java_version)
    │   ├─► Frontend settings (type, build_tool, node_version)
    │   └─► Database settings (type, mode, data_file)
    │
    ├─► GCP Configuration
    │   ├─► Project details (project_id, region, zone)
    │   ├─► Authentication (service_account_key or ADC)
    │   ├─► Backend settings (Cloud Run: service_name, memory, cpu, scaling, env_vars)
    │   ├─► Frontend settings (Firebase: site_name, custom_domain)
    │   ├─► Database strategy (keep-h2 or migrate-to-cloud-sql)
    │   │   └─► Cloud SQL settings (instance, tier, version)
    │   └─► Artifact Registry (repo_name, format)
    │
    ├─► Migration Behavior
    │   ├─► Execution mode (interactive / automated)
    │   ├─► Dry run toggle
    │   ├─► Verbose logging
    │   ├─► Backup settings (enabled, path)
    │   └─► Agent config (max_retries, timeout, parallel_execution)
    │
    ├─► AI Configuration (Dedalus SDK)
    │   ├─► Default model (anthropic/claude-opus-4-6)
    │   ├─► Multi-model routing (auto per phase)
    │   ├─► Temperature (0.3)
    │   ├─► Max tokens (4096)
    │   ├─► Recommendations toggle
    │   └─► MCP servers (windsor/brave-search-mcp)
    │
    ├─► Post-Migration
    │   ├─► Health checks
    │   ├─► Report generation
    │   ├─► Cost estimates
    │   └─► Open in browser
    │
    └─► Notifications (optional)
        ├─► Slack webhook
        └─► Email
```

## Environment Variables

```bash
# Required — AI Keys (at least one)
DEDALUS_API_KEY=            # Primary — Dedalus SDK (multi-model routing)
ANTHROPIC_API_KEY=          # Fallback — Direct Claude API

# Required — GCP
GCP_PROJECT_ID=             # Google Cloud project ID
GCP_REGION=us-central1      # GCP region
GOOGLE_APPLICATION_CREDENTIALS=  # Path to service account JSON (or use ADC)

# Optional
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
DRY_RUN=false               # Preview mode

# Web UI
VITE_API_BASE_URL=http://localhost:8000  # FastAPI backend URL
```

## Prerequisites

Checked at startup by `check_prerequisites()`:

| Prerequisite | Required | Check |
|-------------|----------|-------|
| `DEDALUS_API_KEY` or `ANTHROPIC_API_KEY` | Yes | Environment variable |
| `gcloud` CLI | Yes | `gcloud --version` |
| Docker | Yes | `docker --version` |
| Firebase CLI | Recommended | `firebase --version` |

## Error Handling Strategy

```
┌──────────────┐
│ Agent Error  │
└──────┬───────┘
       │
       ├─► Log Error (structlog)
       │
       ├─► Publish AGENT_FAILED event (with error details)
       │
       ├─► Return AgentResult(FAILED, errors=[...])
       │
       └─► Orchestrator handles
           │
           ├─► Code Analysis fails: Abort migration
           ├─► Infrastructure fails: Abort migration
           ├─► Database Migration fails: Continue with warning
           └─► Backend/Frontend fails: Report in summary
```

## Parallel Execution

```
Sequential Phase 1:
┌──────────────────────────┐
│ CodeAnalyzer [REASONING] │
└──────┬───────────────────┘
       │
       ▼
Sequential Phase 2:
┌──────────────────────────┐
│ Infrastructure [PLANNING]│
└──────┬───────────────────┘
       │
       ▼
Sequential Phase 3:
┌────────────────────────────┐
│ Database Mig. [MULTI_MODEL]│
└──────┬─────────────────────┘
       │
       ▼
Parallel Phase 4:
┌────────────────────────┐  ┌─────────────────────────┐
│ Backend Deploy [OPUS]  │  │ Frontend Deploy [FAST]  │
└────────────────────────┘  └─────────────────────────┘
       │                            │
       └────────────┬───────────────┘
                    ▼
           Migration Complete
```

## Security Considerations

1. **GCP Authentication**
   - Service account key file (via `GOOGLE_APPLICATION_CREDENTIALS`)
   - Application Default Credentials (ADC)
   - Never commit credentials

2. **API Keys**
   - Stored in `.env` file
   - Never committed to git
   - Loaded at runtime via `python-dotenv`

3. **Container Security**
   - Non-root user in Docker (spring:spring)
   - Minimal base images (Alpine Linux)
   - No secrets baked into images
   - Platform-specific builds (linux/amd64 for Cloud Run)

4. **IAM Permissions**
   - Least privilege principle
   - Specific role assignments (roles/run.admin, roles/iam.serviceAccountUser)
   - Service account isolation

5. **Web Backend**
   - CORS middleware (configurable origins)
   - Process isolation (migrations run as subprocesses)
   - Graceful cancellation via SIGTERM

6. **Dockerfile Sanitization**
   - `_clean_dockerfile_content()` strips markdown fences and prose from LLM output
   - Validates Dockerfile instructions before writing

## Tech Stack

### Core (Python)
| Package | Version | Purpose |
|---------|---------|---------|
| `dedalus-labs` | >= 0.2.0 | Multi-model handoffs, tool calling, MCP |
| `anthropic` | >= 0.42.0 | Claude API (fallback) |
| `typer` | >= 0.15.0 | CLI framework |
| `rich` | >= 13.9.0 | Terminal UI, progress bars |
| `fastapi` | >= 0.115.0 | Web backend REST API |
| `uvicorn` | >= 0.30.0 | ASGI server |
| `pyyaml` | >= 6.0.2 | Configuration parsing |
| `python-dotenv` | >= 1.0.1 | Environment variables |
| `structlog` | >= 24.4.0 | Structured JSON logging |
| `docker` | >= 7.1.0 | Docker SDK |
| `google-cloud-run` | >= 0.11.1 | GCP Cloud Run SDK |
| `google-cloud-storage` | >= 2.19.0 | GCP Storage SDK |
| `google-cloud-firestore` | >= 2.20.0 | GCP Firestore SDK |
| `httpx` | >= 0.28.0 | Async HTTP client |
| `aiofiles` | >= 24.1.0 | Async file operations |

### Marketing Site (Next.js)
| Package | Version | Purpose |
|---------|---------|---------|
| `next` | 16.1.6 | React framework (App Router) |
| `react` | 19.2.3 | UI library |
| `framer-motion` | ^12.33.0 | Animations |
| `tailwindcss` | ^4 | Utility-first CSS |
| `typescript` | ^5 | Type safety |

### Web Console
| Stack | Purpose |
|-------|---------|
| React + Vite | Single-page migration console |
| EventSource API | SSE log streaming |

### Testing & Quality
| Package | Purpose |
|---------|---------|
| `pytest` + `pytest-asyncio` | Unit & async tests |
| `pytest-cov` | Code coverage |
| `pytest-mock` | Mocking |
| `mypy` | Static type checking |
| `black` | Code formatting |
| `ruff` | Linting |

## Project Structure

```
Cloudify/
├── migration_orchestrator.py   # CLI entry point (Typer app)
├── migration_config.yaml       # Configuration template
├── requirements.txt            # Python dependencies
├── quickstart.sh               # Automated setup script
├── evidence_pack.json          # Project metrics
├── .env                        # Environment variables (not committed)
│
├── agents/                     # Multi-agent system
│   ├── base_agent.py           # BaseAgent, EventBus, EventType, ModelRole
│   ├── orchestrator.py         # OrchestratorAgent (coordinator)
│   ├── code_analyzer.py        # CodeAnalyzerAgent
│   ├── infrastructure.py       # InfrastructureAgent
│   ├── database_migration.py   # DatabaseMigrationAgent
│   ├── backend_deployment.py   # BackendDeploymentAgent
│   ├── frontend_deployment.py  # FrontendDeploymentAgent
│   └── dedalus_tools.py        # 21 typed tool functions for Dedalus SDK
│
├── utils/                      # Helper utilities
│   ├── file_operations.py      # FileOperations (YAML, file I/O)
│   ├── gcp_utils.py            # GCP helper functions
│   └── logging_config.py       # Structured logging setup
│
├── templates/                  # Dockerfile and CloudBuild templates
│
├── tests/                      # Test suites
│
├── web_backend/                # FastAPI web backend
│   └── app.py                  # REST API + SSE streaming (162 lines)
│
├── web_ui/                     # React + Vite web console
│   └── src/App.jsx             # Migration console with live logs (276 lines)
│
└── frontend/                   # Next.js 16 marketing site
    ├── app/
    │   ├── layout.tsx          # Root layout
    │   └── page.tsx            # Home page
    ├── components/             # 16 React components
    │   ├── Hero.tsx
    │   ├── TerminalDemo.tsx
    │   ├── ArchitectureFlow.tsx
    │   ├── AgentCards.tsx
    │   ├── FeatureCards.tsx
    │   ├── HowItWorks.tsx
    │   ├── BeforeAfter.tsx
    │   ├── Stats.tsx
    │   ├── CTA.tsx
    │   └── ...
    └── package.json
```

## Extensibility

### Adding a New Agent

```python
from agents.base_agent import BaseAgent, AgentResult, AgentStatus, EventType, ModelRole

class NewAgent(BaseAgent):
    def __init__(self, event_bus, config, dedalus_api_key):
        super().__init__(
            name="NewAgent",
            event_bus=event_bus,
            config=config,
            dedalus_api_key=dedalus_api_key,
        )
        self.event_bus.subscribe(EventType.SOME_EVENT, self._on_some_event)

    async def _execute_impl(self) -> AgentResult:
        # Use Dedalus with optimal model and tools
        result = await self.run_with_dedalus(
            prompt="Analyze the configuration...",
            model=ModelRole.REASONING.value,
            tools=[some_tool_function],
            mcp_servers=["windsor/brave-search-mcp"],
        )

        return AgentResult(
            status=AgentStatus.SUCCESS,
            data={"result": result},
        )
```

### Adding a New Tool

```python
# In agents/dedalus_tools.py
async def new_tool(param1: str, param2: int) -> str:
    """One-line description for Dedalus schema extraction.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        JSON string with result.
    """
    # Implementation
    return json.dumps({"success": True, "data": "..."})
```

### Adding a New Event Type

```python
class EventType(Enum):
    # Existing events...
    NEW_CUSTOM_EVENT = "new_custom_event"
```

## Monitoring & Observability

```
┌──────────────────┐
│  Rich Console    │ ◄─── Real-time progress bars, model/tool display
└──────────────────┘

┌──────────────────┐
│  Web Console     │ ◄─── SSE log stream, agent progress tracker
└──────────────────┘

┌──────────────────┐
│  Structlog       │ ◄─── Structured JSON logs
└──────────────────┘

┌──────────────────┐
│  Event History   │ ◄─── Full event timeline (EventBus._event_history)
└──────────────────┘

┌──────────────────┐
│  Agent Results   │ ◄─── models_used, tools_called per agent
└──────────────────┘

┌──────────────────┐
│  Dedalus Summary │ ◄─── Total model handoffs & tool calls
└──────────────────┘
```

## Testing Strategy

### Unit Tests
- Mock external dependencies (GCP, Docker, Dedalus)
- Test agent logic in isolation
- Verify event publishing and model/tool tracking

### Integration Tests
- Test with real GCP APIs
- Verify end-to-end flows
- Check resource creation

### Example Test
```python
@pytest.mark.asyncio
async def test_code_analyzer():
    event_bus = EventBus()
    config = {...}
    agent = CodeAnalyzerAgent(event_bus, config, "dedalus-api-key")

    result = await agent.execute()

    assert result.status == AgentStatus.SUCCESS
    assert "backend" in result.data
    assert len(result.models_used) > 0
    assert len(result.tools_called) > 0
```

---

This architecture enables:
- **Multi-Model Intelligence** — Each phase uses the optimal AI model via Dedalus SDK
- **Tool Calling** — 21 typed tools auto-extracted by Dedalus for agentic loops
- **Scalability** — Add new agents, tools, and models easily
- **Maintainability** — Loose coupling via event bus
- **Testability** — Isolated components with mockable dependencies
- **Reliability** — Comprehensive error handling with policy-based escalation
- **Performance** — Parallel execution of backend/frontend deployment
- **Observability** — Real-time progress via CLI, web console, and structured logs
