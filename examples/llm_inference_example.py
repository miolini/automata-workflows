"""
LLM Inference Example

This example demonstrates how to use the LLM inference workflow with OpenRouter.
"""

import asyncio
from datetime import timedelta

from temporalio.client import Client

from shared.config import config
from shared.models.llm import (
    BatchInferenceRequest,
    ChatMessage,
    FunctionDefinition,
    FunctionParameter,
    InferenceParameters,
    LLMInferenceRequest,
    OpenRouterCredentials,
)


async def main():
    """Run LLM inference examples."""

    # Connect to Temporal server using configuration
    temporal_config = config.get_temporal_client_config()
    client = await Client.connect(
        temporal_config["host"], namespace=temporal_config["namespace"]
    )

    # Get OpenRouter API key from configuration
    try:
        config.validate_openrouter_config()
        credentials = OpenRouterCredentials(api_key=config.OPENROUTER_API_KEY)  # type: ignore
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("Please set your OpenRouter API key in your .env file:")
        print("OPENROUTER_API_KEY=your-api-key-here")
        return

    print("🤖 LLM Inference Examples")
    print("=" * 50)

    # Example 1: Simple chat completion
    print("\n1. Simple Chat Completion")
    print("-" * 30)

    simple_request = LLMInferenceRequest(
        model=config.OPENROUTER_MODEL,
        messages=[
            ChatMessage(role="system", content="You are a helpful assistant."),
            ChatMessage(role="user", content="What is the capital of France?"),
        ],
        credentials=credentials,
        parameters=InferenceParameters(temperature=0.7, max_tokens=100),
    )

    try:
        result = await client.execute_workflow(
            "LLMInferenceWorkflow",
            simple_request,
            id="simple-chat-example",
            task_queue=config.TEMPORAL_TASK_QUEUE,
            execution_timeout=timedelta(minutes=2),
        )

        if result.status == "completed":
            print("✅ Success!")
            print(f"   Model: {result.response.model}")
            print(f"   Response: {result.response.choices[0].message.content}")
            print(f"   Tokens used: {result.tokens_used}")
            print(f"   Execution time: {result.execution_time_ms}ms")
        else:
            print(f"❌ Failed: {result.error_message}")

    except Exception as e:
        print(f"❌ Error: {e}")

    # Example 2: Function calling
    print("\n2. Function Calling")
    print("-" * 20)

    function_request = LLMInferenceRequest(
        model=config.OPENROUTER_MODEL,
        messages=[
            ChatMessage(
                role="system",
                content="You are a helpful assistant with access to weather information.",
            ),
            ChatMessage(role="user", content="What's the weather like in New York?"),
        ],
        credentials=credentials,
        functions=[
            FunctionDefinition(
                name="get_weather",
                description="Get current weather information for a location",
                parameters=[
                    FunctionParameter(
                        name="location",
                        type="string",
                        description="City name, e.g., 'New York, NY'",
                        required=True,
                    ),
                    FunctionParameter(
                        name="unit",
                        type="string",
                        description="Temperature unit (celsius or fahrenheit)",
                        required=False,
                        enum=["celsius", "fahrenheit"],
                    ),
                ],
            )
        ],
        function_call="auto",
        parameters=InferenceParameters(temperature=0.1, max_tokens=150),
    )

    try:
        result = await client.execute_workflow(
            "LLMInferenceWorkflow",
            function_request,
            id="function-call-example",
            task_queue=config.TEMPORAL_TASK_QUEUE,
            execution_timeout=timedelta(minutes=2),
        )

        if result.status == "completed":
            print("✅ Success!")
            response_message = result.response.choices[0].message
            print(f"   Response: {response_message.content}")

            if response_message.function_call:
                print(f"   Function Call: {response_message.function_call}")

            print(f"   Tokens used: {result.tokens_used}")
        else:
            print(f"❌ Failed: {result.error_message}")

    except Exception as e:
        print(f"❌ Error: {e}")

    # Example 3: Model validation
    print("\n3. Model Validation")
    print("-" * 20)

    try:
        validation_result = await client.execute_workflow(
            "ModelValidationWorkflow",
            [credentials.model_dump(), config.OPENROUTER_MODEL],
            id="model-validation-example",
            task_queue=config.TEMPORAL_TASK_QUEUE,
            execution_timeout=timedelta(minutes=1),
        )

        if validation_result.get("valid"):
            print("✅ Model is valid!")
            model_info = validation_result.get("model_info", {})
            print(f"   Name: {model_info.get('name', 'Unknown')}")
            print(f"   Description: {model_info.get('description', 'No description')}")
        else:
            print(
                f"❌ Model validation failed: {validation_result.get('error', 'Unknown error')}"
            )

    except Exception as e:
        print(f"❌ Error: {e}")

    # Example 4: Batch inference
    print("\n4. Batch Inference")
    print("-" * 18)

    batch_requests = [
        LLMInferenceRequest(
            model=config.OPENROUTER_MODEL,
            messages=[
                ChatMessage(role="user", content="What is 2+2?"),
            ],
            credentials=credentials,
            parameters=InferenceParameters(max_tokens=50),
        ),
        LLMInferenceRequest(
            model=config.OPENROUTER_MODEL,
            messages=[
                ChatMessage(role="user", content="What is the capital of Spain?"),
            ],
            credentials=credentials,
            parameters=InferenceParameters(max_tokens=50),
        ),
    ]

    batch_request = BatchInferenceRequest(requests=batch_requests, max_concurrent=2)

    try:
        batch_result = await client.execute_workflow(
            "BatchLLMInferenceWorkflow",
            batch_request,
            id="batch-inference-example",
            task_queue=config.TEMPORAL_TASK_QUEUE,
            execution_timeout=timedelta(minutes=5),
        )

        print("✅ Batch completed!")
        print(f"   Total requests: {batch_result.total_requests}")
        print(f"   Successful: {batch_result.successful_requests}")
        print(f"   Failed: {batch_result.failed_requests}")
        print(f"   Total tokens: {batch_result.total_tokens_used}")
        print(f"   Execution time: {batch_result.total_execution_time_ms}ms")

        for i, result in enumerate(batch_result.results):
            if result.status == "completed":
                response = result.response.choices[0].message.content
                print(f"   Request {i+1}: {response[:50]}...")
            else:
                print(f"   Request {i+1}: Failed - {result.error_message}")

    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n🎉 All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
