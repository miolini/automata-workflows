#!/usr/bin/env python3
"""
Workflow API Server

FastAPI server for querying and managing Temporal workflows.
Provides REST API endpoints for listing, querying, and managing workflow executions.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.services.workflow_query import create_workflow_query_service

app = FastAPI(
    title="Automata Workflows API",
    description="REST API for querying and managing Temporal workflow executions",
    version="0.1.0",
)

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WorkflowListResponse(BaseModel):
    """Response model for workflow listing."""

    workflows: list[dict[str, Any]]
    count: int


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status."""

    workflow_id: str
    run_id: str
    workflow_type: str
    status: str
    start_time: str | None
    close_time: str | None
    execution_time: str | None
    task_queue: str
    history_length: int


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "service": "Automata Workflows API",
        "version": "0.1.0",
        "endpoints": {
            "list_all": "/api/workflows/list",
            "recent": "/api/workflows/recent",
            "running": "/api/workflows/running",
            "completed": "/api/workflows/completed",
            "failed": "/api/workflows/failed",
            "status": "/api/workflows/{workflow_id}/status",
            "result": "/api/workflows/{workflow_id}/result",
        },
    }


@app.get("/api/workflows/list", response_model=WorkflowListResponse)
async def list_workflows(
    workflow_type: Optional[str] = Query(None, description="Filter by workflow type"),
    status: Optional[str] = Query(None, description="Filter by status (RUNNING, COMPLETED, FAILED, etc.)"),
    max_results: int = Query(100, le=1000, description="Maximum number of results"),
):
    """
    List workflow executions with optional filtering.

    Args:
        workflow_type: Optional workflow type filter (e.g., "LLMInferenceWorkflow")
        status: Optional status filter (RUNNING, COMPLETED, FAILED, etc.)
        max_results: Maximum number of results to return (default: 100, max: 1000)

    Returns:
        List of workflow executions with count
    """
    try:
        service = await create_workflow_query_service()
        workflows = await service.list_workflows(
            workflow_type=workflow_type, max_results=max_results
        )
        return WorkflowListResponse(workflows=workflows, count=len(workflows))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/recent", response_model=WorkflowListResponse)
async def list_recent_workflows(
    hours: int = Query(24, le=168, description="Number of hours to look back"),
    workflow_type: Optional[str] = Query(None, description="Filter by workflow type"),
    max_results: int = Query(100, le=1000, description="Maximum number of results"),
):
    """
    List recent workflow executions (last N hours).

    Args:
        hours: Number of hours to look back (default: 24, max: 168)
        workflow_type: Optional workflow type filter
        max_results: Maximum number of results to return

    Returns:
        List of recent workflow executions
    """
    try:
        service = await create_workflow_query_service()
        workflows = await service.list_recent_workflows(
            workflow_type=workflow_type, hours=hours, max_results=max_results
        )
        return WorkflowListResponse(workflows=workflows, count=len(workflows))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/running", response_model=WorkflowListResponse)
async def list_running_workflows(
    workflow_type: Optional[str] = Query(None, description="Filter by workflow type"),
    max_results: int = Query(100, le=1000, description="Maximum number of results"),
):
    """
    List currently running workflows.

    Args:
        workflow_type: Optional workflow type filter
        max_results: Maximum number of results to return

    Returns:
        List of running workflow executions
    """
    try:
        service = await create_workflow_query_service()
        workflows = await service.list_running_workflows(workflow_type=workflow_type, max_results=max_results)
        return WorkflowListResponse(workflows=workflows, count=len(workflows))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/completed", response_model=WorkflowListResponse)
async def list_completed_workflows(
    hours: int = Query(24, le=168, description="Number of hours to look back"),
    workflow_type: Optional[str] = Query(None, description="Filter by workflow type"),
    max_results: int = Query(100, le=1000, description="Maximum number of results"),
):
    """
    List recently completed workflows.

    Args:
        hours: Number of hours to look back
        workflow_type: Optional workflow type filter
        max_results: Maximum number of results to return

    Returns:
        List of completed workflow executions
    """
    try:
        service = await create_workflow_query_service()
        workflows = await service.list_completed_workflows(
            workflow_type=workflow_type, hours=hours, max_results=max_results
        )
        return WorkflowListResponse(workflows=workflows, count=len(workflows))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/failed", response_model=WorkflowListResponse)
async def list_failed_workflows(
    hours: int = Query(24, le=168, description="Number of hours to look back"),
    workflow_type: Optional[str] = Query(None, description="Filter by workflow type"),
    max_results: int = Query(100, le=1000, description="Maximum number of results"),
):
    """
    List recently failed workflows.

    Args:
        hours: Number of hours to look back
        workflow_type: Optional workflow type filter
        max_results: Maximum number of results to return

    Returns:
        List of failed workflow executions
    """
    try:
        service = await create_workflow_query_service()
        workflows = await service.list_failed_workflows(
            workflow_type=workflow_type, hours=hours, max_results=max_results
        )
        return WorkflowListResponse(workflows=workflows, count=len(workflows))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(workflow_id: str):
    """
    Get detailed status of a specific workflow execution.

    Args:
        workflow_id: The workflow ID to query

    Returns:
        Detailed workflow status information
    """
    try:
        service = await create_workflow_query_service()
        status = await service.get_workflow_status(workflow_id)
        return WorkflowStatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/{workflow_id}/result")
async def get_workflow_result(workflow_id: str):
    """
    Get the result of a completed workflow.

    Args:
        workflow_id: The workflow ID to query

    Returns:
        Workflow result if completed, error if still running or failed
    """
    try:
        service = await create_workflow_query_service()
        result = await service.get_workflow_result(workflow_id)
        return {"status": "completed", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/workflows/{workflow_id}/cancel")
async def cancel_workflow(workflow_id: str):
    """
    Cancel a running workflow.

    Args:
        workflow_id: The workflow ID to cancel

    Returns:
        Cancellation confirmation
    """
    try:
        service = await create_workflow_query_service()
        await service.cancel_workflow(workflow_id)
        return {"status": "cancelled", "workflow_id": workflow_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workflows/{workflow_id}/terminate")
async def terminate_workflow(workflow_id: str, reason: str = "Terminated by API request"):
    """
    Terminate a workflow execution.

    Args:
        workflow_id: The workflow ID to terminate
        reason: Reason for termination

    Returns:
        Termination confirmation
    """
    try:
        service = await create_workflow_query_service()
        await service.terminate_workflow(workflow_id, reason=reason)
        return {"status": "terminated", "workflow_id": workflow_id, "reason": reason}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


def main():
    """Run the API server."""
    print("🚀 Starting Automata Workflows API Server")
    print("=" * 80)
    print("API Documentation: http://localhost:8000/docs")
    print("OpenAPI Schema: http://localhost:8000/openapi.json")
    print("=" * 80)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
