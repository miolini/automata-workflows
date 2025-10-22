"""
Code analysis activities for Automata Workflows
"""

import asyncio
from typing import Any

import structlog
from temporalio import activity

from shared.models.github import (
    DiffContent,
    ReviewSummary,
    SecurityScanResult,
    StaticAnalysisResult,
)

logger = structlog.get_logger(__name__)


@activity.defn
async def run_static_analysis(diff_content: DiffContent) -> StaticAnalysisResult:
    """
    Run static code analysis on the provided diff content.

    Args:
        diff_content: The diff content to analyze

    Returns:
        StaticAnalysisResult: Results of the static analysis
    """
    activity.logger.info("Running static code analysis")

    try:
        # Simulate static analysis
        await asyncio.sleep(2.0)

        # Mock analysis results
        mock_issues = [
            {
                "file": "src/main.py",
                "line": 15,
                "severity": "warning",
                "message": "Unused import 'os'",
                "rule": "W0611",
            },
            {
                "file": "src/main.py",
                "line": 25,
                "severity": "error",
                "message": "Undefined variable 'undefined_var'",
                "rule": "E0602",
            },
        ]

        severity_counts = {"error": 1, "warning": 1, "info": 0}
        score = 7.5  # Based on issues found

        recommendations = [
            "Remove unused imports",
            "Fix undefined variable references",
            "Add type hints for better code clarity",
        ]

        return StaticAnalysisResult(
            issues=mock_issues,
            severity_counts=severity_counts,
            score=score,
            recommendations=recommendations,
            analysis_time_ms=2000,
        )

    except Exception as e:
        activity.logger.error(f"Static analysis failed: {e}")
        raise


@activity.defn
async def run_security_scan(diff_content: DiffContent) -> SecurityScanResult:
    """
    Run security vulnerability scanning on the provided diff content.

    Args:
        diff_content: The diff content to scan

    Returns:
        SecurityScanResult: Results of the security scan
    """
    activity.logger.info("Running security vulnerability scan")

    try:
        # Simulate security scanning
        await asyncio.sleep(3.0)

        # Mock security scan results
        mock_vulnerabilities = [
            {
                "file": "src/main.py",
                "line": 30,
                "severity": "medium",
                "cve": None,
                "message": "Potential SQL injection vulnerability",
                "rule": "SQL_INJECTION",
            }
        ]

        severity_counts = {"critical": 0, "high": 0, "medium": 1, "low": 0}
        risk_score = 6.0

        recommendations = [
            "Use parameterized queries for database operations",
            "Implement input validation and sanitization",
            "Review database access patterns",
        ]

        return SecurityScanResult(
            vulnerabilities=mock_vulnerabilities,
            severity_counts=severity_counts,
            risk_score=risk_score,
            recommendations=recommendations,
            scan_time_ms=3000,
        )

    except Exception as e:
        activity.logger.error(f"Security scan failed: {e}")
        raise


@activity.defn
async def generate_review_summary(input: dict[str, Any]) -> ReviewSummary:
    """
    Generate a comprehensive review summary from all analysis results.

    Args:
        input: Dictionary containing all analysis results

    Returns:
        ReviewSummary: Comprehensive review summary
    """
    activity.logger.info("Generating review summary")

    try:
        pr_details = input["pr_details"]
        input["review_feedback"]
        static_analysis = input["static_analysis"]
        security_scan = input["security_scan"]

        # Simulate summary generation
        await asyncio.sleep(1.0)

        # Calculate overall score based on all analyses
        scores = [
            static_analysis.score,
            10 - security_scan.risk_score,
        ]  # Invert risk score
        overall_score = sum(scores) / len(scores)

        key_findings = [
            f"Static analysis score: {static_analysis.score}/10",
            f"Security risk score: {security_scan.risk_score}/10",
            f"Total issues found: {len(static_analysis.issues) + len(security_scan.vulnerabilities)}",
        ]

        recommendations = (
            static_analysis.recommendations + security_scan.recommendations
        )

        # Determine approval recommendation
        if overall_score >= 8.0 and security_scan.risk_score < 3.0:
            approval_recommendation = "approve"
        elif overall_score >= 6.0 and security_scan.risk_score < 5.0:
            approval_recommendation = "comment"
        else:
            approval_recommendation = "request_changes"

        return ReviewSummary(
            pr_number=pr_details.pr_info.pr_number,
            repository=pr_details.pr_info.repository,
            overall_score=overall_score,
            status="completed",
            key_findings=key_findings,
            recommendations=recommendations,
            approval_recommendation=approval_recommendation,
        )

    except Exception as e:
        activity.logger.error(f"Review summary generation failed: {e}")
        raise
