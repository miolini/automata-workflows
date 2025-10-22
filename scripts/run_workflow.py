#!/usr/bin/env python3
"""
Run individual workflows using UV environment.

This script executes specific workflows with provided input data.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from temporalio.client import Client

from shared.config import config
from shared.models.llm import LLMInferenceRequest
from workflows.llm_inference.llm_inference_workflow import LLMInferenceWorkflow


async def run_llm_inference(input_data: dict):
    """Run LLM inference workflow."""
    # Connect to Temporal server
    temporal_config = config.get_temporal_client_config()
    client = await Client.connect(
        temporal_config["host"], namespace=temporal_config["namespace"]
    )

    # Create request from input data
    request = LLMInferenceRequest(**input_data)

    print("🤖 Running LLM Inference Workflow")
    print(f"Model: {request.model}")
    print(f"Messages: {len(request.messages)} messages")
    print(f"Task Queue: {config.TEMPORAL_TASK_QUEUE}")
    print("-" * 50)

    # Execute workflow
    result = await client.execute_workflow(
        LLMInferenceWorkflow.run,
        request,
        id=f"llm-inference-{asyncio.get_event_loop().time()}",
        task_queue=config.TEMPORAL_TASK_QUEUE,
    )

    print("✅ Workflow completed successfully!")
    if result.response:
        content = (
            result.response.choices[0].message.content
            if result.response.choices
            else "No content"
        )
        print(f"Response: {content[:200]}...")
        print(f"Tokens used: {result.response.usage.total_tokens}")
    else:
        print("No response received")
    print(f"Status: {result.status}")
    print(f"Execution time: {result.execution_time_ms}ms")

    return result


async def main():
    """Main entry point for running workflows."""
    parser = argparse.ArgumentParser(description="Run individual workflows")
    parser.add_argument(
        "--workflow", choices=["llm_inference"], required=True, help="Workflow to run"
    )
    parser.add_argument("--input", help="Input data as JSON string")
    parser.add_argument("--input-file", help="Input data from JSON file")

    args = parser.parse_args()

    # Validate input arguments
    if not args.input and not args.input_file:
        parser.error("Either --input or --input-file must be provided")

    # Parse input data
    if args.input_file:
        with open(args.input_file) as f:
            input_data = json.load(f)
    else:
        input_data = json.loads(args.input)

    print("🚀 Starting Workflow Execution")
    print("=" * 50)

    try:
        if args.workflow == "llm_inference":
            await run_llm_inference(input_data)
        else:
            print(f"❌ Unknown workflow: {args.workflow}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
