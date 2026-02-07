# Cloudify - Automated Cloud Migration System

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Dedalus](https://img.shields.io/badge/powered%20by-Dedalus%20AI-purple.svg)

> Automated migration of Spring Boot + React + H2 applications to Google Cloud Platform using AI agents

Cloudify is an intelligent, multi-agent system built with [Dedalus AI](http://dedaluslabs.ai/) that automates the complete migration process from local development to Google Cloud Platform. Perfect for hackathons and rapid prototyping!

## 🌟 Features

- **🤖 AI-Powered Migration**: Uses Claude AI for intelligent decision-making and recommendations
- **🔄 Event-Driven Architecture**: Agents communicate via publish-subscribe pattern
- **📊 Real-Time Progress**: Beautiful CLI with live progress tracking using Rich
- **🛡️ Safe Execution**: Comprehensive error handling and validation
- **🎯 Zero Configuration**: Works out-of-the-box with sensible defaults
- **🚀 One Command Deployment**: Migrate entire stack with a single command

## 🏗️ Architecture

Cloudify uses a multi-agent system where each agent handles a specific migration task:

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

### Agent Responsibilities

1. **Code Analyzer Agent**
   - Scans Spring Boot `application.properties`
   - Detects database configuration (H2, MySQL, PostgreSQL)
   - Identifies API endpoints and CORS settings
   - Analyzes React app for API configurations
   - Outputs migration requirements report

2. **Infrastructure Provisioning Agent**
   - Creates GCP project resources using `gcloud` CLI
   - Sets up Cloud Run service
   - Configures Artifact Registry
   - Sets up Firebase project for hosting
   - Manages IAM permissions

3. **Database Migration Agent**
   - Analyzes H2 database mode (in-memory vs file-based)
   - Recommends Cloud SQL setup OR keeps H2 with warnings
   - Optionally migrates data to Cloud SQL
   - Updates Spring Boot datasource configuration

4. **Backend Deployment Agent**
   - Generates optimized Dockerfile for Spring Boot
   - Updates application properties with GCP configurations
   - Builds Docker image
   - Pushes to Artifact Registry
   - Deploys to Cloud Run
   - Configures environment variables

5. **Frontend Deployment Agent**
   - Detects React build configuration (Vite/CRA)
   - Updates API endpoint to Cloud Run URL
   - Builds React production bundle
   - Deploys to Firebase Hosting
   - Configures custom domain if provided

## 📋 Prerequisites

Before using Cloudify, ensure you have the following installed:

### Required
- **Python 3.10+** ([Download](https://www.python.org/downloads/))
- **Google Cloud SDK** ([Install Guide](https://cloud.google.com/sdk/docs/install))
- **Docker** ([Install Guide](https://docs.docker.com/get-docker/))
- **Node.js 18+** and npm ([Download](https://nodejs.org/))

### Recommended
- **Firebase CLI** (for frontend hosting)
  ```bash
  npm install -g firebase-tools
  ```

### API Keys
- **Anthropic Claude API Key** ([Get one here](https://console.anthropic.com/))
- **Dedalus API Key** (if using Dedalus features) ([Get one here](https://dedaluslabs.ai/))

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd Cloudify
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API keys
ANTHROPIC_API_KEY=your-claude-api-key-here
DEDALUS_API_KEY=your-dedalus-api-key-here
```

### 4. Set Up GCP Authentication

```bash
# Login to GCP
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Configure Docker for Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### 5. Initialize Configuration

```bash
python migration_orchestrator.py init
```

This creates a `migration_config.yaml` template. Edit it with your settings:

```yaml
source:
  path: "./BasicApp"  # Path to your application

gcp:
  project_id: "my-hackathon-project"
  region: "us-central1"

migration:
  mode: "interactive"  # or "automated"
```

### 6. Run Migration

```bash
python migration_orchestrator.py migrate \
  --source-path ./BasicApp \
  --gcp-project cloudify-486706 \
  --region us-central1
```

Or use the config file:

```bash
python migration_orchestrator.py migrate --config migration_config.yaml
```

## 📖 Usage

### Command-Line Options

```bash
python migration_orchestrator.py migrate [OPTIONS]

Options:
  -s, --source-path PATH      Path to source application directory
  -c, --config PATH           Path to migration configuration file
  -p, --gcp-project TEXT      GCP project ID (overrides config)
  -r, --region TEXT           GCP region (default: us-central1)
  -m, --mode TEXT             Execution mode: interactive or automated
  -d, --dry-run               Preview changes without executing
  -v, --verbose               Enable verbose logging
  --help                      Show this message and exit
```

### Configuration File

The `migration_config.yaml` file controls all aspects of the migration:

```yaml
# Source Application Configuration
source:
  path: "./BasicApp"
  backend:
    type: "spring-boot"
    path: "backend"
    build_tool: "maven"
    java_version: "21"
  frontend:
    type: "react"
    path: "frontend"
    build_tool: "vite"

# GCP Configuration
gcp:
  project_id: "my-project"
  region: "us-central1"

  backend:
    service_name: "expense-calculator-backend"
    memory: "1Gi"
    cpu: "1"
    min_instances: 0
    max_instances: 10
    allow_unauthenticated: true

  frontend:
    site_name: "expense-calculator-frontend"

  database:
    strategy: "keep-h2"  # or "migrate-to-cloud-sql"

# Migration Behavior
migration:
  mode: "interactive"
  dry_run: false
  verbose: true
  backup_enabled: true

# AI Configuration
ai:
  model: "claude-opus-4.6"
  temperature: 0.3
```

See [migration_config.yaml](migration_config.yaml) for full configuration options.

## 🎯 Example Migration

Let's migrate the sample expense calculator app:

```bash
# 1. Clone the sample application
git clone https://github.com/sanathmahesh/BasicApp.git

# 2. Run migration with all defaults
python migration_orchestrator.py migrate \
  --source-path ./BasicApp \
  --gcp-project my-gcp-project \
  --mode automated

# Output:
# ╔═══════════════════════════════════════════════════════════╗
# ║                      CLOUDIFY                             ║
# ║        Automated Cloud Migration to Google Cloud         ║
# ╚═══════════════════════════════════════════════════════════╝
#
# ✓ Prerequisites check passed
# ✓ Configuration valid
#
# Starting migration...
#
# ✓ CodeAnalyzer         ████████████████████ 100%  2.3s
# ✓ Infrastructure       ████████████████████ 100%  8.1s
# ✓ DatabaseMigration    ████████████████████ 100%  1.2s
# ✓ BackendDeployment    ████████████████████ 100% 45.7s
# ✓ FrontendDeployment   ████████████████████ 100% 32.4s
#
# Migration completed successfully! ✓
#
# Deployment URLs:
#   • Backend API:  https://expense-calculator-backend-abc123-uc.a.run.app
#   • Frontend App: https://my-gcp-project.web.app
```

## 🧪 Testing

Run unit tests:

```bash
pytest tests/unit -v
```

Run integration tests (requires GCP credentials):

```bash
pytest tests/integration -v
```

## 📁 Project Structure

```
Cloudify/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py              # Base agent class with event handling
│   ├── orchestrator.py            # Main orchestrator agent
│   ├── code_analyzer.py           # Code analysis agent
│   ├── infrastructure.py          # GCP infrastructure provisioning
│   ├── database_migration.py      # Database migration logic
│   ├── backend_deployment.py      # Backend to Cloud Run
│   └── frontend_deployment.py     # Frontend to Firebase
├── utils/
│   ├── __init__.py
│   ├── gcp_helpers.py             # GCP API helpers
│   ├── file_operations.py         # File I/O utilities
│   └── logger.py                  # Logging configuration
├── templates/
│   ├── Dockerfile.spring-boot.template
│   └── cloudbuild.yaml
├── tests/
│   ├── unit/
│   └── integration/
├── migration_orchestrator.py      # Main CLI entry point
├── migration_config.yaml          # Configuration template
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
└── README.md                      # This file
```

## 🔧 Advanced Configuration

### Database Migration Strategies

#### Keep H2 (Default for Development)

```yaml
gcp:
  database:
    strategy: "keep-h2"
```

**Note**: H2 in-memory database will lose data on container restart. Only suitable for development/testing.

#### Migrate to Cloud SQL

```yaml
gcp:
  database:
    strategy: "migrate-to-cloud-sql"
    cloud_sql:
      instance_name: "my-database"
      database_name: "appdb"
      tier: "db-f1-micro"
      database_version: "POSTGRES_15"
```

### Custom Environment Variables

```yaml
gcp:
  backend:
    env_vars:
      SPRING_PROFILES_ACTIVE: "prod"
      CUSTOM_VAR: "value"
```

### Parallel vs Sequential Deployment

```yaml
migration:
  agents:
    parallel_execution: true  # Deploy backend and frontend simultaneously
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Dedalus AI** for the agent framework
- **Anthropic** for the Claude API
- **Google Cloud Platform** for cloud infrastructure
- **TartanHacks** for the hackathon opportunity

## 🐛 Troubleshooting

### Common Issues

#### 1. Authentication Errors

```bash
# Re-authenticate with GCP
gcloud auth login
gcloud auth application-default login
```

#### 2. Docker Build Fails

```bash
# Ensure Docker daemon is running
docker ps

# Check Docker authentication
gcloud auth configure-docker
```

#### 3. Firebase Deployment Fails

```bash
# Login to Firebase
firebase login

# Check project association
firebase projects:list
```

#### 4. API Key Not Found

```bash
# Check environment variables
echo $ANTHROPIC_API_KEY

# Make sure .env is loaded
source .env  # or restart your terminal
```

### Debug Mode

Enable verbose logging for detailed information:

```bash
python migration_orchestrator.py migrate --verbose
```

## 📚 Resources

- [Dedalus AI Documentation](https://docs.dedaluslabs.ai/)
- [Claude API Documentation](https://docs.anthropic.com/)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Firebase Hosting Documentation](https://firebase.google.com/docs/hosting)

## 🎓 Learn More

### How It Works

1. **Code Analysis**: Claude AI analyzes your application structure and generates migration recommendations
2. **Infrastructure Setup**: Automated GCP resource provisioning with proper IAM permissions
3. **Containerization**: Optimized multi-stage Docker builds for minimal image size
4. **Deployment**: Parallel deployment to Cloud Run and Firebase Hosting
5. **Configuration**: Automatic environment variable injection and API endpoint updates

### Event-Driven Architecture

Agents communicate via an event bus using the publish-subscribe pattern:

```python
# Agent publishes event
await event_bus.publish(Event(
    event_type=EventType.BACKEND_DEPLOYED,
    source_agent="BackendDeployment",
    data={"service_url": "https://..."}
))

# Other agents subscribe
event_bus.subscribe(EventType.BACKEND_DEPLOYED, callback)
```

This allows for:
- Loose coupling between agents
- Easy addition of new agents
- Parallel execution where possible
- Clear dependency management

## 💡 Tips & Best Practices

1. **Always run in dry-run mode first**:
   ```bash
   python migration_orchestrator.py migrate --dry-run
   ```

2. **Enable backups** for safety:
   ```yaml
   migration:
     backup_enabled: true
   ```

3. **Use interactive mode** for manual approval:
   ```yaml
   migration:
     mode: "interactive"
   ```

4. **Monitor costs** with Cloud Billing alerts
5. **Review generated Dockerfiles** before production use
6. **Set up CI/CD** with the provided `cloudbuild.yaml`

## 🚀 What's Next?

Future enhancements planned:
- [ ] Support for additional frameworks (Django, Express.js)
- [ ] Multi-cloud support (AWS, Azure)
- [ ] Database data migration tools
- [ ] Web dashboard for migration monitoring
- [ ] Cost optimization recommendations
- [ ] Automated testing post-migration
- [ ] Rollback capabilities

---

**Built with ❤️ for TartanHacks 2026**

For questions or support, please open an issue on GitHub.
