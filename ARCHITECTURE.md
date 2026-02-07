# Cloudify Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER (CLI)                              │
│                  migration_orchestrator.py                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                           │
│                  (Event Bus Coordinator)                        │
│                                                                 │
│  • Manages agent execution order                               │
│  • Handles dependencies between agents                         │
│  • Aggregates results                                          │
│  • Provides progress updates                                   │
└────────┬────────────────────────────────────────────────────────┘
         │
         │ Event Bus (Pub/Sub)
         │
    ┌────┴─────┬──────────┬──────────────┬──────────────┐
    │          │          │              │              │
┌───▼───┐  ┌──▼───┐  ┌───▼────┐  ┌──────▼─────┐  ┌────▼────┐
│ Code  │  │Infra │  │Database│  │  Backend   │  │Frontend │
│Analyze│─▶│Prov. │─▶│Migrat. │─▶│ Deployment │  │Deploym. │
│       │  │      │  │        │  │            │  │         │
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

1. **AGENT_STARTED**: Agent begins execution
2. **AGENT_COMPLETED**: Agent finished successfully
3. **AGENT_FAILED**: Agent encountered error
4. **ANALYSIS_COMPLETE**: Code analysis finished
5. **INFRASTRUCTURE_READY**: GCP resources provisioned
6. **DATABASE_MIGRATED**: Database setup complete
7. **BACKEND_DEPLOYED**: Backend deployed to Cloud Run
8. **FRONTEND_DEPLOYED**: Frontend deployed to Firebase
9. **MIGRATION_COMPLETE**: Entire migration successful
10. **ERROR_OCCURRED**: Error during migration
11. **PROGRESS_UPDATE**: Progress percentage update

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

## Data Flow

### 1. Code Analysis Phase

```
Source Code
    │
    ├─► Spring Boot Files
    │   ├─► pom.xml / build.gradle
    │   ├─► application.properties
    │   └─► Controller classes
    │
    └─► React Files
        ├─► package.json
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
    ├─► Enable APIs
    │   ├─► Cloud Run API
    │   ├─► Artifact Registry API
    │   ├─► Cloud Build API
    │   └─► Firebase API
    │
    ├─► Create Resources
    │   ├─► Artifact Registry repo
    │   ├─► IAM permissions
    │   └─► Firebase project
    │
    └─► Output
        └─► Registry URL
            └─► Project configuration
                │
                ▼
        [Event: INFRASTRUCTURE_READY]
```

### 3. Backend Deployment Phase

```
Spring Boot App
    │
    ├─► Generate Dockerfile (via Claude AI)
    │   └─► Multi-stage build
    │       ├─► Maven build stage
    │       └─► Runtime stage
    │
    ├─► Build Docker Image
    │   └─► docker build -t {image}
    │
    ├─► Push to Artifact Registry
    │   └─► docker push {registry_url}/{image}
    │
    └─► Deploy to Cloud Run
        └─► gcloud run deploy
            ├─► Set memory/CPU
            ├─► Set env vars
            └─► Configure scaling
                │
                ▼
        [Event: BACKEND_DEPLOYED]
        └─► Service URL
```

### 4. Frontend Deployment Phase

```
React App
    │
    ├─► Update Environment
    │   └─► Create .env.production
    │       └─► VITE_API_URL={backend_url}
    │
    ├─► Install Dependencies
    │   └─► npm install
    │
    ├─► Build Production Bundle
    │   └─► npm run build
    │       └─► Creates dist/ or build/
    │
    ├─► Initialize Firebase
    │   ├─► Create firebase.json
    │   └─► Create .firebaserc
    │
    └─► Deploy to Firebase
        └─► firebase deploy --only hosting
            │
            ▼
        [Event: FRONTEND_DEPLOYED]
        └─► Hosting URL
```

## Claude AI Integration

### Decision Points Where Claude is Used

1. **Code Analysis**
   - Generate migration recommendations
   - Analyze compatibility issues
   - Suggest optimizations

2. **Dockerfile Generation**
   - Create optimized multi-stage build
   - Select appropriate base images
   - Configure build tools

3. **Database Migration**
   - Recommend migration strategy
   - Provide data persistence guidance
   - Suggest connection pooling configs

4. **Error Recovery**
   - Analyze error messages
   - Suggest fixes
   - Provide alternative approaches

### Claude Prompt Pattern

```python
system_prompt = "You are a cloud migration expert..."

user_prompt = f"""
Analyze the following configuration:
{analysis_data}

Provide recommendations for:
1. Database migration
2. Container optimization
3. Security considerations

Format as JSON array.
"""

response = claude.messages.create(
    model="claude-opus-4-6",
    system=system_prompt,
    messages=[{"role": "user", "content": user_prompt}],
    max_tokens=2000,
    temperature=0.3,
)
```

