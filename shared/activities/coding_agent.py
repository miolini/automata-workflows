"""
Coding Agent activities for Automata Workflows.

Provides activities for git operations, file management, shell command execution,
NATS notifications, and LLM interactions for the coding agent workflow.
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import structlog
from temporalio import activity

from shared.models.coding_agent import (
    CodingAgentRequest,
    GitCredentials,
    GitCredentialsType,
    ImplementationPlan,
    ImplementationStep,
    NotificationType,
    ValidationResult,
    WorkflowNotification,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# Git Operations
# ============================================================================


@activity.defn
async def clone_repository(
    remote_url: str, branch: str, credentials: dict[str, Any], temp_dir: str
) -> dict[str, Any]:
    """
    Clone a git repository to a temporary directory.

    Args:
        remote_url: Git repository URL
        branch: Branch to checkout
        credentials: Git credentials dictionary
        temp_dir: Temporary directory to clone into

    Returns:
        Dictionary with clone result and repository path
    """
    try:
        logger.info(f"Cloning repository: {remote_url}, branch: {branch}")

        # Parse credentials
        git_creds = GitCredentials(**credentials)

        # Prepare the clone URL with credentials
        clone_url = _prepare_clone_url(remote_url, git_creds)

        # Create temp directory if it doesn't exist
        os.makedirs(temp_dir, exist_ok=True)
        repo_path = os.path.join(temp_dir, "repo")

        # Clone the repository
        clone_cmd = ["git", "clone", "--branch", branch, "--depth", "1", clone_url, repo_path]

        # Set up environment for SSH keys if needed
        env = os.environ.copy()
        ssh_key_path: str | None = None

        if git_creds.credential_type == GitCredentialsType.KEY_CERT:
            ssh_key_path = await _setup_ssh_key(git_creds, temp_dir)
            env["GIT_SSH_COMMAND"] = f"ssh -i {ssh_key_path} -o StrictHostKeyChecking=no"

        # Execute clone command
        process = await asyncio.create_subprocess_exec(
            *clone_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=temp_dir,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Git clone failed: {stderr.decode()}")

        logger.info(f"Repository cloned successfully to: {repo_path}")

        return {
            "success": True,
            "repo_path": repo_path,
            "branch": branch,
            "message": "Repository cloned successfully",
        }

    except Exception as e:
        logger.error(f"Failed to clone repository: {e}")
        return {"success": False, "error": str(e)}
    finally:
        # Clean up SSH key file if it was created
        if ssh_key_path and os.path.exists(ssh_key_path):
            os.remove(ssh_key_path)


@activity.defn
async def create_branch(repo_path: str, branch_name: str, task_description: str) -> dict[str, Any]:
    """
    Create a new git branch with a sensible name based on task description.

    Args:
        repo_path: Path to the git repository
        branch_name: Base branch name or auto-generate from task
        task_description: Task description to generate branch name

    Returns:
        Dictionary with branch creation result
    """
    try:
        logger.info(f"Creating branch in repository: {repo_path}")

        # Generate sensible branch name from task description
        if not branch_name or branch_name == "auto":
            branch_name = _generate_branch_name(task_description)

        # Create and checkout new branch
        process = await asyncio.create_subprocess_exec(
            "git",
            "checkout",
            "-b",
            branch_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=repo_path,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Git branch creation failed: {stderr.decode()}")

        logger.info(f"Branch created successfully: {branch_name}")

        return {
            "success": True,
            "branch_name": branch_name,
            "message": f"Branch '{branch_name}' created successfully",
        }

    except Exception as e:
        logger.error(f"Failed to create branch: {e}")
        return {"success": False, "error": str(e)}


@activity.defn
async def commit_changes(repo_path: str, commit_message: str) -> dict[str, Any]:
    """
    Commit all changes in the repository.

    Args:
        repo_path: Path to the git repository
        commit_message: Commit message

    Returns:
        Dictionary with commit result and hash
    """
    try:
        logger.info(f"Committing changes in repository: {repo_path}")

        # Configure git user if not already configured
        await asyncio.create_subprocess_exec(
            "git", "config", "user.name", "Automata Agent",
            cwd=repo_path,
        )
        await asyncio.create_subprocess_exec(
            "git", "config", "user.email", "agent@automata.sentientwave.com",
            cwd=repo_path,
        )

        # Add all changes
        process = await asyncio.create_subprocess_exec(
            "git", "add", "-A",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=repo_path,
        )
        await process.communicate()

        # Commit changes
        process = await asyncio.create_subprocess_exec(
            "git", "commit", "-m", commit_message,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=repo_path,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            # Check if there are no changes to commit
            if "nothing to commit" in stderr.decode().lower():
                return {
                    "success": True,
                    "commit_hash": None,
                    "message": "No changes to commit",
                }
            raise RuntimeError(f"Git commit failed: {stderr.decode()}")

        # Get commit hash
        process = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=repo_path,
        )
        stdout, stderr = await process.communicate()
        commit_hash = stdout.decode().strip()

        logger.info(f"Changes committed successfully: {commit_hash}")

        return {
            "success": True,
            "commit_hash": commit_hash,
            "message": f"Changes committed: {commit_hash}",
        }

    except Exception as e:
        logger.error(f"Failed to commit changes: {e}")
        return {"success": False, "error": str(e)}


@activity.defn
async def push_changes(
    repo_path: str, branch_name: str, remote_url: str, credentials: dict[str, Any]
) -> dict[str, Any]:
    """
    Push changes to remote repository.

    Args:
        repo_path: Path to the git repository
        branch_name: Branch to push
        remote_url: Remote repository URL
        credentials: Git credentials dictionary

    Returns:
        Dictionary with push result
    """
    try:
        logger.info(f"Pushing changes to remote: {branch_name}")

        # Parse credentials
        git_creds = GitCredentials(**credentials)

        # Prepare the push URL with credentials
        push_url = _prepare_clone_url(remote_url, git_creds)

        # Set up environment for SSH keys if needed
        env = os.environ.copy()
        ssh_key_path: str | None = None

        if git_creds.credential_type == GitCredentialsType.KEY_CERT:
            ssh_key_path = await _setup_ssh_key(git_creds, os.path.dirname(repo_path))
            env["GIT_SSH_COMMAND"] = f"ssh -i {ssh_key_path} -o StrictHostKeyChecking=no"

        # Update remote URL
        process = await asyncio.create_subprocess_exec(
            "git", "remote", "set-url", "origin", push_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=repo_path,
            env=env,
        )
        await process.communicate()

        # Push changes
        process = await asyncio.create_subprocess_exec(
            "git", "push", "-u", "origin", branch_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=repo_path,
            env=env,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Git push failed: {stderr.decode()}")

        logger.info(f"Changes pushed successfully to: {branch_name}")

        return {
            "success": True,
            "branch_name": branch_name,
            "message": f"Changes pushed to '{branch_name}' successfully",
        }

    except Exception as e:
        logger.error(f"Failed to push changes: {e}")
        return {"success": False, "error": str(e)}
    finally:
        # Clean up SSH key file if it was created
        if ssh_key_path and os.path.exists(ssh_key_path):
            os.remove(ssh_key_path)


# ============================================================================
# File Operations
# ============================================================================


@activity.defn
async def read_file_activity(repo_path: str, file_path: str) -> dict[str, Any]:
    """
    Read file content from repository.

    Args:
        repo_path: Path to the git repository
        file_path: Relative path to file within repository

    Returns:
        Dictionary with file content or error
    """
    try:
        full_path = os.path.join(repo_path, file_path)
        
        # Security: Prevent directory traversal
        if not os.path.abspath(full_path).startswith(os.path.abspath(repo_path)):
            return {"success": False, "error": f"Invalid file path (directory traversal attempt): {file_path}"}

        if not os.path.exists(full_path):
            return {"success": False, "error": f"File not found: {file_path}"}

        if not os.path.isfile(full_path):
            return {"success": False, "error": f"Path is not a file: {file_path}"}

        # Check file size (limit to 5MB for more flexibility)
        file_size = os.path.getsize(full_path)
        if file_size > 5 * 1024 * 1024:
            return {
                "success": False,
                "error": f"File too large: {file_size} bytes (max 5MB)",
            }

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        logger.info(f"Read file: {file_path} ({file_size} bytes)")

        return {
            "success": True,
            "content": content,
            "file_path": file_path,
            "size": file_size,
        }

    except UnicodeDecodeError:
        return {"success": False, "error": f"File is not a text file: {file_path}"}
    except PermissionError:
        return {"success": False, "error": f"Permission denied reading file: {file_path}"}
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return {"success": False, "error": str(e)}


@activity.defn
async def write_file_activity(repo_path: str, file_path: str, content: str) -> dict[str, Any]:
    """
    Write content to a file in repository.

    Args:
        repo_path: Path to the git repository
        file_path: Relative path to file within repository
        content: Content to write

    Returns:
        Dictionary with write result
    """
    try:
        full_path = os.path.join(repo_path, file_path)
        
        # Security: Prevent directory traversal
        if not os.path.abspath(full_path).startswith(os.path.abspath(repo_path)):
            return {"success": False, "error": f"Invalid file path (directory traversal attempt): {file_path}"}

        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        file_size = os.path.getsize(full_path)
        logger.info(f"Wrote file: {file_path} ({file_size} bytes)")

        return {
            "success": True,
            "file_path": file_path,
            "size": file_size,
            "message": f"File written successfully: {file_path}",
        }

    except PermissionError:
        logger.error(f"Permission denied writing file {file_path}")
        return {"success": False, "error": f"Permission denied writing file: {file_path}"}
    except OSError as e:
        logger.error(f"OS error writing file {file_path}: {e}")
        return {"success": False, "error": f"OS error: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        return {"success": False, "error": str(e)}


@activity.defn
async def list_directory_activity(repo_path: str, dir_path: str = ".") -> dict[str, Any]:
    """
    List files and directories in a repository path.

    Args:
        repo_path: Path to the git repository
        dir_path: Relative path to directory within repository

    Returns:
        Dictionary with directory listing
    """
    try:
        full_path = os.path.join(repo_path, dir_path)

        if not os.path.exists(full_path):
            return {"success": False, "error": f"Directory not found: {dir_path}"}

        if not os.path.isdir(full_path):
            return {"success": False, "error": f"Path is not a directory: {dir_path}"}

        files = []
        directories = []

        for item in os.listdir(full_path):
            # Skip .git directory
            if item == ".git":
                continue

            item_path = os.path.join(full_path, item)
            if os.path.isfile(item_path):
                files.append(item)
            elif os.path.isdir(item_path):
                directories.append(item)

        logger.info(
            f"Listed directory: {dir_path} ({len(files)} files, {len(directories)} directories)"
        )

        return {
            "success": True,
            "dir_path": dir_path,
            "files": sorted(files),
            "directories": sorted(directories),
        }

    except Exception as e:
        logger.error(f"Failed to list directory {dir_path}: {e}")
        return {"success": False, "error": str(e)}


# ============================================================================
# Shell Command Execution
# ============================================================================


@activity.defn
async def run_shell_command(
    repo_path: str, command: str, timeout: int = 300
) -> dict[str, Any]:
    """
    Run a shell command in the repository directory.

    Args:
        repo_path: Path to the git repository
        command: Shell command to execute
        timeout: Command timeout in seconds

    Returns:
        Dictionary with command result
    """
    try:
        logger.info(f"Running command in {repo_path}: {command}")

        # Security check: don't allow certain dangerous commands
        dangerous_patterns = [
            r"rm\s+-rf\s+/",  # Delete root
            r":\(\)\{.*\}",  # Fork bomb
            r"dd\s+if=/dev/zero",  # Disk wipe
            r"mkfs\.",  # Format filesystem
            r">\s*/dev/sd[a-z]",  # Write to disk device
            r"curl.*\|\s*sh",  # Pipe to shell
            r"wget.*\|\s*sh",  # Pipe to shell
            r"chmod.*777",  # Overly permissive permissions
            r"eval\s+",  # Eval can be dangerous
            r"exec\s+",  # Exec can be dangerous
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return {
                    "success": False,
                    "error": f"Command blocked - matches dangerous pattern: {pattern}",
                }

        # Execute command
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=repo_path,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
            }

        return_code = process.returncode
        stdout_str = stdout.decode() if stdout else ""
        stderr_str = stderr.decode() if stderr else ""

        logger.info(f"Command completed with return code: {return_code}")

        return {
            "success": return_code == 0,
            "return_code": return_code,
            "stdout": stdout_str,
            "stderr": stderr_str,
            "command": command,
        }

    except Exception as e:
        logger.error(f"Failed to run command: {e}")
        return {"success": False, "error": str(e)}


# ============================================================================
# NATS Notifications
# ============================================================================


@activity.defn
async def send_nats_notification(notification: dict[str, Any]) -> dict[str, Any]:
    """
    Send notification to NATS server.

    Args:
        notification: Notification data dictionary

    Returns:
        Dictionary with notification result
    """
    try:
        nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
        nats_http_url = os.getenv("NATS_HTTP_URL")
        subject = os.getenv("NATS_SUBJECT_PREFIX", "automata.workflows")

        # Parse notification
        notif = WorkflowNotification(**notification)

        # Format subject based on notification type
        full_subject = f"{subject}.{notif.company_id}.{notif.project_id}.{notif.task_id}.{notif.notification_type.value}"

        logger.info(f"Sending NATS notification to: {full_subject}")

        # If NATS HTTP bridge is configured, use it
        if nats_http_url:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{nats_http_url}/pub/{full_subject}",
                        json=notification,
                    )
                    response.raise_for_status()
                    logger.info(f"NATS notification sent successfully via HTTP: {notif.notification_type}")
            except httpx.HTTPError as e:
                logger.warning(f"Failed to send NATS notification via HTTP: {e}")
                # Continue - this is non-fatal
        else:
            # If no HTTP bridge, just log the notification
            # In production, you would use nats.py client here
            logger.info(f"NATS HTTP bridge not configured - notification logged only: {notif.notification_type}")

        return {
            "success": True,
            "subject": full_subject,
            "notification_type": notif.notification_type.value,
        }

    except Exception as e:
        logger.error(f"Failed to send NATS notification: {e}")
        # Don't fail the workflow if notification fails
        return {"success": False, "error": str(e)}


# ============================================================================
# Database Operations
# ============================================================================


@activity.defn
async def store_task_activity(
    task_id: str,
    activity_type: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Store task activity in database for monitoring.

    Args:
        task_id: Task ID
        activity_type: Type of activity (e.g., 'progress', 'function_call', 'mcp_call')
        message: Activity message
        details: Additional activity details

    Returns:
        Dictionary with storage result
    """
    try:
        from datetime import timezone
        
        # For now, we'll just log the activity
        # In production, this should store in PostgreSQL using SQLAlchemy
        timestamp = datetime.now(timezone.utc)
        
        logger.info(
            f"Task activity - Task: {task_id}, Type: {activity_type}, Message: {message}",
            details=details or {},
            timestamp=timestamp.isoformat(),
        )

        activity_data = {
            "task_id": task_id,
            "activity_type": activity_type,
            "message": message,
            "details": details or {},
            "timestamp": timestamp.isoformat(),
        }

        # TODO: Store in database
        # async with get_db_session() as session:
        #     task_activity = TaskActivity(**activity_data)
        #     session.add(task_activity)
        #     await session.commit()
        #     await session.refresh(task_activity)
        #     return {
        #         "success": True,
        #         "activity_id": task_activity.id,
        #         "message": "Task activity stored successfully",
        #     }

        return {
            "success": True,
            "activity_id": f"{task_id}_{int(timestamp.timestamp())}",
            "message": "Task activity logged (database storage not yet implemented)",
        }

    except Exception as e:
        logger.error(f"Failed to store task activity: {e}")
        return {"success": False, "error": str(e)}


