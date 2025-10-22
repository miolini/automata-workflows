"""
GitHub-related data models for Automata Workflows
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PullRequestInfo(BaseModel):
    """Information about a GitHub pull request."""
    
    repository: str = Field(..., description="Repository name in format 'owner/repo'")
    pr_number: int = Field(..., description="Pull request number")
    base_branch: str = Field(..., description="Base branch name")
    head_branch: str = Field(..., description="Head branch name")
    author: str = Field(..., description="PR author username")
    title: str = Field(..., description="PR title")
    description: Optional[str] = Field(None, description="PR description")
    labels: List[str] = Field(default_factory=list, description="PR labels")
    post_review_comment: bool = Field(default=True, description="Whether to post review comment")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PullRequestDetails(BaseModel):
    """Detailed information about a pull request."""
    
    pr_info: PullRequestInfo
    created_at: datetime
    updated_at: datetime
    mergeable: Optional[bool] = None
    mergeable_state: Optional[str] = None
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    commits: int = 0
    reviewers: List[str] = Field(default_factory=list)
    assignees: List[str] = Field(default_factory=list)
    milestone: Optional[str] = None


class DiffContent(BaseModel):
    """Content of a pull request diff."""
    
    files: List[Dict[str, Any]] = Field(default_factory=list)
    total_additions: int = 0
    total_deletions: int = 0
    raw_diff: Optional[str] = None


class StaticAnalysisResult(BaseModel):
    """Results from static code analysis."""
    
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    severity_counts: Dict[str, int] = Field(default_factory=dict)
    score: float = Field(ge=0.0, le=10.0)
    recommendations: List[str] = Field(default_factory=list)
    analysis_time_ms: int = 0


class SecurityScanResult(BaseModel):
    """Results from security vulnerability scanning."""
    
    vulnerabilities: List[Dict[str, Any]] = Field(default_factory=list)
    severity_counts: Dict[str, int] = Field(default_factory=dict)
    risk_score: float = Field(ge=0.0, le=10.0)
    recommendations: List[str] = Field(default_factory=list)
    scan_time_ms: int = 0


class AIAnalysisResult(BaseModel):
    """Results from AI-powered code analysis."""
    
    summary: str
    key_changes: List[str] = Field(default_factory=list)
    potential_issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    analysis_time_ms: int = 0


class ReviewFeedback(BaseModel):
    """Generated review feedback."""
    
    overall_assessment: str
    specific_comments: List[Dict[str, Any]] = Field(default_factory=list)
    approval_status: str  # "approve", "request_changes", "comment"
    priority_issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class ReviewSummary(BaseModel):
    """Summary of the complete code review."""
    
    pr_number: int
    repository: str
    overall_score: float = Field(ge=0.0, le=10.0)
    status: str
    key_findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    approval_recommendation: str
    review_timestamp: datetime = Field(default_factory=datetime.utcnow)


class CodeReviewResult(BaseModel):
    """Complete result of the code review workflow."""
    
    pr_number: int
    repository: str
    review_summary: ReviewSummary
    static_analysis: StaticAnalysisResult
    security_scan: SecurityScanResult
    ai_analysis: AIAnalysisResult
    status: str
    error_message: Optional[str] = None
    execution_time_ms: int = 0