## Configuration Management

```
migration_config.yaml
    │
    ├─► Source Configuration
    │   ├─► Application path
    │   ├─► Backend settings
    │   └─► Frontend settings
    │
    ├─► GCP Configuration
    │   ├─► Project details
    │   ├─► Backend settings (Cloud Run)
    │   ├─► Frontend settings (Firebase)
    │   └─► Database strategy
    │
    ├─► Migration Behavior
    │   ├─► Execution mode
    │   ├─► Parallel execution
    │   └─► Backup settings
    │
    └─► AI Configuration
        ├─► Model selection
        ├─► Temperature
        └─► Token limits
```

## Error Handling Strategy

```
┌──────────────┐
│ Agent Error  │
└──────┬───────┘
       │
       ├─► Log Error (structlog)
       │
       ├─► Publish ERROR_OCCURRED event
       │
       ├─► Return AgentResult(FAILED)
       │
       └─► Orchestrator handles
           │
           ├─► If critical: Abort migration
           │
           └─► If non-critical: Continue with warnings
```

## Parallel Execution

```
Sequential Phase 1:
┌──────────────┐
│CodeAnalyzer  │
└──────┬───────┘
       │
       ▼
Sequential Phase 2:
┌──────────────┐
│Infrastructure│
└──────┬───────┘
       │
       ▼
Sequential Phase 3:
┌──────────────┐
│Database Mig. │
└──────┬───────┘
       │
       ▼
Parallel Phase 4:
┌──────────────┐  ┌──────────────┐
│Backend Deploy│  │Frontend Depl.│
└──────────────┘  └──────────────┘
       │                  │
       └─────────┬────────┘
                 ▼
        Migration Complete
```

## Security Considerations

1. **GCP Authentication**
   - Service account key file
   - Application Default Credentials
   - Never commit credentials

2. **API Keys**
   - Stored in .env file
   - Never committed to git
   - Loaded at runtime

3. **Container Security**
   - Non-root user in Docker
   - Minimal base images
   - No secrets in images

4. **IAM Permissions**
   - Least privilege principle
   - Specific role assignments
   - Service account isolation

## Performance Optimizations

1. **Parallel Execution**
   - Backend and frontend deploy simultaneously
   - Independent operations run concurrently

2. **Docker Layer Caching**
   - Multi-stage builds
   - Dependencies cached separately
   - Source code in final layer

3. **Async Operations**
   - All agents use asyncio
   - Non-blocking I/O
   - Efficient resource usage

4. **Event-Driven Architecture**
   - No polling
   - Immediate notifications
   - Loose coupling

## Extensibility

### Adding a New Agent

```python
from agents.base_agent import BaseAgent, AgentResult, AgentStatus, EventType

class NewAgent(BaseAgent):
    def __init__(self, event_bus, config, claude_api_key):
        super().__init__(
            name="NewAgent",
            event_bus=event_bus,
            config=config,
            claude_api_key=claude_api_key,
        )

        # Subscribe to events
        self.event_bus.subscribe(
            EventType.SOME_EVENT,
            self._on_some_event
        )

    async def _execute_impl(self) -> AgentResult:
        # Implementation

        # Publish completion
        await self.event_bus.publish(Event(
            event_type=EventType.NEW_EVENT,
            source_agent=self.name,
            data={"result": "data"}
        ))

        return AgentResult(
            status=AgentStatus.SUCCESS,
            data={"key": "value"}
        )
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
│  Rich Console    │ ◄─── Real-time progress bars
└──────────────────┘

┌──────────────────┐
│  Structlog       │ ◄─── Structured JSON logs
└──────────────────┘

┌──────────────────┐
│  Event History   │ ◄─── Full event timeline
└──────────────────┘

┌──────────────────┐
│  Agent Results   │ ◄─── Detailed execution results
└──────────────────┘
```

## Testing Strategy

### Unit Tests
- Mock external dependencies
- Test agent logic in isolation
- Verify event publishing

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
    agent = CodeAnalyzerAgent(event_bus, config, "api-key")

    result = await agent.execute()

    assert result.status == AgentStatus.SUCCESS
    assert "backend" in result.data
```

---

This architecture enables:
- ✅ Scalability (add new agents easily)
- ✅ Maintainability (loose coupling)
- ✅ Testability (isolated components)
- ✅ Reliability (comprehensive error handling)
- ✅ Performance (parallel execution)
