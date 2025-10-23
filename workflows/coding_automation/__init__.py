"""
Coding Automation Workflows

This package contains workflows for automating software development processes
including code review, PR management, CI/CD orchestration, and documentation generation.
"""

__version__ = "0.1.0"

from .coding_agent_workflow import CodingAgentWorkflow
from .repository_indexing_workflow import RepositoryIndexingWorkflow

__all__ = [
    "CodingAgentWorkflow",
    "RepositoryIndexingWorkflow",
]

