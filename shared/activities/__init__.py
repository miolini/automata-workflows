"""
Shared Temporal activities for Automata Workflows

This package contains reusable activities that can be used across
different workflow implementations.
"""

__version__ = "0.1.0"

# LLM Activities
from .llm import (
    chat_completion,
    estimate_tokens,
    format_function_result,
    notify_completion,
    validate_model,
)

# Coding Agent Activities
from .coding_agent import (
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

__all__ = [
    # LLM
    "chat_completion",
    "estimate_tokens",
    "format_function_result",
    "notify_completion",
    "validate_model",
    # Coding Agent
    "clone_repository",
    "commit_changes",
    "create_branch",
    "list_directory_activity",
    "notify_elixir_api",
    "push_changes",
    "read_file_activity",
    "run_shell_command",
    "send_nats_notification",
    "store_task_activity",
    "write_file_activity",
]

