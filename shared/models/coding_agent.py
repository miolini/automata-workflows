"""
Coding Agent Workflow data models for Automata Workflows
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class GitCredentialsType(str, Enum):
    """Types of Git credentials supported."""
    USERNAME_PASSWORD = "username_password"
    KEY_CERT = "key_cert"
    ACCESS_TOKEN = "access_token"


class GitCredentials(BaseModel):
    """Git repository credentials."""
    
    credential_type: GitCredentialsType = Field(..., description="Type of credentials")
    username: str | None = Field(default=None, description="Username for username/password auth")
    password: str | None = Field(default=None, description="Password for username/password auth")
    private_key_path: str | None = Field(default=None, description="Path to private key file")
    private_key: str | None = Field(default=None, description="Private key content")
    certificate_path: str | None = Field(default=None, description="Path to certificate file")
    certificate: str | None = Field(default=None, description="Certificate content")
    key_password: str | None = Field(default=None, description="Password for private key")
    access_token: str | None = Field(default=None, description="Access token for authentication")
    
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    @model_validator(mode='after')
    def validate_credentials(self):
        """Validate that appropriate credentials are provided based on type."""
        if self.credential_type == GitCredentialsType.USERNAME_PASSWORD:
            if not self.username or not self.password:
                raise ValueError("Username and password are required for USERNAME_PASSWORD authentication")
        elif self.credential_type == GitCredentialsType.KEY_CERT:
            if not self.private_key and not self.private_key_path:
                raise ValueError("Private key or private key path is required for KEY_CERT authentication")
        elif self.credential_type == GitCredentialsType.ACCESS_TOKEN:
            if not self.access_token:
                raise ValueError("Access token is required for ACCESS_TOKEN authentication")
        return self


class AgentConfig(BaseModel):
    """Configuration for the coding agent."""
    
    model: str = Field(default="z-ai/glm-4.6:exacto", description="LLM model to use")
    instructions: str | None = Field(default=None, description="Custom additional instructions for the agent")
    
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class RepositoryConfig(BaseModel):
    """Git repository configuration."""
    
    remote_url: str = Field(..., description="Git repository remote URL")
    branch: str = Field(default="main", description="Git branch to checkout")
    credentials: GitCredentials = Field(..., description="Git repository credentials")
    
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class TaskConfig(BaseModel):
    """Task configuration and details."""
    
    id: str = Field(..., description="Task ID")
    project_id: str = Field(..., description="Project ID")
    company_id: str = Field(..., description="Company ID")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Detailed task description")
    requirements: list[str] = Field(default_factory=list, description="Task requirements")
    tags: list[str] = Field(default_factory=list, description="Task tags")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional task context")
    
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class CodingAgentRequest(BaseModel):
    """Input request for CodingAgentWorkflow."""
    
    agent: AgentConfig = Field(default_factory=AgentConfig, description="Agent configuration")
    repository: RepositoryConfig = Field(..., description="Repository configuration")
    task: TaskConfig = Field(..., description="Task configuration")
    
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class NotificationType(str, Enum):
    """Types of notifications sent during workflow execution."""
    WORKFLOW_STARTED = "workflow_started"
    REPO_CLONED = "repo_cloned"
    BRANCH_CREATED = "branch_created"
    PLAN_CREATED = "plan_created"
    IMPLEMENTATION_STARTED = "implementation_started"
    IMPLEMENTATION_STEP = "implementation_step"
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    CHANGES_COMMITTED = "changes_committed"
    CHANGES_PUSHED = "changes_pushed"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"


class WorkflowNotification(BaseModel):
    """Notification sent to NATS server."""
    
    workflow_id: str = Field(..., description="Workflow execution ID")
    company_id: str = Field(..., description="Company ID")
    project_id: str = Field(..., description="Project ID")
    task_id: str = Field(..., description="Task ID")
    notification_type: NotificationType = Field(..., description="Type of notification")
    message: str = Field(..., description="Notification message")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional notification details")
    timestamp: datetime = Field(..., description="Notification timestamp")
    
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class ImplementationPlan(BaseModel):
    """Implementation plan generated by LLM."""
    goal: str = Field(..., description="Overall goal of the task implementation")
    steps: list[str] = Field(..., description="Implementation steps")
    files_to_create: list[str] = Field(default_factory=list, description="Files to create")
    files_to_modify: list[str] = Field(default_factory=list, description="Files to modify")
    estimated_steps: int = Field(..., description="Number of estimated steps")
    validation_criteria: list[str] = Field(default_factory=list, description="Validation criteria")
    
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class ImplementationStep(BaseModel):
    """Single implementation step."""
    
    step_number: int = Field(..., description="Step number")
    description: str = Field(..., description="Step description")
    action_type: Literal["create_file", "edit_file", "run_command", "read_file", "list_dir"] = Field(..., description="Type of action")
    target: str = Field(..., description="Target file or directory")
    content: str | None = Field(default=None, description="Content for file operations")
    command: str | None = Field(default=None, description="Command to run")
    expected_result: str | None = Field(default=None, description="Expected result")
    
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class ValidationResult(BaseModel):
    """Result of validation step."""
    
    success: bool = Field(..., description="Whether validation passed")
    issues: list[str] = Field(default_factory=list, description="Issues found during validation")
    suggestions: list[str] = Field(default_factory=list, description="Suggestions for improvement")
    tests_passed: int = Field(default=0, description="Number of tests passed")
    tests_failed: int = Field(default=0, description="Number of tests failed")
    
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class CodingAgentResult(BaseModel):
    """Result of CodingAgentWorkflow execution."""
    
    success: bool = Field(..., description="Whether workflow completed successfully")
    workflow_id: str = Field(..., description="Workflow execution ID")
    company_id: str = Field(..., description="Company ID")
    project_id: str = Field(..., description="Project ID")
    task_id: str = Field(..., description="Task ID")
    branch_name: str = Field(..., description="Created branch name")
    commit_hash: str | None = Field(default=None, description="Final commit hash")
    implementation_plan: ImplementationPlan | None = Field(default=None, description="Implementation plan")
    steps_completed: int = Field(default=0, description="Number of steps completed")
    validation_result: ValidationResult | None = Field(default=None, description="Final validation result")
    error_message: str | None = Field(default=None, description="Error message if workflow failed")
    execution_time_hours: float = Field(..., description="Total execution time in hours")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="Generated artifacts")
    
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})