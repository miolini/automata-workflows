"""
Workflow Query Service

Service for querying and managing workflow executions from Temporal database.
"""

from datetime import datetime, timedelta
from typing import Any

from temporalio.client import Client, WorkflowExecutionStatus, WorkflowHandle

from shared.config import config


class WorkflowQueryService:
    """Service for querying workflow executions."""

    def __init__(self, client: Client):
        """Initialize the workflow query service."""
        self.client = client

    async def list_workflows(
        self,
        workflow_type: str | None = None,
        status: WorkflowExecutionStatus | None = None,
        max_results: int = 100,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        List workflow executions with optional filtering.

        Args:
            workflow_type: Filter by workflow type (e.g., "LLMInferenceWorkflow")
            status: Filter by status (RUNNING, COMPLETED, FAILED, etc.)
            max_results: Maximum number of results to return
            start_time: Filter workflows started after this time
            end_time: Filter workflows started before this time

        Returns:
            List of workflow execution information dictionaries
        """
        # Build query string
        query_parts = []

        if workflow_type:
            query_parts.append(f'WorkflowType="{workflow_type}"')

        if status:
            query_parts.append(f"ExecutionStatus='{status.name}'")

        if start_time:
            start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S")
            query_parts.append(f'StartTime >= "{start_time_str}"')

        if end_time:
            end_time_str = end_time.strftime("%Y-%m-%dT%H:%M:%S")
            query_parts.append(f'StartTime <= "{end_time_str}"')

        query = " AND ".join(query_parts) if query_parts else ""

        # Query workflows
        workflows = []
        async for workflow in self.client.list_workflows(query):
            workflow_info = {
                "workflow_id": workflow.id,
                "run_id": workflow.run_id,
                "workflow_type": workflow.workflow_type,
                "status": workflow.status.name if workflow.status else "UNKNOWN",
                "start_time": workflow.start_time.isoformat() if workflow.start_time else None,
                "close_time": workflow.close_time.isoformat() if workflow.close_time else None,
                "execution_time": workflow.execution_time.isoformat() if workflow.execution_time else None,
                "task_queue": workflow.task_queue,
                "history_length": workflow.history_length,
            }
            workflows.append(workflow_info)

            if len(workflows) >= max_results:
                break

        return workflows

    async def get_workflow_handle(self, workflow_id: str, run_id: str | None = None) -> WorkflowHandle:
        """
        Get a handle to an existing workflow execution.

        Args:
            workflow_id: The workflow ID
            run_id: Optional run ID (uses latest if not specified)

        Returns:
            WorkflowHandle for the workflow execution
        """
        return self.client.get_workflow_handle(workflow_id, run_id=run_id)

    async def get_workflow_status(self, workflow_id: str, run_id: str | None = None) -> dict[str, Any]:
        """
        Get detailed status of a workflow execution.

        Args:
            workflow_id: The workflow ID
            run_id: Optional run ID (uses latest if not specified)

        Returns:
            Dictionary with workflow status and details
        """
        handle = await self.get_workflow_handle(workflow_id, run_id)
        describe = await handle.describe()

        return {
            "workflow_id": describe.id,
            "run_id": describe.run_id,
            "workflow_type": describe.workflow_type,
            "status": describe.status.name if describe.status else "UNKNOWN",
            "start_time": describe.start_time.isoformat() if describe.start_time else None,
            "close_time": describe.close_time.isoformat() if describe.close_time else None,
            "execution_time": describe.execution_time.isoformat() if describe.execution_time else None,
            "task_queue": describe.task_queue,
            "history_length": describe.history_length,
            "parent_id": describe.parent_id,
            "parent_run_id": describe.parent_run_id,
        }

    async def get_workflow_result(self, workflow_id: str, run_id: str | None = None) -> Any:
        """
        Get the result of a completed workflow.

        Args:
            workflow_id: The workflow ID
            run_id: Optional run ID (uses latest if not specified)

        Returns:
            The workflow result

        Raises:
            WorkflowFailureError: If the workflow failed
            RuntimeError: If the workflow is still running
        """
        handle = await self.get_workflow_handle(workflow_id, run_id)
        return await handle.result()

    async def cancel_workflow(self, workflow_id: str, run_id: str | None = None) -> None:
        """
        Cancel a running workflow.

        Args:
            workflow_id: The workflow ID
            run_id: Optional run ID (uses latest if not specified)
        """
        handle = await self.get_workflow_handle(workflow_id, run_id)
        await handle.cancel()

    async def terminate_workflow(
        self, workflow_id: str, reason: str = "Terminated by user", run_id: str | None = None
    ) -> None:
        """
        Terminate a workflow execution.

        Args:
            workflow_id: The workflow ID
            reason: Reason for termination
            run_id: Optional run ID (uses latest if not specified)
        """
        handle = await self.get_workflow_handle(workflow_id, run_id)
        await handle.terminate(reason=reason)

    async def list_recent_workflows(
        self, workflow_type: str | None = None, hours: int = 24, max_results: int = 100
    ) -> list[dict[str, Any]]:
        """
        List recent workflow executions (last N hours).

        Args:
            workflow_type: Optional filter by workflow type
            hours: Number of hours to look back
            max_results: Maximum number of results

        Returns:
            List of recent workflow executions
        """
        start_time = datetime.utcnow() - timedelta(hours=hours)
        return await self.list_workflows(
            workflow_type=workflow_type, start_time=start_time, max_results=max_results
        )

    async def list_running_workflows(
        self, workflow_type: str | None = None, max_results: int = 100
    ) -> list[dict[str, Any]]:
        """
        List currently running workflows.

        Args:
            workflow_type: Optional filter by workflow type
            max_results: Maximum number of results

        Returns:
            List of running workflow executions
        """
        return await self.list_workflows(
            workflow_type=workflow_type, status=WorkflowExecutionStatus.RUNNING, max_results=max_results
        )

    async def list_completed_workflows(
        self, workflow_type: str | None = None, hours: int = 24, max_results: int = 100
    ) -> list[dict[str, Any]]:
        """
        List recently completed workflows.

        Args:
            workflow_type: Optional filter by workflow type
            hours: Number of hours to look back
            max_results: Maximum number of results

        Returns:
            List of completed workflow executions
        """
        start_time = datetime.utcnow() - timedelta(hours=hours)
        return await self.list_workflows(
            workflow_type=workflow_type,
            status=WorkflowExecutionStatus.COMPLETED,
            start_time=start_time,
            max_results=max_results,
        )

    async def list_failed_workflows(
        self, workflow_type: str | None = None, hours: int = 24, max_results: int = 100
    ) -> list[dict[str, Any]]:
        """
        List recently failed workflows.

        Args:
            workflow_type: Optional filter by workflow type
            hours: Number of hours to look back
            max_results: Maximum number of results

        Returns:
            List of failed workflow executions
        """
        start_time = datetime.utcnow() - timedelta(hours=hours)
        return await self.list_workflows(
            workflow_type=workflow_type,
            status=WorkflowExecutionStatus.FAILED,
            start_time=start_time,
            max_results=max_results,
        )


async def create_workflow_query_service() -> WorkflowQueryService:
    """
    Create a workflow query service with default Temporal connection.

    Returns:
        WorkflowQueryService instance
    """
    temporal_config = config.get_temporal_client_config()
    client = await Client.connect(temporal_config["host"], namespace=temporal_config["namespace"])
    return WorkflowQueryService(client)
