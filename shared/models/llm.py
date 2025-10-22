"""
LLM and OpenRouter related data models for Automata Workflows
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OpenRouterCredentials(BaseModel):
    """Credentials for OpenRouter API access."""

    api_key: str = Field(..., description="OpenRouter API key")
    base_url: str = Field(
        default="https://openrouter.ai/api/v1", description="OpenRouter base URL"
    )

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class InferenceParameters(BaseModel):
    """Parameters for LLM inference."""

    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Sampling temperature"
    )
    max_tokens: int | None = Field(
        default=None, ge=1, le=32768, description="Maximum tokens to generate"
    )
    top_p: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter"
    )
    top_k: int | None = Field(
        default=None, ge=1, description="Top-k sampling parameter"
    )
    frequency_penalty: float = Field(
        default=0.0, ge=-2.0, le=2.0, description="Frequency penalty"
    )
    presence_penalty: float = Field(
        default=0.0, ge=-2.0, le=2.0, description="Presence penalty"
    )
    stop: str | list[str] | None = Field(
        default=None, description="Stop sequences"
    )
    stream: bool = Field(default=False, description="Whether to stream responses")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class FunctionParameter(BaseModel):
    """Parameter definition for function calling."""

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (string, number, boolean, etc.)")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=True, description="Whether parameter is required")
    enum: list[str] | None = Field(
        default=None, description="Allowed values for enum parameters"
    )


class FunctionDefinition(BaseModel):
    """Function definition for function calling."""

    name: str = Field(..., description="Function name")
    description: str = Field(..., description="Function description")
    parameters: list[FunctionParameter] = Field(..., description="Function parameters")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class MessageRole(BaseModel):
    """Message role in conversation."""

    role: Literal["system", "user", "assistant", "function"] = Field(
        ..., description="Message role"
    )
    content: str = Field(..., description="Message content")
    name: str | None = Field(
        default=None, description="Optional name for the message sender"
    )
    function_call: dict[str, Any] | None = Field(
        default=None, description="Function call information"
    )


class ChatMessage(BaseModel):
    """Chat message in conversation history."""

    role: Literal["system", "user", "assistant", "function"] = Field(
        ..., description="Message role"
    )
    content: str = Field(..., description="Message content")
    name: str | None = Field(
        default=None, description="Optional name for the message sender"
    )
    function_call: dict[str, Any] | None = Field(
        default=None, description="Function call information"
    )

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class LLMInferenceRequest(BaseModel):
    """Request for LLM inference."""

    model: str = Field(
        ...,
        description="Model name (e.g., 'glm-4.6')",
    )
    messages: list[ChatMessage] = Field(..., description="Conversation history")
    credentials: OpenRouterCredentials | None = Field(
        default=None, description="OpenRouter credentials (optional, will use env vars if not provided)"
    )
    parameters: InferenceParameters | None = Field(
        default=None, description="Inference parameters"
    )
    functions: list[FunctionDefinition] | None = Field(
        default=None, description="Available functions for calling"
    )
    function_call: str | dict[str, Any] | None = Field(
        default=None, description="Function call mode"
    )

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class UsageInfo(BaseModel):
    """Token usage information."""

    prompt_tokens: int = Field(..., description="Tokens used in prompt")
    completion_tokens: int = Field(..., description="Tokens used in completion")
    total_tokens: int = Field(..., description="Total tokens used")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class Choice(BaseModel):
    """Choice in LLM response."""

    index: int = Field(..., description="Choice index")
    message: ChatMessage = Field(..., description="Response message")
    finish_reason: str | None = Field(
        default=None, description="Reason for finishing"
    )

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class LLMInferenceResponse(BaseModel):
    """Response from LLM inference."""

    id: str = Field(..., description="Response ID")
    object: str = Field(default="chat.completion", description="Object type")
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Model used")
    choices: list[Choice] = Field(..., description="Response choices")
    usage: UsageInfo = Field(..., description="Token usage information")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class LLMInferenceResult(BaseModel):
    """Result of LLM inference workflow."""

    request: LLMInferenceRequest
    response: LLMInferenceResponse | None = None
    status: str
    error_message: str | None = None
    execution_time_ms: int = 0
    tokens_used: int = 0
    finish_reason: str | None = None

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class BatchInferenceRequest(BaseModel):
    """Request for batch LLM inference."""

    requests: list[LLMInferenceRequest] = Field(
        ..., description="List of inference requests"
    )
    max_concurrent: int = Field(
        default=5, ge=1, le=10, description="Maximum concurrent requests"
    )

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class BatchInferenceResult(BaseModel):
    """Result of batch LLM inference workflow."""

    results: list[LLMInferenceResult] = Field(
        ..., description="List of inference results"
    )
    total_requests: int = Field(..., description="Total number of requests")
    successful_requests: int = Field(..., description="Number of successful requests")
    failed_requests: int = Field(..., description="Number of failed requests")
    total_tokens_used: int = Field(
        ..., description="Total tokens used across all requests"
    )
    total_execution_time_ms: int = Field(..., description="Total execution time")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
