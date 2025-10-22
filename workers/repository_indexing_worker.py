"""
Repository Indexing Worker

This worker runs the repository indexing workflow that fetches and indexes repositories.
"""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from workflows.coding_automation.repository_indexing_workflow import (
    RepositoryIndexingWorkflow,
    cleanup_repository,
    clone_repository,
    index_repository,
    save_to_database,
)


async def main():
    """Run the repository indexing worker."""

    # Connect to Temporal server
    client = await Client.connect("localhost:7233")

    # Create worker with workflows and activities
    worker = Worker(
        client,
        task_queue="repository-indexing-task-queue",
        workflows=[
            RepositoryIndexingWorkflow,
        ],
        activities=[
            clone_repository,
            index_repository,
            save_to_database,
            cleanup_repository,
        ],
        max_concurrent_activities=5,  # Limit concurrent activities
    )

    print("Starting repository indexing worker...")
    print("Task queue: repository-indexing-task-queue")
    print("Workflows:")
    print("  - RepositoryIndexingWorkflow")
    print("Activities:")
    print("  - clone_repository")
    print("  - index_repository")
    print("  - save_to_database")
    print("  - cleanup_repository")
    print()
    print("Press Ctrl+C to stop the worker")

    try:
        await worker.run()
    except KeyboardInterrupt:
        print("\nShutting down worker...")
        await worker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
