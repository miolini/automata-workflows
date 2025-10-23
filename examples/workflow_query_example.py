"""
Example: Using Workflow Query Service

This example demonstrates how to query and manage workflow executions
programmatically using the WorkflowQueryService.
"""

import asyncio
from datetime import datetime

from shared.services.workflow_query import create_workflow_query_service


async def example_list_all_workflows():
    """Example: List all recent workflows."""
    print("\n1. Listing all recent workflows")
    print("=" * 80)

    service = await create_workflow_query_service()
    workflows = await service.list_recent_workflows(hours=24, max_results=10)

    for workflow in workflows:
        print(f"  {workflow['workflow_id']}")
        print(f"    Type: {workflow['workflow_type']}")
        print(f"    Status: {workflow['status']}")
        print(f"    Started: {workflow['start_time']}")
        print()


async def example_list_by_type():
    """Example: List workflows filtered by type."""
    print("\n2. Listing LLM inference workflows")
    print("=" * 80)

    service = await create_workflow_query_service()
    workflows = await service.list_recent_workflows(
        workflow_type="LLMInferenceWorkflow", hours=48, max_results=10
    )

    print(f"Found {len(workflows)} LLM inference workflows\n")

    for workflow in workflows:
        print(f"  {workflow['workflow_id']} - {workflow['status']}")


async def example_running_workflows():
    """Example: List currently running workflows."""
    print("\n3. Listing running workflows")
    print("=" * 80)

    service = await create_workflow_query_service()
    workflows = await service.list_running_workflows()

    print(f"Found {len(workflows)} running workflows\n")

    for workflow in workflows:
        print(f"  {workflow['workflow_id']}")
        print(f"    Type: {workflow['workflow_type']}")
        print(f"    Started: {workflow['start_time']}")
        print()


async def example_workflow_status():
    """Example: Get status of a specific workflow."""
    print("\n4. Getting workflow status")
    print("=" * 80)

    service = await create_workflow_query_service()

    # First, get a workflow ID from recent workflows
    workflows = await service.list_recent_workflows(max_results=1)

    if not workflows:
        print("No workflows found")
        return

    workflow_id = workflows[0]["workflow_id"]
    print(f"Checking status of: {workflow_id}\n")

    status = await service.get_workflow_status(workflow_id)

    print(f"  Workflow ID: {status['workflow_id']}")
    print(f"  Run ID: {status['run_id']}")
    print(f"  Type: {status['workflow_type']}")
    print(f"  Status: {status['status']}")
    print(f"  Started: {status['start_time']}")
    print(f"  Task Queue: {status['task_queue']}")
    print(f"  History Length: {status['history_length']}")


async def example_completed_workflows():
    """Example: List completed workflows."""
    print("\n5. Listing completed workflows")
    print("=" * 80)

    service = await create_workflow_query_service()
    workflows = await service.list_completed_workflows(hours=24, max_results=10)

    print(f"Found {len(workflows)} completed workflows\n")

    for workflow in workflows:
        print(f"  {workflow['workflow_id']}")
        print(f"    Type: {workflow['workflow_type']}")
        print(f"    Started: {workflow['start_time']}")
        print(f"    Completed: {workflow['close_time']}")
        print()


async def example_failed_workflows():
    """Example: List failed workflows."""
    print("\n6. Listing failed workflows")
    print("=" * 80)

    service = await create_workflow_query_service()
    workflows = await service.list_failed_workflows(hours=24, max_results=10)

    print(f"Found {len(workflows)} failed workflows\n")

    for workflow in workflows:
        print(f"  {workflow['workflow_id']}")
        print(f"    Type: {workflow['workflow_type']}")
        print(f"    Failed: {workflow['close_time']}")
        print()


async def example_workflow_result():
    """Example: Get result of a completed workflow."""
    print("\n7. Getting workflow result")
    print("=" * 80)

    service = await create_workflow_query_service()

    # Get a completed workflow
    workflows = await service.list_completed_workflows(max_results=1)

    if not workflows:
        print("No completed workflows found")
        return

    workflow_id = workflows[0]["workflow_id"]
    print(f"Getting result of: {workflow_id}\n")

    try:
        result = await service.get_workflow_result(workflow_id)
        print("Result:")
        print(result)
    except Exception as e:
        print(f"Error getting result: {e}")


async def example_page_reload_simulation():
    """Example: Simulate loading workflows on page reload."""
    print("\n8. Simulating page reload - loading user's workflows")
    print("=" * 80)

    service = await create_workflow_query_service()

    # Load recent workflows (what a user would see on page load)
    workflows = await service.list_recent_workflows(
        workflow_type="LLMInferenceWorkflow", hours=24, max_results=50
    )

    print(f"Page loaded: Found {len(workflows)} workflows\n")

    # Separate by status
    running = [w for w in workflows if w["status"] == "RUNNING"]
    completed = [w for w in workflows if w["status"] == "COMPLETED"]
    failed = [w for w in workflows if w["status"] == "FAILED"]

    print(f"  Running: {len(running)}")
    print(f"  Completed: {len(completed)}")
    print(f"  Failed: {len(failed)}")
    print()

    # For running workflows, you would start polling their status
    if running:
        print("Would start polling these running workflows:")
        for workflow in running[:3]:  # Show first 3
            print(f"  - {workflow['workflow_id']}")


async def main():
    """Run all examples."""
    print("=" * 80)
    print("Workflow Query Service Examples")
    print("=" * 80)

    try:
        await example_list_all_workflows()
        await example_list_by_type()
        await example_running_workflows()
        await example_workflow_status()
        await example_completed_workflows()
        await example_failed_workflows()
        # await example_workflow_result()  # Uncomment if you have completed workflows
        await example_page_reload_simulation()

        print("\n" + "=" * 80)
        print("✅ All examples completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
