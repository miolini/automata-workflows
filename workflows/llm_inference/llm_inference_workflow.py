"""
LLM Inference Workflow

This workflow provides reliable LLM inference using OpenRouter with support for
various models, function calling, and comprehensive error handling.
"""

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

# Import only the models, not the activities (to avoid sandbox issues)
from shared.models.llm import (
    BatchInferenceRequest,
    BatchInferenceResult,
    LLMInferenceRequest,
    LLMInferenceResult,
)


@workflow.defn
class LLMInferenceWorkflow:
    """Reliable LLM inference workflow using OpenRouter."""

    @workflow.run
    async def run(self, request: LLMInferenceRequest) -> LLMInferenceResult:
        """
        Run LLM inference with comprehensive error handling and retry logic.

        Args:
            request: LLM inference request with model, messages, and parameters

        Returns:
            LLMInferenceResult: Complete inference result with response and metadata
        """
        workflow.logger.info(f"Starting LLM inference with model: {request.model}")

        try:
            # Step 1: Validate model availability
            workflow.logger.info("Step 1: Validating model availability")
            validation_result = await workflow.execute_activity(
                "validate_model",
                args=[request.credentials.model_dump() if request.credentials else None, request.model],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                    backoff_coefficient=2.0,
                    maximum_attempts=10,
                ),
            )

            if not validation_result["valid"]:
                error_msg = f"Model validation failed: {validation_result.get('error', 'Unknown error')}"
                workflow.logger.error(error_msg)

                return LLMInferenceResult(
                    request=request,
                    response=None,
                    status="failed",
                    error_message=error_msg,
                    execution_time_ms=0,
                    tokens_used=0,
                )

            workflow.logger.info(
                f"Model validation successful: {validation_result.get('model_info', {}).get('name', request.model)}"
            )

            # Step 2: Estimate tokens for monitoring
            workflow.logger.info("Step 2: Estimating token usage")
            total_text = " ".join([msg.content for msg in request.messages])
            token_estimate = await workflow.execute_activity(
                "estimate_tokens",
                args=[request],
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(minutes=1),
                    backoff_coefficient=2.0,
                    maximum_attempts=3
                )
            )

            estimated_tokens = token_estimate.get("estimated_tokens", 0)
            workflow.logger.info(f"Estimated input tokens: {estimated_tokens}")

            # Step 3: Perform chat completion
            workflow.logger.info("Step 3: Performing chat completion")
            inference_result: Any = await workflow.execute_activity(
                "chat_completion",
                args=[request],
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1.2),
                    maximum_interval=timedelta(minutes=2),
                    backoff_coefficient=2.0,
                    maximum_attempts=10
                )
            )

            # Step 4: Handle function calls if present
            if (
                isinstance(inference_result, dict)
                and inference_result.get("response")
                and inference_result["response"].get("choices")
                and inference_result["response"]["choices"][0]["message"].get("function_call")
            ):

                workflow.logger.info("Step 4: Function call detected in response")
                function_call = inference_result["response"]["choices"][0]["message"]["function_call"]

                # Format function result for logging
                formatted_result = await workflow.execute_activity(
                    "format_function_result",
                    args=[function_call.get("name", "unknown"), function_call],
                    start_to_close_timeout=timedelta(seconds=10),
                )

                workflow.logger.info(f"Function call result: {formatted_result}")

            # Handle both object and dict formats
            tokens_used = inference_result.tokens_used if hasattr(inference_result, 'tokens_used') else inference_result.get('tokens_used', 0)
            execution_time = inference_result.execution_time_ms if hasattr(inference_result, 'execution_time_ms') else inference_result.get('execution_time_ms', 0)
            status = inference_result.status if hasattr(inference_result, 'status') else inference_result.get('status', 'unknown')
            
            workflow.logger.info(
                f"LLM inference completed successfully. "
                f"Status: {status}, "
                f"Tokens used: {tokens_used}, "
                f"Execution time: {execution_time}ms"
            )
            
            # Convert dict to LLMInferenceResult if needed
            if isinstance(inference_result, dict):
                result = LLMInferenceResult(
                    request=request,
                    response=inference_result.get("response"),
                    status=status,
                    error_message=inference_result.get("error_message"),
                    execution_time_ms=execution_time,
                    tokens_used=tokens_used,
                    finish_reason=inference_result.get("finish_reason")
                )
            else:
                result = inference_result
            
            # Step 5: Notify Elixir API about completion
            try:
                workflow.logger.info("Step 5: Notifying Elixir API about completion")
                notification_result = await workflow.execute_activity(
                    "notify_completion",
                    args=[workflow.info().workflow_id, result.model_dump()],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=1),
                        maximum_interval=timedelta(seconds=10),
                        backoff_coefficient=2.0,
                        maximum_attempts=3,
                    ),
                )
                
                if notification_result.get("success"):
                    workflow.logger.info("Successfully notified Elixir API")
                else:
                    workflow.logger.warning(f"Failed to notify Elixir API: {notification_result.get('error')}")
            except Exception as notify_error:
                # Don't fail the workflow if notification fails
                workflow.logger.warning(f"Notification to Elixir API failed (non-fatal): {notify_error}")
            
            return result

        except Exception as e:
            workflow.logger.error(f"LLM inference workflow failed: {e}")

            # Create error result
            return LLMInferenceResult(
                request=request,
                response=None,
                status="failed",
                error_message=str(e),
                execution_time_ms=0,
                tokens_used=0,
            )


