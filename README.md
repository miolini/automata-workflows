# Automata Workflows - Python Temporal Implementation

**Enterprise Multi-Agent Process Automation Platform - Workflow Engine**

[![License](https://img.shields.io/badge/license-Proprietary-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Temporal](https://img.shields.io/badge/temporal-1.0+-orange.svg)](https://temporal.io)

## Overview

This repository contains the Python implementation of Temporal workflows for the Automata platform. Each workflow is isolated in its own directory and represents a critical business process that runs on Temporal.io for reliability, scalability, and fault tolerance.

## Architecture

### Umbrella Project Structure

```
automata-workflows/
├── workflows/                    # Individual workflow implementations
│   ├── coding_automation/       # Code review, PR management, etc.
│   ├── fine_tuning/             # ML model fine-tuning pipelines
│   ├── agent_orchestration/     # Multi-agent coordination
│   ├── billing_tracking/        # Usage tracking and billing
│   └── system_management/       # Infrastructure and monitoring
├── shared/                      # Common utilities and base classes
│   ├── activities/              # Reusable Temporal activities
│   ├── models/                  # Data models and schemas
│   ├── clients/                 # External service clients
│   └── utils/                   # Helper functions
├── tests/                       # Test suites for all workflows
├── scripts/                     # Deployment and utility scripts
└── docs/                        # Workflow documentation
```

### Workflow Categories

#### 🤖 Coding Automation Workflows
- **Code Review Automation**: Automated PR analysis and feedback
- **Bug Triage**: Intelligent issue categorization and prioritization
- **CI/CD Orchestration**: Pipeline management and deployment coordination
- **Documentation Generation**: Automated doc creation and updates

#### 🧠 ML Fine-Tuning Workflows
- **Adapter Training**: QLoRA adapter fine-tuning pipelines
- **Model Evaluation**: Performance testing and validation
- **Continuous Learning**: Automated model improvement cycles
- **A/B Testing**: Model comparison and rollout management

#### 🎭 Agent Orchestration Workflows
- **Multi-Agent Coordination**: Complex task delegation and synchronization
- **Context Management**: Agent state and memory management
- **Conflict Resolution**: Handling competing agent decisions
- **Task Distribution**: Intelligent workload balancing

#### 💰 Billing & Usage Workflows
- **Usage Tracking**: Real-time resource consumption monitoring
- **Billing Cycles**: Automated invoice generation and processing
- **Cost Optimization**: Resource usage analysis and recommendations
- **Revenue Recognition**: Subscription and usage-based billing

#### 🔧 System Management Workflows
- **Health Monitoring**: System health checks and alerting
- **Backup Operations**: Data backup and recovery procedures
- **Maintenance Tasks**: Scheduled system maintenance
- **Incident Response**: Automated incident handling and escalation

## Technology Stack

### Core Dependencies
- **Python 3.14+**: Latest Python with advanced async/await and pattern matching
- **Temporal.io**: Durable workflow execution engine
- **Pydantic**: Data validation and serialization
- **AsyncIO**: Asynchronous programming support

### External Integrations
- **Modal.com**: ML inference and fine-tuning
- **GitHub/GitLab**: Version control operations
- **Slack/Teams**: Messaging platform integration
- **Jira/Trello**: Task tracker integration
- **PostgreSQL**: State persistence and analytics

## Development Setup

### Prerequisites
- Python 3.14+ (UV will manage the Python version)
- [UV](https://docs.astral.sh/uv/) - Modern Python package manager
- Podman and Podman Compose
- Temporal CLI tools
- PostgreSQL 15+

### Installation

1. **Install UV** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # or with pip: pip install uv
   ```

2. **Clone the repository**
   ```bash
   git clone https://github.com/sentientwave/automata-workflows.git
   cd automata-workflows
   ```

3. **Set up the project with UV**
   ```bash
   make install
   # or: uv sync
   ```
   This will:
   - Create a virtual environment in `.venv/`
   - Install all dependencies from `pyproject.toml`
   - Generate a `uv.lock` file for reproducible builds

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start development environment**
   ```bash
   make dev
   ```
   This will:
   - Install dependencies
   - Start Temporal development environment
   - Prepare the system for workflow execution

6. **Run database migrations**
   ```bash
   make migrate
   # or: uv run python scripts/migrate_db.py
   ```

### Running Workflows

#### Quick Start with Makefile
```bash
# Show current configuration
make config

# Start all workflow workers
make worker

# Start only LLM inference worker
make worker-llm

# Quick test of LLM inference
make test-llm

# Run any workflow interactively
make workflow
```

#### Manual Development Mode
```bash
# Start workflow workers
uv run python scripts/run_workers.py --workflow llm_inference

# Run individual workflow with JSON input
uv run python scripts/run_workflow.py --workflow llm_inference --input '{"model": "glm-4.6", "messages": [{"role": "user", "content": "Hello"}]}'

# Run workflow with input file
uv run python scripts/run_workflow.py --workflow llm_inference --input-file examples/llm_test_input.json
```

#### Production Mode
```bash
# Deploy all workers
podman-compose up -d workers

# Monitor workflow execution
temporal workflow list --namespace default
```

### Querying Workflows

Query and manage workflow executions from the command line or via REST API:

#### Command Line Query Tool
```bash
# List all recent workflows (last 24 hours)
uv run python scripts/query_workflows.py list

# List workflows by type
uv run python scripts/query_workflows.py list-type --workflow-type LLMInferenceWorkflow

# List only running workflows
uv run python scripts/query_workflows.py running

# List completed workflows
uv run python scripts/query_workflows.py completed --hours 48

# List failed workflows
uv run python scripts/query_workflows.py failed

# Get detailed status of a specific workflow
uv run python scripts/query_workflows.py status --workflow-id my-workflow-123

# Get workflow result (if completed)
uv run python scripts/query_workflows.py result --workflow-id my-workflow-123

# Cancel a running workflow
uv run python scripts/query_workflows.py cancel --workflow-id my-workflow-123
```

#### REST API Server

Start the API server to expose workflow querying via HTTP:

```bash
# Install optional dependencies first
uv pip install fastapi uvicorn

# Start the API server
uv run python scripts/api_server.py
```

API endpoints:
- `GET /api/workflows/list` - List all workflows
- `GET /api/workflows/recent?hours=24` - List recent workflows
- `GET /api/workflows/running` - List running workflows
- `GET /api/workflows/completed` - List completed workflows
- `GET /api/workflows/failed` - List failed workflows
- `GET /api/workflows/{workflow_id}/status` - Get workflow status
- `GET /api/workflows/{workflow_id}/result` - Get workflow result
- `POST /api/workflows/{workflow_id}/cancel` - Cancel workflow
- `POST /api/workflows/{workflow_id}/terminate` - Terminate workflow

API documentation: http://localhost:8000/docs

#### Loading Workflows on Page Reload

For web applications, use the API to load existing workflows when the page reloads:

```javascript
// Load recent workflows on page mount
async function loadWorkflows() {
  const response = await fetch('/api/workflows/recent?hours=24&workflow_type=LLMInferenceWorkflow');
  const data = await response.json();
  
  // Update UI with workflows
  setWorkflows(data.workflows);
  
  // Poll running workflows
  data.workflows
    .filter(w => w.status === 'RUNNING')
    .forEach(w => pollWorkflowStatus(w.workflow_id));
}
```

See `docs/elixir_integration.md` for complete Elixir/Phoenix and React examples.

### Development Commands

```bash
# Code quality
make lint          # Run linting and type checking
make format        # Format code with black and isort
make test          # Run tests with coverage
make clean         # Clean up cache files

# Configuration
make config        # Show current configuration
make help          # Show all available commands
```

## Workflow Development

### Creating a New Workflow

1. **Create workflow directory**
   ```bash
   mkdir workflows/my_new_workflow
   ```

2. **Implement workflow interface**
   ```python
   # workflows/my_new_workflow/workflow.py
   from temporalio import workflow
   from shared.activities import my_activity

   @workflow.defn
   class MyNewWorkflow:
       @workflow.run
       async def run(self, input: MyInput) -> MyOutput:
           result = await workflow.execute_activity(
               my_activity,
               input,
               start_to_close_timeout=timedelta(minutes=5)
           )
           return MyOutput(result=result)
   ```

3. **Add activities**
   ```python
   # workflows/my_new_workflow/activities.py
   from temporalio import activity

   @activity.defn
   async def my_activity(input: MyInput) -> str:
       # Activity implementation
       return "result"
   ```

4. **Create tests**
   ```python
   # tests/test_my_new_workflow.py
   from temporalio.testing import WorkflowEnvironment
   from workflows.my_new_workflow.workflow import MyNewWorkflow

   async def test_my_new_workflow():
       async with await WorkflowEnvironment.start_time_skipping() as env:
           result = await env.client.execute_workflow(
               MyNewWorkflow.run,
               MyInput(param="value"),
               id="test-workflow",
               task_queue="test-task-queue"
           )
           assert result.result == "expected"
   ```

### Best Practices

#### Workflow Design
- Keep workflows deterministic and idempotent
- Use activities for external service calls
- Implement proper error handling and retries
- Design for long-running operations (hours/days)

#### Activity Implementation
- Activities should be short-lived (minutes max)
- Handle network failures gracefully
- Use circuit breakers for external services
- Implement proper logging and monitoring

#### Testing Strategy
- Unit test activities in isolation
- Integration test workflows with mocked services
- End-to-end test with Temporal test environment
- Load test for performance validation

## Monitoring and Observability

### Metrics Collection
- Workflow execution metrics
- Activity performance tracking
- Error rates and retry patterns
- Resource utilization monitoring

### Logging
- Structured JSON logging
- Correlation IDs for request tracing
- Workflow and activity context preservation
- Centralized log aggregation

### Alerting
- Workflow failure notifications
- Performance degradation alerts
- Resource exhaustion warnings
- SLA breach notifications

## Deployment

### Local Development
```bash
# Run all services locally
podman-compose up -d

# Start workers in development mode
uv run python scripts/dev_server.py
```

### Kubernetes Deployment

The project includes comprehensive Helm charts for deploying to Kubernetes:

```bash
cd k8s

# Deploy to development environment
./scripts/deploy.sh dev all

# Set up port forwarding to access services
./scripts/port-forward.sh dev all

# Access Temporal Web UI at http://localhost:8088
```

#### Architecture
- **Temporal Service**: Workflow orchestration with PostgreSQL
- **Automata Workers**: Individual deployments per worker type
- **Monitoring**: Prometheus metrics and health checks
- **Security**: Non-root containers, network policies, secrets management

#### Environment Configuration
- **Development**: Single replicas, minimal resources, debug logging
- **Production**: Multiple replicas, resource limits, structured logging

#### Management Commands
```bash
# Deploy components
./scripts/deploy.sh <env> <component>  # env: dev/staging/prod, component: temporal/workers/all

# Destroy deployments
./scripts/destroy.sh <env> <component>

# Port forwarding
./scripts/port-forward.sh <env> <service>

# Check status
kubectl get pods -n automata-dev
```

For detailed instructions, see [k8s/docs/kubernetes-deployment.md](k8s/docs/kubernetes-deployment.md).

### Staging Environment
```bash
# Deploy to staging using Helm charts
./scripts/deploy.sh staging all

# Run smoke tests
uv run python scripts/smoke_tests.py --env staging
```

### Production Deployment
```bash
# Deploy to production using Helm charts
./scripts/deploy.sh prod all

# Verify deployment
uv run python scripts/health_check.py --env production
```

## UV Package Management

This project uses [UV](https://docs.astral.sh/uv/) for modern Python package management. UV provides:

- **Fast dependency resolution** (10-100x faster than pip)
- **Deterministic builds** with lock files
- **Virtual environment management**
- **Unified dependency management**

### Common UV Commands

```bash
# Install dependencies
uv sync

# Add a new dependency
uv add requests

# Add a development dependency
uv add --dev pytest

# Run commands in the project environment
uv run python scripts/run_workflow.py

# Update dependencies
uv sync --upgrade

# Show dependency tree
uv tree

# Check for outdated packages
uv pip list --outdated
```

### Virtual Environment

UV automatically creates and manages a virtual environment in `.venv/`. To activate it manually:

```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

However, it's recommended to use `uv run` instead of activating the environment directly.

## Configuration

### Environment Variables
```bash
# Temporal Configuration
TEMPORAL_HOST=localhost:7233
TEMPORAL_NAMESPACE=automata

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost/automata

# External Services
MODAL_TOKEN=your_modal_token
GITHUB_TOKEN=your_github_token
SLACK_BOT_TOKEN=your_slack_token
```

### Workflow-Specific Settings
Each workflow can have its own configuration file in `config/workflows/`.

## Security

### Authentication & Authorization
- JWT-based authentication for workflow access
- Role-based access control (RBAC)
- API key management for external services
- Audit logging for all workflow operations

### Data Protection
- Encryption at rest and in transit
- PII redaction in logs
- Secure credential management
- Compliance with GDPR and SOC 2

## Contributing

This is a proprietary SentientWave product. Internal contributors should:

1. Follow the established code patterns and conventions
2. Write comprehensive tests for all new functionality
3. Update documentation for any API changes
4. Ensure all workflows are production-ready

## Support

- **Internal Documentation**: Confluence space "Automata Workflows"
- **Slack Channel**: #automata-workflows
- **Issue Tracking**: Jira project "AUT"
- **On-call Rotation**: PagerDuty schedule "Automata-Workflows"

## License

Copyright © 2025 SentientWave. All rights reserved.

This is proprietary software. Unauthorized copying, distribution, or modification is strictly prohibited.

---

**Built with ❤️ by SentientWave**