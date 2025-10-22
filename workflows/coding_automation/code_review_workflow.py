"""
Code Review Automation Workflow

This workflow automates the code review process for pull requests,
including static analysis, security scanning, and automated feedback generation.
"""

from datetime import timedelta
from typing import Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

from shared.models.github import PullRequestInfo, CodeReviewResult
from shared.activities.github import (
    get_pull_request_details,
    post_review_comment,
    get_diff_content,
)
from shared.activities.analysis import (
    run_static_analysis,
    run_security_scan,
    generate_review_summary,
)
from shared.activities.ai import (
    analyze_code_changes,
    generate_review_feedback,
)


@workflow.defn
class CodeReviewWorkflow:
    """Automated code review workflow for pull requests."""

    @workflow.run
    async def run(self, input: PullRequestInfo) -> CodeReviewResult:
        """
        Run the automated code review process.
        
        Args:
            input: Pull request information including repo, PR number, etc.
            
        Returns:
            CodeReviewResult: Summary of the review findings and recommendations.
        """
        workflow.logger.info(f"Starting code review for PR #{input.pr_number} in {input.repository}")
        
        try:
            # Step 1: Get PR details and diff
            pr_details = await workflow.execute_activity(
                get_pull_request_details,
                input,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(minutes=1),
                    backoff_coefficient=2.0,
                    maximum_attempts=3,
                ),
            )
            
            diff_content = await workflow.execute_activity(
                get_diff_content,
                input,
                start_to_close_timeout=timedelta(minutes=3),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(minutes=1),
                    backoff_coefficient=2.0,
                    maximum_attempts=3,
                ),
            )
            
            # Step 2: Run static analysis and security scans
            static_analysis_result = await workflow.execute_activity(
                run_static_analysis,
                diff_content,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=2),
                    maximum_interval=timedelta(minutes=2),
                    backoff_coefficient=2.0,
                    maximum_attempts=2,
                ),
            )
            
            security_scan_result = await workflow.execute_activity(
                run_security_scan,
                diff_content,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=2),
                    maximum_interval=timedelta(minutes=2),
                    backoff_coefficient=2.0,
                    maximum_attempts=2,
                ),
            )
            
            # Step 3: AI-powered code analysis
            ai_analysis = await workflow.execute_activity(
                analyze_code_changes,
                {
                    "pr_details": pr_details,
                    "diff_content": diff_content,
                    "static_analysis": static_analysis_result,
                    "security_scan": security_scan_result,
                },
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    maximum_interval=timedelta(minutes=5),
                    backoff_coefficient=2.0,
                    maximum_attempts=2,
                ),
            )
            
            # Step 4: Generate review feedback
            review_feedback = await workflow.execute_activity(
                generate_review_feedback,
                {
                    "ai_analysis": ai_analysis,
                    "static_analysis": static_analysis_result,
                    "security_scan": security_scan_result,
                },
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=2),
                    maximum_interval=timedelta(minutes=2),
                    backoff_coefficient=2.0,
                    maximum_attempts=2,
                ),
            )
            
            # Step 5: Generate final summary
            review_summary = await workflow.execute_activity(
                generate_review_summary,
                {
                    "pr_details": pr_details,
                    "review_feedback": review_feedback,
                    "static_analysis": static_analysis_result,
                    "security_scan": security_scan_result,
                },
                start_to_close_timeout=timedelta(minutes=3),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(minutes=1),
                    backoff_coefficient=2.0,
                    maximum_attempts=3,
                ),
            )
            
            # Step 6: Post review comment (if enabled)
            if input.post_review_comment:
                await workflow.execute_activity(
                    post_review_comment,
                    {
                        "pr_info": input,
                        "review_summary": review_summary,
                    },
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=1),
                        maximum_interval=timedelta(minutes=1),
                        backoff_coefficient=2.0,
                        maximum_attempts=3,
                    ),
                )
            
            workflow.logger.info(f"Code review completed for PR #{input.pr_number}")
            
            return CodeReviewResult(
                pr_number=input.pr_number,
                repository=input.repository,
                review_summary=review_summary,
                static_analysis=static_analysis_result,
                security_scan=security_scan_result,
                ai_analysis=ai_analysis,
                status="completed",
            )
            
        except Exception as e:
            workflow.logger.error(f"Code review failed for PR #{input.pr_number}: {e}")
            raise