@workflow.defn
class BatchLLMInferenceWorkflow:
    """Batch LLM inference workflow for processing multiple requests."""

    @workflow.run
    async def run(self, batch_request: BatchInferenceRequest) -> BatchInferenceResult:
        """
        Run batch LLM inference with controlled concurrency.

        Args:
            batch_request: Batch inference request with multiple requests

        Returns:
            BatchInferenceResult: Complete batch processing results
        """
        workflow.logger.info(
            f"Starting batch LLM inference for {len(batch_request.requests)} requests"
        )

        start_timestamp = workflow.time()
        results = []

        # Process requests in batches to control concurrency
        max_concurrent = batch_request.max_concurrent
        total_requests = len(batch_request.requests)

        for i in range(0, total_requests, max_concurrent):
            batch = batch_request.requests[i : i + max_concurrent]
            workflow.logger.info(
                f"Processing batch {i//max_concurrent + 1}: {len(batch)} requests"
            )

            # Execute current batch concurrently
            batch_tasks = []
            for j, request in enumerate(batch):
                task_id = f"batch-inference-{i+j}-{request.model[:20]}"

                task = workflow.execute_child_workflow(
                    "LLMInferenceWorkflow",
                    request,
                    id=task_id,
                    execution_timeout=timedelta(minutes=10),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=5),
                        maximum_interval=timedelta(minutes=1),
                        backoff_coefficient=2.0,
                        maximum_attempts=2,
                    ),
                )
                batch_tasks.append(task)

            # Wait for current batch to complete
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Process batch results
            for k, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    # Handle failed workflow
                    error_result = LLMInferenceResult(
                        request=batch[k],
                        response=None,
                        status="failed",
                        error_message=str(result),
                        execution_time_ms=0,
                        tokens_used=0,
                    )
                    results.append(error_result)
                    workflow.logger.error(f"Request {i+k} failed: {result}")
                else:
                    results.append(result)
                    workflow.logger.info(f"Request {i+k} completed successfully")

        # Calculate summary statistics
        successful_requests = sum(1 for r in results if r.status == "completed")
        failed_requests = len(results) - successful_requests
        total_tokens_used = sum(r.tokens_used for r in results)

        end_timestamp = workflow.time()
        total_execution_time_ms = int((end_timestamp - start_timestamp) * 1000)

        batch_result = BatchInferenceResult(
            results=results,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            total_tokens_used=total_tokens_used,
            total_execution_time_ms=total_execution_time_ms,
        )

        workflow.logger.info(
            f"Batch LLM inference completed. "
            f"Total: {total_requests}, "
            f"Successful: {successful_requests}, "
            f"Failed: {failed_requests}, "
            f"Total tokens: {total_tokens_used}, "
            f"Execution time: {total_execution_time_ms}ms"
        )

        return batch_result


@workflow.defn
class ModelValidationWorkflow:
    """Workflow for validating model availability and getting model information."""

    @workflow.run
    async def run(
        self, credentials: dict[str, Any], model: str | None = None
    ) -> dict[str, Any]:
        """
        Validate model or get all available models.

        Args:
            credentials: OpenRouter credentials
            model: Specific model to validate (optional)

        Returns:
            Dict with validation results or available models
        """
        workflow.logger.info(
            f"Starting model validation workflow for model: {model or 'all models'}"
        )

        try:
            if model:
                # Validate specific model
                validation_result = await workflow.execute_activity(
                    "validate_model",
                    args=[credentials, model],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=1), maximum_attempts=3
                    ),
                )

                workflow.logger.info(
                    f"Model validation completed for {model}: {validation_result['valid']}"
                )
                return validation_result
            else:
                # Get all available models
                models_result = await workflow.execute_activity(
                    "get_available_models",
                    args=[credentials],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=1), maximum_attempts=3
                    ),
                )

                workflow.logger.info(
                    f"Retrieved {models_result.get('total_count', 0)} available models"
                )
                return models_result

        except Exception as e:
            workflow.logger.error(f"Model validation workflow failed: {e}")
            return {"success": False, "error": str(e), "valid": False, "models": []}
