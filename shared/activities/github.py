"""
GitHub integration activities for Automata Workflows
"""

import asyncio
from datetime import datetime
from typing import Any

import httpx
import structlog
from temporalio import activity

from shared.models.github import (
    DiffContent,
    PullRequestDetails,
    PullRequestInfo,
)

logger = structlog.get_logger(__name__)


class GitHubClient:
    """GitHub API client for activities."""

    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Automata-Workflows/1.0",
        }

    async def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> dict[str, Any]:
        """Make an authenticated request to GitHub API."""
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.request(
                method, f"{self.base_url}{endpoint}", **kwargs
            )
            response.raise_for_status()
            return response.json()


@activity.defn
async def get_pull_request_details(input: PullRequestInfo) -> PullRequestDetails:
    """
    Retrieve detailed information about a pull request.

    Args:
        input: Pull request information

    Returns:
        PullRequestDetails: Detailed PR information
    """
    activity.logger.info(
        f"Getting details for PR #{input.pr_number} in {input.repository}"
    )

    try:
        # In a real implementation, this would use actual GitHub API
        # For now, we'll simulate the response
        await asyncio.sleep(0.5)  # Simulate API call

        return PullRequestDetails(
            pr_info=input,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            mergeable=True,
            mergeable_state="clean",
            additions=150,
            deletions=25,
            changed_files=8,
            commits=3,
            reviewers=["reviewer1", "reviewer2"],
            assignees=["assignee1"],
            milestone="v1.2.0",
        )

    except Exception as e:
        activity.logger.error(f"Failed to get PR details: {e}")
        raise


@activity.defn
async def get_diff_content(input: PullRequestInfo) -> DiffContent:
    """
    Retrieve the diff content for a pull request.

    Args:
        input: Pull request information

    Returns:
        DiffContent: The diff content and metadata
    """
    activity.logger.info(
        f"Getting diff for PR #{input.pr_number} in {input.repository}"
    )

    try:
        # Simulate API call
        await asyncio.sleep(1.0)

        # Mock diff data
        mock_files = [
            {
                "filename": "src/main.py",
                "status": "modified",
                "additions": 50,
                "deletions": 10,
                "patch": "@@ -1,20 +1,60 @@\n+ def new_function():\n+     pass\n",
            },
            {
                "filename": "tests/test_main.py",
                "status": "added",
                "additions": 100,
                "deletions": 0,
                "patch": "@@ -0,0 +1,100 @@\n+ import unittest\n",
            },
        ]

        return DiffContent(
            files=mock_files,
            total_additions=150,
            total_deletions=25,
            raw_diff="simulated diff content...",
        )

    except Exception as e:
        activity.logger.error(f"Failed to get diff content: {e}")
        raise


@activity.defn
async def post_review_comment(input: dict[str, Any]) -> bool:
    """
    Post a review comment to a pull request.

    Args:
        input: Dictionary containing PR info and review summary

    Returns:
        bool: True if comment was posted successfully
    """
    pr_info = input["pr_info"]
    input["review_summary"]

    activity.logger.info(f"Posting review comment for PR #{pr_info.pr_number}")

    try:
        # Simulate API call
        await asyncio.sleep(0.5)

        # In a real implementation, this would:
        # 1. Format the review summary as a markdown comment
        # 2. Post it to the PR via GitHub API
        # 3. Return success status

        activity.logger.info("Review comment posted successfully")
        return True

    except Exception as e:
        activity.logger.error(f"Failed to post review comment: {e}")
        raise