# ============================================================================
# Elixir API Notification
# ============================================================================


@activity.defn
async def notify_elixir_api(
    workflow_id: str, result: dict[str, Any], status: str
) -> dict[str, Any]:
    """
    Notify Elixir API about workflow completion or failure.

    Args:
        workflow_id: Workflow execution ID
        result: Workflow result data
        status: Workflow status ('completed' or 'failed')

    Returns:
        Dictionary with notification result
    """
    webhook_url = os.getenv(
        "ELIXIR_WEBHOOK_URL", "http://localhost:4000/api/webhooks/workflows"
    )
    webhook_secret = os.getenv("ELIXIR_WEBHOOK_SECRET", "dev-webhook-secret-12345")

    try:
        logger.info(f"Notifying Elixir API about workflow {status}: {workflow_id}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{webhook_url}/{workflow_id}",
                json={"status": status, "result": result},
                headers={"Authorization": f"Bearer {webhook_secret}"},
            )
            response.raise_for_status()

            logger.info(f"Successfully notified Elixir API for workflow {workflow_id}")
            return {
                "success": True,
                "status_code": response.status_code,
                "response": response.json() if response.text else None,
            }

    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error notifying Elixir API: {e.response.status_code} - {e.response.text}"
        )
        return {
            "success": False,
            "error": f"HTTP {e.response.status_code}: {e.response.text}",
            "status_code": e.response.status_code,
        }
    except Exception as e:
        logger.error(f"Failed to notify Elixir API: {e}")
        return {"success": False, "error": str(e)}


