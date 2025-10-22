"""
AI-powered analysis activities for Automata Workflows
"""

import asyncio
from typing import Dict, Any, List
import json

from temporalio import activity
import structlog

from shared.models.github import (
    PullRequestDetails,
    DiffContent,
    StaticAnalysisResult,
    SecurityScanResult,
    AIAnalysisResult,
    ReviewFeedback,
)

logger = structlog.get_logger(__name__)


@activity.defn
async def analyze_code_changes(input: Dict[str, Any]) -> AIAnalysisResult:
    """
    Use AI to analyze code changes and provide insights.
    
    Args:
        input: Dictionary containing PR details, diff, and analysis results
        
    Returns:
        AIAnalysisResult: AI-powered analysis results
    """
    activity.logger.info("Running AI-powered code analysis")
    
    try:
        pr_details = input["pr_details"]
        diff_content = input["diff_content"]
        static_analysis = input["static_analysis"]
        security_scan = input["security_scan"]
        
        # Simulate AI analysis (in reality, this would call an LLM API)
        await asyncio.sleep(5.0)
        
        # Mock AI analysis results
        summary = (
            f"The PR introduces {len(diff_content.files)} file changes with "
            f"{diff_content.total_additions} additions and {diff_content.total_deletions} deletions. "
            f"Key changes include new functionality and bug fixes."
        )
        
        key_changes = [
            "Added new authentication module",
            "Refactored database connection logic",
            "Fixed memory leak in data processing",
            "Updated unit tests for new functionality"
        ]
        
        potential_issues = [
            "Database connection pooling not implemented",
            "Error handling could be more robust",
            "Missing input validation in API endpoints"
        ]
        
        suggestions = [
            "Consider implementing connection pooling for better performance",
            "Add comprehensive error handling with proper logging",
            "Implement input validation middleware",
            "Add integration tests for the new authentication flow"
        ]
        
        return AIAnalysisResult(
            summary=summary,
            key_changes=key_changes,
            potential_issues=potential_issues,
            suggestions=suggestions,
            confidence_score=0.85,
            analysis_time_ms=5000,
        )
        
    except Exception as e:
        activity.logger.error(f"AI analysis failed: {e}")
        raise


@activity.defn
async def generate_review_feedback(input: Dict[str, Any]) -> ReviewFeedback:
    """
    Generate detailed review feedback using AI analysis.
    
    Args:
        input: Dictionary containing AI analysis and other results
        
    Returns:
        ReviewFeedback: Detailed review feedback
    """
    activity.logger.info("Generating AI-powered review feedback")
    
    try:
        ai_analysis = input["ai_analysis"]
        static_analysis = input["static_analysis"]
        security_scan = input["security_scan"]
        
        # Simulate feedback generation
        await asyncio.sleep(3.0)
        
        overall_assessment = (
            f"This PR introduces valuable improvements but requires attention to "
            f"security and code quality issues. The changes are well-structured "
            f"but need some refinements before merging."
        )
        
        specific_comments = [
            {
                "file": "src/main.py",
                "line": 15,
                "type": "suggestion",
                "comment": "Consider using a context manager for database connections"
            },
            {
                "file": "src/auth.py",
                "line": 45,
                "type": "issue",
                "comment": "Potential security vulnerability: validate user input properly"
            }
        ]
        
        # Determine approval status based on analysis
        critical_issues = len([v for v in security_scan.vulnerabilities if v["severity"] in ["critical", "high"]])
        error_count = static_analysis.severity_counts.get("error", 0)
        
        if critical_issues > 0 or error_count > 2:
            approval_status = "request_changes"
        elif critical_issues == 0 and error_count == 0:
            approval_status = "approve"
        else:
            approval_status = "comment"
        
        priority_issues = [
            "Address security vulnerabilities in database operations",
            "Fix static analysis errors before merging"
        ]
        
        suggestions = [
            "Add more comprehensive unit tests",
            "Update documentation for new API endpoints",
            "Consider performance implications of the changes"
        ]
        
        return ReviewFeedback(
            overall_assessment=overall_assessment,
            specific_comments=specific_comments,
            approval_status=approval_status,
            priority_issues=priority_issues,
            suggestions=suggestions,
        )
        
    except Exception as e:
        activity.logger.error(f"Review feedback generation failed: {e}")
        raise