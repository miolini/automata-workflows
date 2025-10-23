"""
Coding Agent Workflow Example

This example demonstrates how to start a CodingAgentWorkflow to work on a coding task.
"""

import asyncio
import os
import sys
from datetime import timedelta

from temporalio.client import Client

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models.coding_agent import (
    AgentConfig,
    CodingAgentRequest,
    GitCredentials,
    GitCredentialsType,
    RepositoryConfig,
    TaskConfig,
)


async def main():
    """Run the Coding Agent workflow example."""
    # Connect to Temporal
    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    client = await Client.connect(temporal_host)

    # Example 1: Basic usage with username/password authentication
    basic_request = CodingAgentRequest(
        agent=AgentConfig(),  # Use defaults
        repository=RepositoryConfig(
            remote_url="https://github.com/username/repository.git",
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
            title="Add user authentication feature",
            description="Implement JWT-based user authentication with login and registration endpoints. Create user model with email and password fields, implement password hashing using bcrypt, create login endpoint that returns JWT token, create registration endpoint, and add authentication middleware. Users should be able to register with email and password, login and receive JWT token. Protected endpoints must require valid JWT token and passwords must be securely hashed. All tests must pass.",
            requirements=[
                "Create user model with email and password fields",
                "Implement password hashing using bcrypt",
                "Create login endpoint that returns JWT token",
                "Create registration endpoint",
                "Add authentication middleware",
            ],
            tags=["authentication", "security", "api"],
        ),
    )

    # Example 2: Task with access token authentication (GitHub)
    request_token_auth = CodingAgentRequest(
        agent=AgentConfig(
            model="z-ai/glm-4.6:exacto",
            instructions="Focus on database transactions and add comprehensive error logging.",
        ),
        repository=RepositoryConfig(
            remote_url="https://github.com/username/repository.git",
            branch="develop",
            credentials=GitCredentials(
                credential_type=GitCredentialsType.ACCESS_TOKEN,
                access_token=os.getenv("GITHUB_TOKEN", "ghp_xxxxxxxxxxxx"),
            ),
        ),
        task=TaskConfig(
            id="task-790",
            project_id="project-456",
            company_id="company-123",
            title="Fix bug in user profile update",
            description="Fix the bug where user profile updates are not being saved to the database.",
            requirements=[
                "Investigate why profile updates fail",
                "Fix the database transaction issue",
                "Add proper error handling",
                "Add unit tests for profile update",
            ],
            tags=["bug", "profile", "database"],
        ),
    )

    # Example 3: Task with SSH key authentication
    request_ssh_auth = CodingAgentRequest(
        agent=AgentConfig(),  # Use defaults
        repository=RepositoryConfig(
            remote_url="git@github.com:username/repository.git",
            branch="main",
            credentials=GitCredentials(
                credential_type=GitCredentialsType.KEY_CERT,
                private_key_path=os.path.expanduser("~/.ssh/id_rsa"),
                key_password=None,  # If key is encrypted
            ),
        ),
        task=TaskConfig(
            id="task-791",
            project_id="project-456",
            company_id="company-123",
            title="Refactor database query performance",
            description="Optimize slow database queries identified in the performance audit.",
            requirements=[
                "Add database indexes for frequently queried fields",
                "Optimize N+1 query issues",
                "Add query result caching",
                "Update ORM queries to use eager loading",
            ],
            tags=["performance", "database", "optimization"],
        ),
    )

    # Choose which example to run
    request = request_token_auth  # Change this to run different examples

    print(f"Starting CodingAgentWorkflow for task: {request.task.title}")
    print(f"Company ID: {request.task.company_id}")
    print(f"Project ID: {request.task.project_id}")
    print(f"Task ID: {request.task.id}")
    print(f"Repository: {request.repository.remote_url}")
    print(f"Branch: {request.repository.branch}")
    print()

    # Start the workflow
    workflow_id = f"coding-agent-{request.task.id}"
    handle = await client.start_workflow(
        "CodingAgentWorkflow.run",
        request,
        id=workflow_id,
        task_queue="coding-agent",
        execution_timeout=timedelta(hours=24),  # Default timeout
    )

    print(f"Workflow started with ID: {workflow_id}")
    print(f"Workflow URL: http://localhost:8080/namespaces/default/workflows/{workflow_id}")
    print()
    print("Waiting for workflow to complete...")
    print("(This may take a while depending on the task complexity)")
    print()

    # Wait for result
    result = await handle.result()

    print("=" * 80)
    print("WORKFLOW COMPLETED")
    print("=" * 80)
    print(f"Success: {result.success}")
    print(f"Branch name: {result.branch_name}")
    print(f"Commit hash: {result.commit_hash}")
    print(f"Steps completed: {result.steps_completed}")
    print(f"Execution time: {result.execution_time_hours:.2f} hours")
    print()

    if result.implementation_plan:
        print("Implementation Plan:")
        print(f"  - Total steps: {len(result.implementation_plan.steps)}")
        print(f"  - Files created: {len(result.implementation_plan.files_to_create)}")
        print(f"  - Files modified: {len(result.implementation_plan.files_to_modify)}")
        print()

    if result.validation_result:
        print("Validation Result:")
        print(f"  - Success: {result.validation_result.success}")
        print(f"  - Tests passed: {result.validation_result.tests_passed}")
        print(f"  - Tests failed: {result.validation_result.tests_failed}")
        print(f"  - Issues: {len(result.validation_result.issues)}")
        print()

    if result.error_message:
        print(f"Error: {result.error_message}")
        print()

    print("Artifacts:")
    for key, value in result.artifacts.items():
        print(f"  - {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
