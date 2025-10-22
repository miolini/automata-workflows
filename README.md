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

### Staging Environment
```bash
# Deploy to staging
kubectl apply -f k8s/staging/

# Run smoke tests
uv run python scripts/smoke_tests.py --env staging
```

### Production Deployment
```bash
# Deploy to production
kubectl apply -f k8s/production/

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