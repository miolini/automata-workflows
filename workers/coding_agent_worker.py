"""
Coding Agent Worker

Worker process for the CodingAgentWorkflow that handles autonomous coding tasks.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from temporalio.client import Client
from temporalio.worker import Worker

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.activities.coding_agent import (
    clone_repository,
    commit_changes,
    create_branch,
    list_directory_activity,
    notify_elixir_api,
    push_changes,
    read_file_activity,
    run_shell_command,
    send_nats_notification,
    store_task_activity,
    write_file_activity,
)
from workflows.coding_automation.coding_agent_workflow import CodingAgentWorkflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Run the Coding Agent worker."""
    # Get Temporal configuration from environment
    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    temporal_namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    task_queue = os.getenv("TEMPORAL_TASK_QUEUE_CODING_AGENT", "coding-agent")

    logger.info(f"Connecting to Temporal at {temporal_host}")
    logger.info(f"Namespace: {temporal_namespace}")
    logger.info(f"Task Queue: {task_queue}")

    # Create Temporal client
    client = await Client.connect(
        temporal_host,
        namespace=temporal_namespace,
    )

    logger.info("Connected to Temporal successfully")

    # Create worker with all activities
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[CodingAgentWorkflow],
        activities=[
            # Git operations (workflow-level)
            clone_repository,
            create_branch,
            commit_changes,
            push_changes,
            # Function calling tools (available to LLM agent)
            read_file_activity,
            write_file_activity,
            list_directory_activity,
            run_shell_command,
            # Notifications
            send_nats_notification,
            notify_elixir_api,
            # Database
            store_task_activity,
        ],
    )

    logger.info("Starting Coding Agent worker...")
    logger.info("Worker is ready to process coding tasks")

    # Run worker
    await worker.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)
