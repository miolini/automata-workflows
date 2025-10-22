"""
GitHub-related data models for Automata Workflows
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PullRequestInfo(BaseModel):
    """Information about a GitHub pull request."""

    repository: str = Field(..., description="Repository name in format 'owner/repo'")
    pr_number: int = Field(..., description="Pull request number")
    base_branch: str = Field(..., description="Base branch name")
    head_branch: str = Field(..., description="Head branch name")
    author: str = Field(..., description="PR author username")
    title: str = Field(..., description="PR title")
    description: str | None = Field(None, description="PR description")
    labels: list[str] = Field(default_factory=list, description="PR labels")
    post_review_comment: bool = Field(
        default=True, description="Whether to post review comment"
    )

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class PullRequestDetails(BaseModel):
    """Detailed information about a pull request."""

    pr_info: PullRequestInfo
    created_at: datetime
    updated_at: datetime
    mergeable: bool | None = None
    mergeable_state: str | None = None
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    commits: int = 0
    reviewers: list[str] = Field(default_factory=list)
    assignees: list[str] = Field(default_factory=list)
    milestone: str | None = None


class DiffContent(BaseModel):
    """Content of a pull request diff."""

    files: list[dict[str, Any]] = Field(default_factory=list)
    total_additions: int = 0
    total_deletions: int = 0
    raw_diff: str | None = None


class StaticAnalysisResult(BaseModel):
    """Results from static code analysis."""

    issues: list[dict[str, Any]] = Field(default_factory=list)
    severity_counts: dict[str, int] = Field(default_factory=dict)
    score: float = Field(ge=0.0, le=10.0)
    recommendations: list[str] = Field(default_factory=list)
    analysis_time_ms: int = 0


class SecurityScanResult(BaseModel):
    """Results from security vulnerability scanning."""

    vulnerabilities: list[dict[str, Any]] = Field(default_factory=list)
    severity_counts: dict[str, int] = Field(default_factory=dict)
    risk_score: float = Field(ge=0.0, le=10.0)
    recommendations: list[str] = Field(default_factory=list)
    scan_time_ms: int = 0


class AIAnalysisResult(BaseModel):
    """Results from AI-powered code analysis."""

    summary: str
    key_changes: list[str] = Field(default_factory=list)
    potential_issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    analysis_time_ms: int = 0


class ReviewFeedback(BaseModel):
    """Generated review feedback."""

    overall_assessment: str
    specific_comments: list[dict[str, Any]] = Field(default_factory=list)
    approval_status: str  # "approve", "request_changes", "comment"
    priority_issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ReviewSummary(BaseModel):
    """Summary of the complete code review."""

    pr_number: int
    repository: str
    overall_score: float = Field(ge=0.0, le=10.0)
    status: str
    key_findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    approval_recommendation: str
    review_timestamp: datetime = Field(default_factory=datetime.now)


class CodeReviewResult(BaseModel):
    """Complete result of the code review workflow."""

    pr_number: int
    repository: str
    review_summary: ReviewSummary
    static_analysis: StaticAnalysisResult
    security_scan: SecurityScanResult
    ai_analysis: AIAnalysisResult
    status: str
    error_message: str | None = None
    execution_time_ms: int = 0


class RepositoryCredentials(BaseModel):
    """Credentials for accessing a repository."""

    token: str | None = Field(
        None, description="Access token for private repositories"
    )
    username: str | None = Field(None, description="Username for authentication")
    password: str | None = Field(None, description="Password for authentication")
    ssh_key_path: str | None = Field(None, description="Path to SSH private key")
    ssh_key_content: str | None = Field(None, description="SSH private key content")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class RepositoryInfo(BaseModel):
    """Information about a repository to be fetched and indexed."""

    remote_url: str = Field(..., description="Git repository URL")
    name: str = Field(..., description="Repository name")
    owner: str = Field(..., description="Repository owner")
    branch: str = Field(default="main", description="Branch to fetch")
    credentials: RepositoryCredentials | None = Field(
        None, description="Repository access credentials"
    )
    is_private: bool = Field(default=False, description="Whether repository is private")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class RepositoryIndex(BaseModel):
    """Indexed repository information."""

    repository_id: str
    name: str
    owner: str
    remote_url: str
    branch: str
    commit_hash: str
    file_count: int
    total_lines: int
    languages: dict[str, int] = Field(default_factory=dict)
    indexed_at: datetime = Field(default_factory=datetime.now)
    file_paths: list[str] = Field(default_factory=list)

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class RepositoryIndexingResult(BaseModel):
    """Result of repository indexing workflow."""

    repository_info: RepositoryInfo
    repository_index: RepositoryIndex | None = None
    status: str
    error_message: str | None = None
    execution_time_ms: int = 0
    files_processed: int = 0
    files_skipped: int = 0
