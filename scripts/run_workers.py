#!/usr/bin/env python3
"""
Run workflow workers using UV environment.

This script starts workflow workers for the specified workflows.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from workers.llm_inference_worker import run_llm_inference_worker


async def main():
    """Main entry point for running workers."""
    parser = argparse.ArgumentParser(description="Run workflow workers")
    parser.add_argument(
        "--workflow",
        choices=["llm_inference", "all"],
        default="all",
        help="Specific workflow worker to run (default: all)",
    )
    parser.add_argument("--task-queue", default=None, help="Override task queue name")

    args = parser.parse_args()

    print("🚀 Starting Automata Workflows Workers")
    print("=" * 50)

    if args.workflow == "llm_inference" or args.workflow == "all":
        print("🤖 Starting LLM Inference Worker...")
        try:
            await run_llm_inference_worker(task_queue=args.task_queue)
        except KeyboardInterrupt:
            print("\n⏹️  LLM Inference Worker stopped by user")
        except Exception as e:
            print(f"❌ LLM Inference Worker failed: {e}")
            if args.workflow != "all":
                sys.exit(1)

    if args.workflow == "all":
        print("\n✅ All workers started successfully")
        print("Press Ctrl+C to stop all workers")

        try:
            # Keep running until interrupted
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n⏹️  All workers stopped by user")


if __name__ == "__main__":
    asyncio.run(main())
