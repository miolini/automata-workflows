"""
Configuration management for Automata Workflows.

This module provides centralized access to environment variables and configuration
settings used across the workflows system.
"""

import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    # Get the project root directory
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"

    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    # python-dotenv not available, use only system environmglm-4.6
    pass


class Config:
    """Centralized configuration class for environment variables."""

    # Temporal Configuration
    TEMPORAL_HOST: str = os.getenv("TEMPORAL_HOST", "localhost:7233")
    TEMPORAL_NAMESPACE: str = os.getenv("TEMPORAL_NAMESPACE", "default")
    TEMPORAL_TASK_QUEUE: str = os.getenv("TEMPORAL_TASK_QUEUE", "llm-inference")

    # OpenRouter Configuration
    OPENROUTER_API_KEY: str | None = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "glm-4.6")

    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://user:password@localhost:5432/automata"
    )
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "20"))
    DATABASE_MAX_OVERFLOW: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "30"))

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")
    LOG_CORRELATION_ID_ENABLED: bool = (
        os.getenv("LOG_CORRELATION_ID_ENABLED", "true").lower() == "true"
    )

    # Timeouts (in seconds)
    HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", "30"))
    TEMPORAL_ACTIVITY_TIMEOUT: int = int(os.getenv("TEMPORAL_ACTIVITY_TIMEOUT", "300"))
    TEMPORAL_WORKFLOW_TIMEOUT: int = int(os.getenv("TEMPORAL_WORKFLOW_TIMEOUT", "3600"))

    # Retry Configuration
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    RETRY_INITIAL_INTERVAL: int = int(os.getenv("RETRY_INITIAL_INTERVAL", "1"))
    RETRY_MAXIMUM_INTERVAL: int = int(os.getenv("RETRY_MAXIMUM_INTERVAL", "60"))
    RETRY_BACKOFF_COEFFICIENT: float = float(
        os.getenv("RETRY_BACKOFF_COEFFICIENT", "2.0")
    )

    # NATS Configuration
    NATS_URL: str = os.getenv("NATS_URL", "nats://localhost:4222")
    NATS_HTTP_URL: str | None = os.getenv("NATS_HTTP_URL")
    NATS_SUBJECT_PREFIX: str = os.getenv("NATS_SUBJECT_PREFIX", "automata.workflows")

    # Elixir API Configuration
    ELIXIR_WEBHOOK_URL: str = os.getenv(
        "ELIXIR_WEBHOOK_URL", "http://localhost:4000/api/webhooks/workflows"
    )
    ELIXIR_WEBHOOK_SECRET: str = os.getenv(
        "ELIXIR_WEBHOOK_SECRET", "dev-webhook-secret-12345"
    )

    # Coding Agent Configuration
    TEMPORAL_TASK_QUEUE_CODING_AGENT: str = os.getenv(
        "TEMPORAL_TASK_QUEUE_CODING_AGENT", "coding-agent"
    )

    @classmethod
    def validate_openrouter_config(cls) -> bool:
        """Validate that required OpenRouter configuration is present."""
        if not cls.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        return True

    @classmethod
    def get_temporal_client_config(cls) -> dict:
        """Get Temporal client configuration."""
        return {
            "host": cls.TEMPORAL_HOST,
            "namespace": cls.TEMPORAL_NAMESPACE,
        }

    @classmethod
    def get_openrouter_credentials(cls) -> dict:
        """Get OpenRouter credentials."""
        cls.validate_openrouter_config()
        return {"api_key": cls.OPENROUTER_API_KEY}


# Global configuration instance
config = Config()
