# Coding Agent Workflow

## Overview

The `CodingAgentWorkflow` is an autonomous coding agent that can work on assigned software development tasks. It clones a repository, creates a feature branch, generates an implementation plan, implements changes using LLM guidance with function calling tools, validates the changes, and pushes them to the remote repository.

This workflow is designed to run for extended periods (months) and provides comprehensive monitoring through task activities stored in the database and real-time notifications via NATS.

## Features

### Core Capabilities

- **Git Repository Management**: Clone, branch creation, commit, and push operations
- **Multiple Authentication Methods**: Username/password, SSH keys, and access tokens
- **LLM-Powered Implementation**: Uses `z-ai/glm-4.6:exacto` model (200K context window)
- **Function Calling Tools**: Shell commands, file operations (read, write, list)
- **Long-Running Support**: Designed to run for months with proper state management
- **Real-Time Monitoring**: NATS notifications and database activity tracking
- **Elixir API Integration**: Completion/failure notifications to external API

### Function Calling Tools

The workflow provides the following tools to the LLM agent:

1. **run_shell_command**: Execute shell commands in the repository
2. **read_file**: Read file contents
3. **write_file**: Create or modify files
4. **list_directory**: List files and directories

## Input Parameters

### CodingAgentRequest

```python
{
    "agent": {
        "model": "string",            # LLM model to use (default: "z-ai/glm-4.6:exacto")
        "instructions": "string|null" # Custom instructions for the agent
    },
    "repository": {
        "remote_url": "string",       # Git repository URL
        "branch": "string",           # Base branch (default: "main")
        "credentials": {              # Git authentication
            "credential_type": "username_password|key_cert|access_token",
            # For username_password:
            "username": "string",
            "password": "string",
            # For key_cert:
            "private_key": "string",
            "private_key_path": "string",
            "key_password": "string|null",
            # For access_token:
            "access_token": "string"
        }
    }              # Task identifier
    "task": {
        "id": "string",
        "project_id": "string",
        "company_id": "string",
        "title": "string",
        "description": "string",
        "requirements": ["string"],
        "tags": ["string"],
        "context": {}
    }
}
```

## Workflow Steps

### 1. Initialization
- Creates temporary working directory
- Sends workflow started notification

### 2. Repository Cloning
- Clones the git repository using provided credentials
- Checks out the specified branch
- Sends repository cloned notification

### 3. Branch Creation
- Creates a new feature branch with sensible name
- Branch name format: `feat/YYYYMMDD-<task-description>`
- Sends branch created notification

### 4. Implementation Plan Generation
- Calls LLM to generate detailed implementation plan
- Includes files to create/modify, steps, and validation criteria
- Sends plan created notification

### 5. Iterative Implementation
- Executes implementation plan using LLM with function calling
- Iterates up to 10 times (default max iterations)
- Each iteration:
  - LLM analyzes current state
  - Chooses appropriate tool (read, write, run command)
  - Executes tool via Temporal activity
  - Receives result and continues
- Sends notifications for each implementation step
- Stores all activities in database

### 6. Validation
- Runs validation commands (tests, linters, etc.)
- Collects validation results
- Sends validation completed notification

### 7. Commit Changes
- Commits all changes with descriptive message
- Includes task details and implementation summary
- Sends changes committed notification

### 8. Push Changes
- Pushes feature branch to remote repository
- Handles authentication
- Sends changes pushed notification

### 9. Completion
- Calculates execution metrics
- Sends workflow completed notification
- Notifies Elixir API with results
- Cleans up temporary directory

## Notifications

### NATS Notifications

The workflow sends notifications to NATS at each step:

**Subject Format**: `{prefix}.{company_id}.{project_id}.{task_id}.{notification_type}`

**Notification Types**:
- `workflow_started`
- `repo_cloned`
- `branch_created`
- `plan_created`
- `implementation_started`
- `implementation_step`
- `validation_started`
- `validation_completed`
- `changes_committed`
- `changes_pushed`
- `workflow_completed`
- `workflow_failed`