# ============================================================================
# Helper Functions
# ============================================================================


def _prepare_clone_url(remote_url: str, credentials: GitCredentials) -> str:
    """Prepare clone URL with credentials embedded."""
    if credentials.credential_type == GitCredentialsType.USERNAME_PASSWORD:
        # Extract hostname from URL
        if "://" in remote_url:
            protocol, rest = remote_url.split("://", 1)
            return f"{protocol}://{credentials.username}:{credentials.password}@{rest}"
        else:
            return f"https://{credentials.username}:{credentials.password}@{remote_url}"

    elif credentials.credential_type == GitCredentialsType.ACCESS_TOKEN:
        # For GitHub/GitLab, use token as username
        if "://" in remote_url:
            protocol, rest = remote_url.split("://", 1)
            return f"{protocol}://{credentials.access_token}@{rest}"
        else:
            return f"https://{credentials.access_token}@{remote_url}"

    # For SSH keys, return original URL
    return remote_url


async def _setup_ssh_key(credentials: GitCredentials, temp_dir: str) -> str:
    """Set up SSH key for git operations."""
    ssh_key_path = os.path.join(temp_dir, "ssh_key")

    # Write private key to file
    key_content = credentials.private_key or ""
    if credentials.private_key_path:
        with open(credentials.private_key_path, "r") as f:
            key_content = f.read()

    with open(ssh_key_path, "w") as f:
        f.write(key_content)

    # Set proper permissions
    os.chmod(ssh_key_path, 0o600)

    return ssh_key_path


def _generate_branch_name(task_description: str) -> str:
    """Generate a sensible branch name from task description."""
    # Take first 50 chars of description
    desc = task_description[:50].lower()

    # Remove special characters and replace spaces with dashes
    desc = re.sub(r"[^\w\s-]", "", desc)
    desc = re.sub(r"[-\s]+", "-", desc)
    
    # Remove leading/trailing dashes
    desc = desc.strip("-")
    
    # Ensure we have at least something
    if not desc:
        desc = "task"

    # Add prefix and timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    branch_name = f"feat/{timestamp}-{desc}"
    
    # Ensure branch name is not too long (git has limits)
    if len(branch_name) > 100:
        branch_name = branch_name[:100].rstrip("-")
    
    return branch_name
