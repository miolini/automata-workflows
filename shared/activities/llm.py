"""
LLM and OpenRouter integration activities for Automata Workflows
"""

import json
import time
from typing import Any

import httpx
import structlog
from temporalio import activity

from shared.models.llm import (
    ChatMessage,
    Choice,
    FunctionDefinition,
    InferenceParameters,
    LLMInferenceRequest,
    LLMInferenceResponse,
    LLMInferenceResult,
    UsageInfo,
)

logger = structlog.get_logger(__name__)


class OpenRouterClient:
    """OpenRouter API client for LLM inference."""

    def __init__(self, credentials: dict[str, Any]):
        self.api_key = credentials["api_key"]
        self.base_url = credentials.get("base_url", "https://openrouter.ai/api/v1")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/sentientwave/automata-workflows",
            "X-Title": "Automata Workflows",
        }

    async def _make_request(
        self, endpoint: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Make an authenticated request to OpenRouter API."""
        url = f"{self.base_url}/{endpoint}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=data, headers=self.headers)
            response.raise_for_status()
            return response.json()

    def _convert_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        """Convert ChatMessage objects to OpenRouter format."""
        converted = []
        for msg in messages:
            msg_dict = {
                "role": msg.role,
                "content": msg.content,
            }
            if msg.name:
                msg_dict["name"] = msg.name
            if msg.function_call:
                msg_dict["function_call"] = msg.function_call
            converted.append(msg_dict)
        return converted

    def _convert_functions(
        self, functions: list[FunctionDefinition] | None
    ) -> list[dict[str, Any]] | None:
        """Convert FunctionDefinition objects to OpenRouter format."""
        if not functions:
            return None

        converted = []
        for func in functions:
            func_dict = {
                "name": func.name,
                "description": func.description,
                "parameters": {"type": "object", "properties": {}, "required": []},
            }

            # Convert parameters
            for param in func.parameters:
                func_dict["parameters"]["properties"][param.name] = {
                    "type": param.type,
                    "description": param.description,
                }
                if param.enum:
                    func_dict["parameters"]["properties"][param.name][
                        "enum"
                    ] = param.enum
                if param.required:
                    func_dict["parameters"]["required"].append(param.name)

            converted.append(func_dict)

        return converted

    def _convert_parameters(
        self, params: InferenceParameters | None
    ) -> dict[str, Any]:
        """Convert InferenceParameters to OpenRouter format."""
        if not params:
            return {}

        converted = {}
        if params.temperature is not None:
            converted["temperature"] = params.temperature
        if params.max_tokens is not None:
            converted["max_tokens"] = params.max_tokens
        if params.top_p is not None:
            converted["top_p"] = params.top_p
        if params.top_k is not None:
            converted["top_k"] = params.top_k
        if params.frequency_penalty is not None:
            converted["frequency_penalty"] = params.frequency_penalty
        if params.presence_penalty is not None:
            converted["presence_penalty"] = params.presence_penalty
        if params.stop is not None:
            converted["stop"] = params.stop
        if params.stream is not None:
            converted["stream"] = params.stream

        return converted

    def _parse_response(self, response_data: dict[str, Any]) -> LLMInferenceResponse:
        """Parse OpenRouter response to LLMInferenceResponse."""
        choices = []
        for choice_data in response_data.get("choices", []):
            message_data = choice_data.get("message", {})
            message = ChatMessage(
                role=message_data.get("role", "assistant"),
                content=message_data.get("content", ""),
                name=message_data.get("name"),
                function_call=message_data.get("function_call"),
            )

            choice = Choice(
                index=choice_data.get("index", 0),
                message=message,
                finish_reason=choice_data.get("finish_reason"),
            )
            choices.append(choice)

        usage_data = response_data.get("usage", {})
        usage = UsageInfo(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        return LLMInferenceResponse(
            id=response_data.get("id", ""),
            object=response_data.get("object", "chat.completion"),
            created=response_data.get("created", int(time.time())),
            model=response_data.get("model", ""),
            choices=choices,
            usage=usage,
        )


@activity.defn
async def chat_completion(request: LLMInferenceRequest) -> LLMInferenceResult:
    """
    Perform chat completion using OpenRouter API.

    Args:
        request: LLM inference request with model, messages, and parameters

    Returns:
        LLMInferenceResult: Result with response and metadata
    """
    start_time = time.time()
    logger.info(f"Starting chat completion with model: {request.model}")

    try:
        # Use provided credentials or fall back to environment variables
        if request.credentials:
            credentials_dict = request.credentials.model_dump()
        else:
            from shared.config import Config
            if not Config.OPENROUTER_API_KEY:
                raise ValueError("OpenRouter API key not provided and not found in environment")
            credentials_dict = {"api_key": Config.OPENROUTER_API_KEY}
        
        # Initialize client
        client = OpenRouterClient(credentials_dict)

        # Prepare request data
        request_data = {
            "model": request.model,
            "messages": client._convert_messages(request.messages),
        }

        # Add parameters
        if request.parameters:
            request_data.update(client._convert_parameters(request.parameters))

        # Add functions
        if request.functions:
            request_data["functions"] = client._convert_functions(request.functions)

        # Add function call mode
        if request.function_call:
            request_data["function_call"] = request.function_call

        # Make API call
        response_data = await client._make_request("chat/completions", request_data)

        # Parse response
        response = client._parse_response(response_data)

        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Create result
        result = LLMInferenceResult(
            request=request,
            response=response,
            status="completed",
            execution_time_ms=execution_time_ms,
            tokens_used=response.usage.total_tokens,
            finish_reason=(
                response.choices[0].finish_reason if response.choices else None
            ),
        )

        logger.info(
            f"Chat completion completed successfully. "
            f"Tokens used: {result.tokens_used}, "
            f"Execution time: {execution_time_ms}ms"
        )

        return result

    except httpx.HTTPStatusError as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_message = f"HTTP error {e.response.status_code}: {e.response.text}"

        logger.error(f"Chat completion failed: {error_message}")

        return LLMInferenceResult(
            request=request,
            response=None,
            status="failed",
            error_message=error_message,
            execution_time_ms=execution_time_ms,
            tokens_used=0,
        )

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_message = f"Unexpected error: {str(e)}"

        logger.error(f"Chat completion failed: {error_message}")

        return LLMInferenceResult(
            request=request,
            response=None,
            status="failed",
            error_message=error_message,
            execution_time_ms=execution_time_ms,
            tokens_used=0,
        )


@activity.defn
async def validate_model(credentials: dict[str, Any] | None, model: str) -> dict[str, Any]:
    """
    Validate if a model is available on OpenRouter.

    Args:
        credentials: OpenRouter credentials (optional, will use env vars if None)
        model: Model name to validate

    Returns:
        Dict with validation result and model info
    """
    logger.info(f"Validating model: {model}")

    try:
        # Use provided credentials or fall back to environment variables
        if credentials:
            credentials_dict = credentials
        else:
            from shared.config import Config
            if not Config.OPENROUTER_API_KEY:
                raise ValueError("OpenRouter API key not provided and not found in environment")
            credentials_dict = {"api_key": Config.OPENROUTER_API_KEY}
        
        client = OpenRouterClient(credentials_dict)

        # Get available models
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.get(
                f"{client.base_url}/models", headers=client.headers
            )
            response.raise_for_status()
            models_data = response.json()

        # Find the model
        model_info = None
        for model_data in models_data.get("data", []):
            if model_data.get("id") == model:
                model_info = model_data
                break

        if model_info:
            return {
                "valid": True,
                "model": model,
                "model_info": {
                    "id": model_info.get("id"),
                    "name": model_info.get("name"),
                    "description": model_info.get("description"),
                    "pricing": model_info.get("pricing"),
                    "context_length": model_info.get("context_length"),
                },
            }
        else:
            return {
                "valid": False,
                "model": model,
                "error": f"Model '{model}' not found on OpenRouter",
            }

    except Exception as e:
        logger.error(f"Model validation failed: {e}")
        return {"valid": False, "model": model, "error": f"Validation failed: {str(e)}"}


@activity.defn
async def get_available_models(credentials: dict[str, Any] | None) -> dict[str, Any]:
    """
    Get list of available models from OpenRouter.

    Args:
        credentials: OpenRouter credentials (optional, will use env vars if None)

    Returns:
        Dict with list of available models
    """
    logger.info("Fetching available models from OpenRouter")

    try:
        # Use provided credentials or fall back to environment variables
        if credentials:
            credentials_dict = credentials
        else:
            from shared.config import Config
            if not Config.OPENROUTER_API_KEY:
                raise ValueError("OpenRouter API key not provided and not found in environment")
            credentials_dict = {"api_key": Config.OPENROUTER_API_KEY}
        
        client = OpenRouterClient(credentials_dict)

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.get(
                f"{client.base_url}/models", headers=client.headers
            )
            response.raise_for_status()
            models_data = response.json()

        models = []
        for model_data in models_data.get("data", []):
            models.append(
                {
                    "id": model_data.get("id"),
                    "name": model_data.get("name"),
                    "description": model_data.get("description"),
                    "pricing": model_data.get("pricing"),
                    "context_length": model_data.get("context_length"),
                }
            )

        return {"success": True, "models": models, "total_count": len(models)}

    except Exception as e:
        logger.error(f"Failed to fetch models: {e}")
        return {"success": False, "error": str(e), "models": []}


@activity.defn
async def estimate_tokens(text: str, model: str = "gpt-3.5-turbo") -> dict[str, Any]:
    """
    Estimate token count for given text.

    Args:
        text: Text to estimate tokens for
        model: Model name for tokenization (affects token count)

    Returns:
        Dict with estimated token count
    """
    try:
        # Simple estimation: ~4 characters per token for English
        # This is a rough estimate, actual tokenization varies by model
        estimated_tokens = max(1, len(text) // 4)

        # Add some buffer for special tokens and formatting
        estimated_tokens = int(estimated_tokens * 1.1)

        return {
            "text_length": len(text),
            "estimated_tokens": estimated_tokens,
            "model": model,
            "method": "character_based_estimation",
        }

    except Exception as e:
        logger.error(f"Token estimation failed: {e}")
        return {
            "text_length": len(text),
            "estimated_tokens": len(text) // 4,  # Fallback estimation
            "error": str(e),
        }


@activity.defn
async def format_function_result(function_name: str, result: Any) -> str:
    """
    Format function call result for inclusion in conversation.

    Args:
        function_name: Name of the function that was called
        result: Result from the function call

    Returns:
        Formatted string for function result
    """
    try:
        if isinstance(result, dict):
            formatted_result = json.dumps(result, indent=2)
        elif isinstance(result, (list, tuple)):
            formatted_result = json.dumps(list(result), indent=2)
        else:
            formatted_result = str(result)

        return f"Function '{function_name}' returned:\n{formatted_result}"

    except Exception as e:
        logger.error(f"Failed to format function result: {e}")
        return f"Function '{function_name}' returned a result that could not be formatted: {str(result)}"