**Notification Payload**:
```json
{
    "workflow_id": "string",
    "company_id": "string",
    "project_id": "string",
    "task_id": "string",
    "notification_type": "string",
    "message": "string",
    "details": {},
    "timestamp": "ISO8601"
}
```

### Task Activities

All task activities are stored in the database for monitoring:

**Activity Types**:
- `progress`: General progress updates
- `function_call`: LLM function call execution
- `mcp_call`: MCP server interactions (if applicable)
- `error`: Error messages

**Activity Schema**:
```json
{
    "task_id": "string",
    "activity_type": "string",
    "message": "string",
    "details": {},
    "timestamp": "ISO8601"
}
```

## Output Result

### CodingAgentResult

```python
{
    "success": bool,
    "workflow_id": "string",
    "company_id": "string",
    "project_id": "string",
    "task_id": "string",
    "branch_name": "string",
    "commit_hash": "string|null",
    "implementation_plan": {
        "steps": ["string"],
        "files_to_create": ["string"],
        "files_to_modify": ["string"],
        "estimated_steps": int,
        "validation_criteria": ["string"]
    },
    "steps_completed": int,
    "validation_result": {
        "success": bool,
        "issues": ["string"],
        "suggestions": ["string"],
        "tests_passed": int,
        "tests_failed": int
    },
    "error_message": "string|null",
    "execution_time_hours": float,
    "artifacts": {
        "llm_calls": int,
        "temp_dir": "string"
    }
}
```

## Configuration

### Environment Variables

```bash
# Temporal Configuration
TEMPORAL_HOST=localhost:7233
TEMPORAL_NAMESPACE=default
TEMPORAL_TASK_QUEUE_CODING_AGENT=coding-agent

# OpenRouter Configuration (required)
OPENROUTER_API_KEY=sk-or-xxx...

# NATS Configuration
NATS_URL=nats://localhost:4222
NATS_HTTP_URL=http://localhost:8222  # Optional HTTP bridge
NATS_SUBJECT_PREFIX=automata.workflows

# Elixir API Configuration
ELIXIR_WEBHOOK_URL=http://localhost:4000/api/webhooks/workflows
ELIXIR_WEBHOOK_SECRET=your-webhook-secret

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/automata
```

## Usage Examples

### Example 1: Username/Password Authentication

```python
from shared.models.coding_agent import (
    AgentConfig,
    CodingAgentRequest,
    GitCredentials,
    GitCredentialsType,
    RepositoryConfig,
    TaskConfig,
)

request = CodingAgentRequest(
    agent=AgentConfig(
        model="z-ai/glm-4.6:exacto",  # default
        instructions=None,  # optional custom instructions
    ),
    repository=RepositoryConfig(
        remote_url="https://github.com/username/repo.git",
        branch="main",
        credentials=GitCredentials(
            credential_type=GitCredentialsType.USERNAME_PASSWORD,
            username="github-username",
            password="github-password",
        ),
    ),
    task=TaskConfig(
        id="task-789",
        project_id="project-456",
        company_id="company-123",
        title="Add user authentication",
        description="Implement JWT-based authentication",
        requirements=[
            "Create user model",
            "Implement password hashing",
            "Create login endpoint",
        ],
        tags=["authentication", "security"],
    ),
)

# Start workflow
handle = await client.start_workflow(
    "CodingAgentWorkflow.run",
    request,
    id=f"coding-agent-{request.task.id}",
    task_queue="coding-agent",
)

result = await handle.result()
```

### Example 2: SSH Key Authentication

```python
request = CodingAgentRequest(
    agent=AgentConfig(
        instructions="Focus on database performance and add comprehensive benchmarks.",
    ),
    repository=RepositoryConfig(
        remote_url="git@github.com:username/repo.git",
        branch="develop",
        credentials=GitCredentials(
            credential_type=GitCredentialsType.KEY_CERT,
            private_key_path="~/.ssh/id_rsa",
            key_password=None,  # or provide if key is encrypted
        ),
    ),
    task=TaskConfig(
        id="task-790",
        project_id="project-456",
        company_id="company-123",
        title="Fix database query performance",
        description="Optimize slow queries",
        requirements=[
            "Add database indexes",
            "Fix N+1 queries",
            "Add caching",
        ],
        tags=["performance", "database"],
    ),
)
```

