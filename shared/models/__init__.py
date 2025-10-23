"""
Data models and schemas for Automata Workflows

This package contains Pydantic models for all input/output data structures
used across workflows and activities.
"""

__version__ = "0.1.0"

# LLM Models
from .llm import (
    ChatMessage,
    Choice,
    FunctionDefinition,
    FunctionParameter,
    InferenceParameters,
    LLMInferenceRequest,
    LLMInferenceResponse,
    LLMInferenceResult,
    OpenRouterCredentials,
    UsageInfo,
)

# Coding Agent Models
from .coding_agent import (
    AgentConfig,
    CodingAgentRequest,
    CodingAgentResult,
    GitCredentials,
    GitCredentialsType,
    ImplementationPlan,
    ImplementationStep,
    NotificationType,
    RepositoryConfig,
    TaskConfig,
    ValidationResult,
    WorkflowNotification,
)

__all__ = [
    # LLM
    "ChatMessage",
    "Choice",
    "FunctionDefinition",
    "FunctionParameter",
    "InferenceParameters",
    "LLMInferenceRequest",
    "LLMInferenceResponse",
    "LLMInferenceResult",
    "OpenRouterCredentials",
    "UsageInfo",
    # Coding Agent
    "AgentConfig",
    "CodingAgentRequest",
    "CodingAgentResult",
    "GitCredentials",
    "GitCredentialsType",
    "ImplementationPlan",
    "ImplementationStep",
    "NotificationType",
    "RepositoryConfig",
    "TaskConfig",
    "ValidationResult",
    "WorkflowNotification",
]

