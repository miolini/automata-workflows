"""
Repository Indexing Worker

This worker runs the repository indexing workflow that fetches and indexes repositories.
"""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from shared.config import config
from workflows.coding_automation.repository_indexing_workflow import (
    RepositoryIndexingWorkflow,
    cleanup_repository,
    clone_repository,
    index_repository,
    save_to_database,
)


async def run_repository_indexing_worker(task_queue: str | None = None):
    """Run the repository indexing worker."""

    # Connect to Temporal server using configuration
    temporal_config = config.get_temporal_client_config()
    client = await Client.connect(
        temporal_config["host"], namespace=temporal_config["namespace"]
    )

    # Use provided task queue or default from config
    queue = task_queue or config.TEMPORAL_TASK_QUEUE

    # Create worker with workflows and activities
    worker = Worker(
        client,
        task_queue=queue,
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
    print(f"Temporal host: {config.TEMPORAL_HOST}")
    print(f"Temporal namespace: {config.TEMPORAL_NAMESPACE}")
    print(f"Task queue: {queue}")
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


async def main():
    """Main entry point when run directly."""
    await run_repository_indexing_worker()


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(main())