### Example 3: Access Token Authentication (GitHub)

```python
request = CodingAgentRequest(
    agent=AgentConfig(),  # Use defaults
    repository=RepositoryConfig(
        remote_url="https://github.com/username/repo.git",
        branch="main",
        credentials=GitCredentials(
            credential_type=GitCredentialsType.ACCESS_TOKEN,
            access_token=os.getenv("GITHUB_TOKEN"),
        ),
    ),
    task=TaskConfig(
        id="task-791",
        project_id="project-456",
        company_id="company-123",
        title="Implement new API endpoint",
        description="Create REST API endpoint for user profiles",
        requirements=[
            "Create endpoint handler",
            "Add input validation",
            "Add unit tests",
            "Update API documentation",
        ],
        tags=["api", "backend"],
    ),
)
```

## Running the Worker

Start the coding agent worker:

```bash
python workers/coding_agent_worker.py
```

Or using Docker:

```bash
docker-compose up coding-agent-worker
```

## Monitoring

### Task Activity Monitoring

Monitor task progress in real-time by querying the database:

```sql
SELECT * FROM task_activities
WHERE task_id = 'task-789'
ORDER BY timestamp DESC;
```

### NATS Monitoring

Subscribe to NATS notifications:

```bash
nats sub "automata.workflows.company-123.project-456.task-789.>"
```

### Temporal UI

Monitor workflow execution in Temporal UI:

```
http://localhost:8080/namespaces/default/workflows/{workflow_id}
```

## Error Handling

The workflow includes comprehensive error handling:

1. **Git Operations**: Retries with exponential backoff
2. **LLM Calls**: Child workflow with built-in retry logic
3. **File Operations**: Validation and size limits
4. **Shell Commands**: Security checks and timeouts
5. **Notifications**: Non-blocking, won't fail workflow

## Security Considerations

### Command Execution

The workflow blocks dangerous shell commands:
- `rm -rf /`
- Fork bombs
- Disk wiping commands
- Filesystem modifications

### File Operations

- File size limits (1MB for read operations)
- Path validation to prevent directory traversal
- UTF-8 encoding validation

### Credentials

- Credentials are not logged
- SSH keys are stored with proper permissions (0600)
- Temporary files are cleaned up

## Performance Characteristics

- **Startup Time**: ~5-10 seconds (repository cloning)
- **LLM Latency**: ~2-5 seconds per call
- **File Operations**: < 1 second per operation
- **Commit/Push**: ~2-5 seconds
- **Total Time**: Varies by task complexity (minutes to hours)

## Limitations

1. **Repository Size**: Large repositories (>1GB) may take longer to clone
2. **File Size**: Individual files limited to 5MB for read operations
3. **Iterations**: Limited to 10 iterations by default
4. **Context Window**: LLM limited to 200K tokens
5. **Timeout**: Default workflow timeout is 24 hours

## Troubleshooting

### Common Issues

**Issue**: Repository clone fails
- **Solution**: Check git credentials and repository URL

**Issue**: LLM implementation gets stuck
- **Solution**: Simplify the task description or break it into smaller tasks

**Issue**: Push fails with authentication error
- **Solution**: Verify git credentials have push permissions

**Issue**: Validation fails
- **Solution**: Check acceptance criteria and test setup

## Future Enhancements

- [ ] Support for multiple programming languages
- [ ] Integration with code review tools
- [ ] Automatic PR creation
- [ ] Advanced validation with custom test runners
- [ ] Support for monorepos with multiple projects
- [ ] Integration with CI/CD pipelines
- [ ] Rollback mechanism for failed implementations
