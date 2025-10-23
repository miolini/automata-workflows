"""
Query and monitor Coding Agent Workflows

This script provides utilities to query and monitor coding agent workflow executions.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta

from temporalio.client import Client

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def get_workflow_status(workflow_id: str):
    """Get the current status of a coding agent workflow."""
    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    client = await Client.connect(temporal_host)

    try:
        handle = client.get_workflow_handle(workflow_id)
        
        # Get workflow description
        description = await handle.describe()
        
        print("=" * 80)
        print(f"Workflow: {workflow_id}")
        print("=" * 80)
        print(f"Status: {description.status}")
        print(f"Start Time: {description.start_time}")
        print(f"Execution Time: {description.execution_time}")
        
        if description.close_time:
            print(f"Close Time: {description.close_time}")
            duration = description.close_time - description.start_time
            print(f"Duration: {duration}")
        
        # Try to get result if workflow is completed
        if description.status and str(description.status) == "COMPLETED":
            result = await handle.result()
            print("\nResult:")
            print(json.dumps(result, indent=2, default=str))
        
    except Exception as e:
        print(f"Error getting workflow status: {e}")


async def list_recent_workflows(hours: int = 24):
    """List recent coding agent workflows."""
    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    client = await Client.connect(temporal_host)

    query = "WorkflowType='CodingAgentWorkflow'"
    
    print("=" * 80)
    print(f"Recent Coding Agent Workflows (last {hours} hours)")
    print("=" * 80)
    print()

    workflows = client.list_workflows(query=query)
    
    count = 0
    async for workflow in workflows:
        count += 1
        print(f"{count}. Workflow ID: {workflow.id}")
        print(f"   Status: {workflow.status}")
        print(f"   Start Time: {workflow.start_time}")
        if workflow.close_time:
            duration = workflow.close_time - workflow.start_time
            print(f"   Duration: {duration}")
        print()


async def monitor_workflow(workflow_id: str, interval: int = 5):
    """Monitor a workflow in real-time."""
    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    client = await Client.connect(temporal_host)

    try:
        handle = client.get_workflow_handle(workflow_id)
        
        print("=" * 80)
        print(f"Monitoring Workflow: {workflow_id}")
        print("=" * 80)
        print("Press Ctrl+C to stop monitoring")
        print()

        while True:
            description = await handle.describe()
            
            status = str(description.status) if description.status else "UNKNOWN"
            execution_time = datetime.utcnow() - description.start_time
            
            print(f"[{datetime.utcnow().isoformat()}] Status: {status}, Runtime: {execution_time}")
            
            if status in ["COMPLETED", "FAILED", "CANCELED", "TERMINATED"]:
                print()
                print(f"Workflow {status}")
                
                if status == "COMPLETED":
                    result = await handle.result()
                    print("\nFinal Result:")
                    print(json.dumps(result, indent=2, default=str))
                
                break
            
            await asyncio.sleep(interval)
    
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    except Exception as e:
        print(f"Error monitoring workflow: {e}")


async def cancel_workflow(workflow_id: str):
    """Cancel a running workflow."""
    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    client = await Client.connect(temporal_host)

    try:
        handle = client.get_workflow_handle(workflow_id)
        await handle.cancel()
        print(f"Workflow {workflow_id} has been cancelled")
    except Exception as e:
        print(f"Error cancelling workflow: {e}")


async def main():
    """Main entry point for the query script."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/query_coding_agent_workflows.py status <workflow_id>")
        print("  python scripts/query_coding_agent_workflows.py list [hours]")
        print("  python scripts/query_coding_agent_workflows.py monitor <workflow_id> [interval]")
        print("  python scripts/query_coding_agent_workflows.py cancel <workflow_id>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "status":
        if len(sys.argv) < 3:
            print("Error: workflow_id required")
            sys.exit(1)
        await get_workflow_status(sys.argv[2])

    elif command == "list":
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        await list_recent_workflows(hours)

    elif command == "monitor":
        if len(sys.argv) < 3:
            print("Error: workflow_id required")
            sys.exit(1)
        workflow_id = sys.argv[2]
        interval = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        await monitor_workflow(workflow_id, interval)

    elif command == "cancel":
        if len(sys.argv) < 3:
            print("Error: workflow_id required")
            sys.exit(1)
        await cancel_workflow(sys.argv[2])

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
