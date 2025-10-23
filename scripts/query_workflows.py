#!/usr/bin/env python3
"""
Query Workflows Script

This script demonstrates how to query and list workflow executions from Temporal.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from temporalio.client import WorkflowExecutionStatus

from shared.services.workflow_query import create_workflow_query_service


async def list_all_workflows(max_results: int = 100):
    """List all recent workflow executions."""
    service = await create_workflow_query_service()
    workflows = await service.list_recent_workflows(max_results=max_results)

    print(f"📋 Found {len(workflows)} workflow executions")
    print("=" * 80)

    for workflow in workflows:
        print(f"\n🔹 Workflow ID: {workflow['workflow_id']}")
        print(f"   Type: {workflow['workflow_type']}")
        print(f"   Status: {workflow['status']}")
        print(f"   Started: {workflow['start_time']}")
        if workflow['close_time']:
            print(f"   Completed: {workflow['close_time']}")
        print(f"   Task Queue: {workflow['task_queue']}")
        print(f"   History Length: {workflow['history_length']}")


async def list_workflows_by_type(workflow_type: str, max_results: int = 100):
    """List workflows filtered by type."""
    service = await create_workflow_query_service()
    workflows = await service.list_recent_workflows(workflow_type=workflow_type, max_results=max_results)

    print(f"📋 Found {len(workflows)} {workflow_type} executions")
    print("=" * 80)

    for workflow in workflows:
        print(f"\n🔹 {workflow['workflow_id']}")
        print(f"   Status: {workflow['status']}")
        print(f"   Started: {workflow['start_time']}")
        if workflow['close_time']:
            print(f"   Completed: {workflow['close_time']}")


async def list_running_workflows(workflow_type: str | None = None):
    """List currently running workflows."""
    service = await create_workflow_query_service()
    workflows = await service.list_running_workflows(workflow_type=workflow_type)

    print(f"🏃 Found {len(workflows)} running workflows")
    print("=" * 80)

    for workflow in workflows:
        print(f"\n🔹 {workflow['workflow_id']}")
        print(f"   Type: {workflow['workflow_type']}")
        print(f"   Started: {workflow['start_time']}")
        print(f"   Task Queue: {workflow['task_queue']}")


async def list_completed_workflows(workflow_type: str | None = None, hours: int = 24):
    """List completed workflows."""
    service = await create_workflow_query_service()
    workflows = await service.list_completed_workflows(workflow_type=workflow_type, hours=hours)

    print(f"✅ Found {len(workflows)} completed workflows (last {hours} hours)")
    print("=" * 80)

    for workflow in workflows:
        print(f"\n🔹 {workflow['workflow_id']}")
        print(f"   Type: {workflow['workflow_type']}")
        print(f"   Started: {workflow['start_time']}")
        print(f"   Completed: {workflow['close_time']}")


async def list_failed_workflows(workflow_type: str | None = None, hours: int = 24):
    """List failed workflows."""
    service = await create_workflow_query_service()
    workflows = await service.list_failed_workflows(workflow_type=workflow_type, hours=hours)

    print(f"❌ Found {len(workflows)} failed workflows (last {hours} hours)")
    print("=" * 80)

    for workflow in workflows:
        print(f"\n🔹 {workflow['workflow_id']}")
        print(f"   Type: {workflow['workflow_type']}")
        print(f"   Started: {workflow['start_time']}")
        if workflow['close_time']:
            print(f"   Failed: {workflow['close_time']}")


async def get_workflow_status(workflow_id: str):
    """Get detailed status of a specific workflow."""
    service = await create_workflow_query_service()
    status = await service.get_workflow_status(workflow_id)

    print(f"📊 Workflow Status: {workflow_id}")
    print("=" * 80)
    print(json.dumps(status, indent=2))


async def get_workflow_result(workflow_id: str):
    """Get the result of a completed workflow."""
    service = await create_workflow_query_service()

    try:
        result = await service.get_workflow_result(workflow_id)
        print(f"✅ Workflow Result: {workflow_id}")
        print("=" * 80)
        print(json.dumps(result, indent=2, default=str))
    except Exception as e:
        print(f"❌ Error getting workflow result: {e}")


async def cancel_workflow(workflow_id: str):
    """Cancel a running workflow."""
    service = await create_workflow_query_service()

    try:
        await service.cancel_workflow(workflow_id)
        print(f"✅ Workflow cancelled: {workflow_id}")
    except Exception as e:
        print(f"❌ Error cancelling workflow: {e}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Query workflow executions")
    parser.add_argument("command", choices=[
        "list", "list-type", "running", "completed", "failed", 
        "status", "result", "cancel"
    ], help="Command to execute")
    parser.add_argument("--workflow-id", help="Workflow ID for status/result/cancel commands")
    parser.add_argument("--workflow-type", help="Filter by workflow type")
    parser.add_argument("--max-results", type=int, default=100, help="Maximum results to return")
    parser.add_argument("--hours", type=int, default=24, help="Number of hours to look back")

    args = parser.parse_args()

    print("🔍 Workflow Query Tool")
    print("=" * 80)

    try:
        if args.command == "list":
            await list_all_workflows(max_results=args.max_results)
        elif args.command == "list-type":
            if not args.workflow_type:
                parser.error("--workflow-type is required for list-type command")
            await list_workflows_by_type(args.workflow_type, max_results=args.max_results)
        elif args.command == "running":
            await list_running_workflows(workflow_type=args.workflow_type)
        elif args.command == "completed":
            await list_completed_workflows(workflow_type=args.workflow_type, hours=args.hours)
        elif args.command == "failed":
            await list_failed_workflows(workflow_type=args.workflow_type, hours=args.hours)
        elif args.command == "status":
            if not args.workflow_id:
                parser.error("--workflow-id is required for status command")
            await get_workflow_status(args.workflow_id)
        elif args.command == "result":
            if not args.workflow_id:
                parser.error("--workflow-id is required for result command")
            await get_workflow_result(args.workflow_id)
        elif args.command == "cancel":
            if not args.workflow_id:
                parser.error("--workflow-id is required for cancel command")
            await cancel_workflow(args.workflow_id)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
