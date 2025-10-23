"""
LLM Inference Worker

This worker runs LLM inference workflows using OpenRouter API.
"""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from shared.activities.llm import (
    chat_completion,
    estimate_tokens,
    format_function_result,
    get_available_models,
    notify_completion,
    validate_model,
)
from shared.config import config
from workflows.llm_inference.llm_inference_workflow import LLMInferenceWorkflow


async def run_llm_inference_worker(task_queue: str | None = None):
    """Run the LLM inference worker."""

    # Connect to Temporal server using configuration
    temporal_config = config.get_temporal_client_config()
    client = await Client.connect(
        temporal_config["host"], namespace=temporal_config["namespace"]
    )

    # Use provided task queue or default to llm-inference
    queue = task_queue or "llm-inference"

    # Create worker with workflows and activities
    worker = Worker(
        client,
        task_queue=queue,
        workflows=[
            LLMInferenceWorkflow,
        ],
        activities=[
            chat_completion,
            validate_model,
            get_available_models,
            estimate_tokens,
            format_function_result,
            notify_completion,
        ],
        max_concurrent_activities=100,  # Allow concurrent LLM requests
    )

    print("Starting LLM inference worker...")
    print(f"Temporal host: {config.TEMPORAL_HOST}")
    print(f"Temporal namespace: {config.TEMPORAL_NAMESPACE}")
    print(f"Task queue: {queue}")
    print("Workflows:")
    print("  - LLMInferenceWorkflow")
    print("Activities:")
    print("  - chat_completion")
    print("  - validate_model")
    print("  - get_available_models")
    print("  - estimate_tokens")
    print("  - format_function_result")
    print("  - notify_completion")
    print()
    print("Press Ctrl+C to stop the worker")

    try:
        await worker.run()
    except KeyboardInterrupt:
        print("\nShutting down worker...")
        await worker.shutdown()


async def main():
    """Main entry point when run directly."""
    await run_llm_inference_worker()


if __name__ == "__main__":
    asyncio.run(main())
