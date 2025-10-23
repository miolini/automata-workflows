"""
Coding Agent Workflow

This workflow implements an autonomous coding agent that can work on assigned tasks.
It clones a repository, creates a branch, implements changes using LLM guidance,
validates the changes, and pushes them to the remote repository.

The workflow is designed to run for extended periods (months) and provides
comprehensive monitoring through task activities and NATS notifications.
"""

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from typing import Any

# Read API key at module level (outside workflow) to avoid sandbox restrictions
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

from temporalio import workflow
from temporalio.common import RetryPolicy

from shared.models.coding_agent import (
    CodingAgentRequest,
    CodingAgentResult,
    ImplementationPlan,
    NotificationType,
    ValidationResult,
    WorkflowNotification,
)
from shared.models.llm import (
    ChatMessage,
    FunctionDefinition,
    FunctionParameter,
    InferenceParameters,
    LLMInferenceRequest,
    OpenRouterCredentials,
)
from workflows.llm_inference.llm_inference_workflow import LLMInferenceWorkflow


@workflow.defn
class CodingAgentWorkflow:
    """
    Autonomous coding agent workflow for implementing software tasks.

    This workflow orchestrates the entire development lifecycle:
    1. Clone repository and create feature branch
    2. Generate implementation plan using LLM
    3. Iteratively implement changes with function calling tools
    4. Validate changes and run tests
    5. Commit and push changes
    6. Send notifications at each step
    """

    def __init__(self):
        self.temp_dir: str | None = None
        self.repo_path: str | None = None
        self.branch_name: str | None = None
        self.implementation_steps: int = 0
        self.llm_calls: int = 0
        self.max_iterations: int = 10  # Default max iterations
        self.timeout_hours: float = 24.0  # Default timeout in hours

    @workflow.run
    async def run(self, request: CodingAgentRequest) -> CodingAgentResult:
        """
        Execute the coding agent workflow.

        Args:
            request: Coding agent request with task details and git credentials

        Returns:
            CodingAgentResult with execution details and outcomes
        """
        workflow_id = workflow.info().workflow_id
        start_time = datetime.fromtimestamp(workflow.time())

        workflow.logger.info(
            f"Starting CodingAgentWorkflow - Company: {request.task.company_id}, "
            f"Project: {request.task.project_id}, Task: {request.task.id}"
        )
        
                # Validate OpenRouter API key
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        try:
            # Step 1: Initialize - Create temp directory and send initial notification
            workflow.logger.info("Step 1: Initializing workflow")
            # Use workflow ID to create deterministic temp directory path
            temp_base = tempfile.gettempdir()
            self.temp_dir = os.path.join(temp_base, f"automata_agent_{workflow.info().workflow_id}")

            await self._send_notification(
                request,
                NotificationType.WORKFLOW_STARTED,
                "Coding agent workflow started",
                {"temp_dir": self.temp_dir},
            )

            await self._store_activity(
                request.task.id,
                "progress",
                "Workflow initialized, preparing to clone repository",
            )

            # Step 2: Clone repository
            workflow.logger.info("Step 2: Cloning repository")
            clone_result = await workflow.execute_activity(
                "clone_repository",
                args=[
                    request.repository.remote_url,
                    request.repository.branch,
                    request.repository.credentials.model_dump(),
                    self.temp_dir,
                ],
                start_to_close_timeout=timedelta(minutes=15),  # Increased timeout for large repos
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=2),
                    maximum_interval=timedelta(minutes=2),
                    backoff_coefficient=2.0,
                    maximum_attempts=3,
                ),
            )

            if not clone_result["success"]:
                raise RuntimeError(f"Failed to clone repository: {clone_result['error']}")

            self.repo_path = clone_result["repo_path"]

            await self._send_notification(
                request,
                NotificationType.REPO_CLONED,
                f"Repository cloned successfully: {request.repository.remote_url}",
                {"branch": request.repository.branch},
            )

            await self._store_activity(
                request.task.id, "progress", f"Repository cloned from {request.repository.remote_url}"
            )

            # Step 3: Create feature branch
            workflow.logger.info("Step 3: Creating feature branch")
            branch_result = await workflow.execute_activity(
                "create_branch",
                args=[self.repo_path, "auto", request.task.title],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                    backoff_coefficient=2.0,
                    maximum_attempts=3,
                ),
            )

            if not branch_result["success"]:
                raise RuntimeError(f"Failed to create branch: {branch_result['error']}")

            self.branch_name = branch_result["branch_name"]

            await self._send_notification(
                request,
                NotificationType.BRANCH_CREATED,
                f"Feature branch created: {self.branch_name}",
                {"branch_name": self.branch_name},
            )

            await self._store_activity(
                request.task.id, "progress", f"Created feature branch: {self.branch_name}"
            )

            # Step 4: Generate implementation plan
            workflow.logger.info("Step 4: Generating implementation plan")
            implementation_plan = await self._generate_implementation_plan(request)

            await self._send_notification(
                request,
                NotificationType.PLAN_CREATED,
                "Implementation plan created",
                {
                    "steps": len(implementation_plan.steps),
                    "files_to_create": implementation_plan.files_to_create,
                    "files_to_modify": implementation_plan.files_to_modify,
                },
            )

            await self._store_activity(
                request.task.id,
                "progress",
                f"Implementation plan created with {len(implementation_plan.steps)} steps",
                {"plan": implementation_plan.model_dump()},
            )

            # Step 5: Implement changes iteratively
            workflow.logger.info("Step 5: Starting implementation")
            await self._send_notification(
                request,
                NotificationType.IMPLEMENTATION_STARTED,
                "Starting implementation",
                {"max_iterations": self.max_iterations},
            )

            implementation_result = await self._implement_changes(
                request, implementation_plan
            )

            # Step 6: Validate changes
            workflow.logger.info("Step 6: Validating changes")
            await self._send_notification(
                request,
                NotificationType.VALIDATION_STARTED,
                "Validating implementation",
            )

            validation_result = await self._validate_changes(request)

            await self._send_notification(
                request,
                NotificationType.VALIDATION_COMPLETED,
                f"Validation completed - Success: {validation_result.success}",
                {
                    "issues": len(validation_result.issues),
                    "tests_passed": validation_result.tests_passed,
                    "tests_failed": validation_result.tests_failed,
                },
            )

            await self._store_activity(
                request.task.id,
                "progress",
                f"Validation completed - {validation_result.tests_passed} tests passed, {validation_result.tests_failed} failed",
                {"validation": validation_result.model_dump()},
            )

            # Step 7: Commit changes
            workflow.logger.info("Step 7: Committing changes")
            commit_message = self._generate_commit_message(request, implementation_plan)
            commit_result = await workflow.execute_activity(
                "commit_changes",
                args=[self.repo_path, commit_message],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                    backoff_coefficient=2.0,
                    maximum_attempts=3,
                ),
            )

            if not commit_result["success"]:
                raise RuntimeError(f"Failed to commit changes: {commit_result['error']}")

            commit_hash = commit_result.get("commit_hash")

            await self._send_notification(
                request,
                NotificationType.CHANGES_COMMITTED,
                f"Changes committed: {commit_hash}",
                {"commit_hash": commit_hash, "commit_message": commit_message},
            )

            await self._store_activity(
                request.task.id, "progress", f"Changes committed: {commit_hash}"
            )

            # Step 8: Push changes
            workflow.logger.info("Step 8: Pushing changes")
            push_result = await workflow.execute_activity(
                "push_changes",
                args=[
                    self.repo_path,
                    self.branch_name,
                    request.repository.remote_url,
                    request.repository.credentials.model_dump(),
                ],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=2),
                    maximum_interval=timedelta(minutes=1),
                    backoff_coefficient=2.0,
                    maximum_attempts=5,
                ),
            )

            if not push_result["success"]:
                raise RuntimeError(f"Failed to push changes: {push_result['error']}")

            await self._send_notification(
                request,
                NotificationType.CHANGES_PUSHED,
                f"Changes pushed to {self.branch_name}",
                {"branch_name": self.branch_name},
            )

            await self._store_activity(
                request.task.id, "progress", f"Changes pushed to remote branch: {self.branch_name}"
            )

            # Step 9: Calculate execution time
            end_time = datetime.fromtimestamp(workflow.time())
            execution_time_seconds = (end_time - start_time).total_seconds()
            execution_time_hours = execution_time_seconds / 3600

            # Step 10: Create success result
            result = CodingAgentResult(
                success=True,
                workflow_id=workflow_id,
                company_id=request.task.company_id,
                project_id=request.task.project_id,
                task_id=request.task.id,
                branch_name=self.branch_name or "unknown",
                commit_hash=commit_hash,
                implementation_plan=implementation_plan,
                steps_completed=self.implementation_steps,
                validation_result=validation_result,
                execution_time_hours=execution_time_hours,
                artifacts={
                    "llm_calls": self.llm_calls,
                    "temp_dir": self.temp_dir,
                },
            )

            # Step 11: Send completion notification
            await self._send_notification(
                request,
                NotificationType.WORKFLOW_COMPLETED,
                "Coding agent workflow completed successfully",
                result.model_dump(),
            )

            await self._store_activity(
                request.task.id,
                "progress",
                f"Workflow completed successfully in {execution_time_hours:.2f} hours",
                {"result": result.model_dump()},
            )

            # Step 12: Notify Elixir API (disabled for debug)
            # await self._notify_elixir(workflow_id, result.model_dump(), "completed")

            workflow.logger.info(
                f"CodingAgentWorkflow completed successfully - "
                f"Steps: {self.implementation_steps}, "
                f"LLM calls: {self.llm_calls}, "
                f"Time: {execution_time_hours:.2f}h"
            )

            return result

        except Exception as e:
            workflow.logger.error(f"CodingAgentWorkflow failed: {e}")

            # Calculate execution time
            end_time = datetime.fromtimestamp(workflow.time())
            execution_time_seconds = (end_time - start_time).total_seconds()
            execution_time_hours = execution_time_seconds / 3600

            # Create error result
            result = CodingAgentResult(
                success=False,
                workflow_id=workflow_id,
                company_id=request.task.company_id,
                project_id=request.task.project_id,
                task_id=request.task.id,
                branch_name=self.branch_name or "unknown",
                commit_hash=None,
                implementation_plan=None,
                steps_completed=self.implementation_steps,
                validation_result=None,
                error_message=str(e),
                execution_time_hours=execution_time_hours,
                artifacts={
                    "llm_calls": self.llm_calls,
                    "temp_dir": self.temp_dir,
                },
            )

            # Send failure notification
            await self._send_notification(
                request,
                NotificationType.WORKFLOW_FAILED,
                f"Workflow failed: {str(e)}",
                {"error": str(e)},
            )

            await self._store_activity(
                request.task.id, "error", f"Workflow failed: {str(e)}", {"error": str(e)}
            )

            # Notify Elixir API
            await self._notify_elixir(workflow_id, result.model_dump(), "failed")

            return result

        finally:
            # Cleanup temp directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                try:
                    shutil.rmtree(self.temp_dir)
                    workflow.logger.info(f"Cleaned up temp directory: {self.temp_dir}")
                except Exception as cleanup_error:
                    workflow.logger.warning(f"Failed to cleanup temp directory: {cleanup_error}")

    async def _generate_implementation_plan(
        self, request: CodingAgentRequest
    ) -> ImplementationPlan:
        """Generate implementation plan using LLM."""
        workflow.logger.info("Generating implementation plan with LLM")

        # Build context for the LLM
        system_message = """You are an expert software developer tasked with creating a detailed implementation plan.
Analyze the task and generate a step-by-step plan including:
1. Overall goal
2. Files that need to be created
3. Files that need to be modified
4. Implementation steps in logical order
5. Validation criteria

Respond with a JSON object in this exact format:
{
    "goal": "Overall implementation goal",
    "steps": ["step 1", "step 2", ...],
    "files_to_create": ["path/to/file1", ...],
    "files_to_modify": ["path/to/file2", ...],
    "estimated_steps": <number>,
    "validation_criteria": ["criterion 1", ...]
}"""

        task_context = f"""Task: {request.task.title}
Description: {request.task.description}
Requirements: {', '.join(request.task.requirements) if request.task.requirements else 'None specified'}
Tags: {', '.join(request.task.tags) if request.task.tags else 'None'}
"""

        # Add custom instructions if provided
        if request.agent.instructions:
            system_message += f"\n\nAdditional Instructions:\n{request.agent.instructions}"

        # Call LLM inference workflow
        llm_request = LLMInferenceRequest(
            model=request.agent.model,
            messages=[
                ChatMessage(role="system", content=system_message),
                ChatMessage(role="user", content=task_context),
            ],
            parameters=InferenceParameters(
                temperature=0.3,
                max_tokens=4000,
            ),
            credentials=OpenRouterCredentials(
                api_key=OPENROUTER_API_KEY
            ),
        )

        llm_result = await workflow.execute_child_workflow(
            LLMInferenceWorkflow.run,
            llm_request,
            id=f"{workflow.info().workflow_id}-plan-generation",
            task_queue="llm-inference",
        )

        self.llm_calls += 1

        # Parse response
        if llm_result.status != "completed" or not llm_result.response:
            raise RuntimeError("Failed to generate implementation plan")

        content = llm_result.response.choices[0].message.content

        # Extract JSON from response
        try:
            # Try to find JSON block in the response
            import re

            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                plan_data = json.loads(json_match.group())
            else:
                plan_data = json.loads(content)

            return ImplementationPlan(**plan_data)
        except json.JSONDecodeError as e:
            workflow.logger.error(f"Failed to parse LLM response: {e}")
            # Fallback to basic plan
            return ImplementationPlan(
                goal=request.task.title,
                steps=["Implement the task as described"],
                files_to_create=[],
                files_to_modify=[],
                estimated_steps=1,
                validation_criteria=["Implementation matches task description"],
            )

    async def _implement_changes(
        self, request: CodingAgentRequest, plan: ImplementationPlan
    ) -> dict[str, Any]:
        """Implement changes iteratively using LLM with function calling."""
        workflow.logger.info(f"Starting implementation with max {self.max_iterations} iterations")

        # Define function calling tools
        tools = self._get_function_tools()

        system_message = f"""You are an expert software developer implementing a task in a git repository.

Repository path: {self.repo_path}
Branch: {self.branch_name}

Task: {request.task.title}
Description: {request.task.description}
Requirements: {', '.join(request.task.requirements) if request.task.requirements else 'None specified'}

Implementation Plan:
{json.dumps(plan.model_dump(), indent=2)}

You have access to the following tools:
- run_shell_command: Execute shell commands in the repository
- read_file: Read file contents
- write_file: Create or modify files
- list_directory: List files and directories

Work through the implementation plan step by step. For each step:
1. Read relevant files to understand the code
2. Make necessary changes
3. Validate your changes
4. Move to the next step

When you have completed all steps, respond with "IMPLEMENTATION_COMPLETE"."""

        # Add custom instructions if provided
        if request.agent.instructions:
            system_message += f"\n\nAdditional Instructions:\n{request.agent.instructions}"

        messages = [
            ChatMessage(role="system", content=system_message),
            ChatMessage(role="user", content="Please start implementing the task."),
        ]

        for iteration in range(self.max_iterations):
            workflow.logger.info(f"Implementation iteration {iteration + 1}/{self.max_iterations}")

            await self._send_notification(
                request,
                NotificationType.IMPLEMENTATION_STEP,
                f"Implementation iteration {iteration + 1}",
                {"iteration": iteration + 1, "max_iterations": self.max_iterations},
            )

            # Call LLM with function calling
            llm_request = LLMInferenceRequest(
                model=request.agent.model,
                messages=messages,
                functions=tools,
                parameters=InferenceParameters(
                    temperature=0.2,
                    max_tokens=8000,
                ),
                credentials=OpenRouterCredentials(
                    api_key=OPENROUTER_API_KEY
                ),
            )

            llm_result = await workflow.execute_child_workflow(
                LLMInferenceWorkflow.run,
                llm_request,
                id=f"{workflow.info().workflow_id}-implementation-{iteration}",
                task_queue="llm-inference",
            )

            self.llm_calls += 1
            self.implementation_steps += 1

            if llm_result.status != "completed" or not llm_result.response:
                raise RuntimeError(f"LLM inference failed at iteration {iteration + 1}")

            choice = llm_result.response.choices[0]
            assistant_message = choice.message

            # Add assistant message to conversation
            messages.append(
                ChatMessage(
                    role="assistant",
                    content=assistant_message.content or "",
                    function_call=assistant_message.function_call,
                )
            )

            # Check if implementation is complete
            if (
                assistant_message.content
                and "IMPLEMENTATION_COMPLETE" in assistant_message.content
            ):
                workflow.logger.info("Implementation completed by agent")
                break

            # Handle function call
            if assistant_message.function_call:
                function_result = await self._execute_function(
                    request, assistant_message.function_call
                )

                # Add function result to conversation
                messages.append(
                    ChatMessage(
                        role="function",
                        name=assistant_message.function_call["name"],
                        content=json.dumps(function_result),
                    )
                )

        workflow.logger.info(
            f"Implementation completed after {self.implementation_steps} steps and {self.llm_calls} LLM calls"
        )

        return {"success": True, "iterations": self.implementation_steps}

    async def _execute_function(
        self, request: CodingAgentRequest, function_call: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a function call from the LLM."""
        function_name = function_call.get("name", "")
        arguments = json.loads(function_call.get("arguments", "{}"))

        workflow.logger.info(f"Executing function: {function_name}")

        # Store function call activity
        await self._store_activity(
            request.task.id,
            "function_call",
            f"Calling function: {function_name}",
            {"function": function_name, "arguments": arguments},
        )

        if function_name == "run_shell_command":
            result = await workflow.execute_activity(
                "run_shell_command",
                args=[self.repo_path, arguments["command"], arguments.get("timeout", 300)],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=30),
                    backoff_coefficient=2.0,
                    maximum_attempts=2,
                ),
            )

        elif function_name == "read_file":
            result = await workflow.execute_activity(
                "read_file_activity",
                args=[self.repo_path, arguments["file_path"]],
                start_to_close_timeout=timedelta(seconds=30),
            )

        elif function_name == "write_file":
            result = await workflow.execute_activity(
                "write_file_activity",
                args=[self.repo_path, arguments["file_path"], arguments["content"]],
                start_to_close_timeout=timedelta(minutes=2),
            )

        elif function_name == "list_directory":
            result = await workflow.execute_activity(
                "list_directory_activity",
                args=[self.repo_path, arguments.get("dir_path", ".")],
                start_to_close_timeout=timedelta(seconds=30),
            )

        else:
            result = {"success": False, "error": f"Unknown function: {function_name}"}

        return result

    async def _validate_changes(self, request: CodingAgentRequest) -> ValidationResult:
        """Validate implementation changes."""
        workflow.logger.info("Validating implementation changes")

        # Run basic validation commands
        validation_commands = [
            "git status",
            "git diff --stat",
        ]

        issues = []
        tests_passed = 0
        tests_failed = 0

        for cmd in validation_commands:
            result = await workflow.execute_activity(
                "run_shell_command",
                args=[self.repo_path, cmd, 60],
                start_to_close_timeout=timedelta(minutes=2),
            )

            if not result["success"]:
                issues.append(f"Command failed: {cmd}")

        # Try to run tests if they exist
        test_commands = ["npm test", "pytest", "go test ./...", "cargo test"]

        for test_cmd in test_commands:
            # Check if the command exists
            check_result = await workflow.execute_activity(
                "run_shell_command",
                args=[self.repo_path, f"which {test_cmd.split()[0]}", 5],
                start_to_close_timeout=timedelta(seconds=10),
            )

            if check_result["success"]:
                test_result = await workflow.execute_activity(
                    "run_shell_command",
                    args=[self.repo_path, test_cmd, 300],
                    start_to_close_timeout=timedelta(minutes=6),
                )

                if test_result["success"]:
                    tests_passed += 1
                else:
                    tests_failed += 1
                    issues.append(f"Tests failed: {test_cmd}")

                break  # Only run one test framework

        return ValidationResult(
            success=len(issues) == 0 and tests_failed == 0,
            issues=issues,
            suggestions=[],
            tests_passed=tests_passed,
            tests_failed=tests_failed,
        )

    def _get_function_tools(self) -> list[FunctionDefinition]:
        """Get function calling tools for the LLM."""
        return [
            FunctionDefinition(
                name="run_shell_command",
                description="Execute a shell command in the repository directory",
                parameters=[
                    FunctionParameter(
                        name="command",
                        type="string",
                        description="The shell command to execute",
                        required=True,
                    ),
                    FunctionParameter(
                        name="timeout",
                        type="integer",
                        description="Command timeout in seconds (default: 300)",
                        required=False,
                    ),
                ],
            ),
            FunctionDefinition(
                name="read_file",
                description="Read the contents of a file",
                parameters=[
                    FunctionParameter(
                        name="file_path",
                        type="string",
                        description="Relative path to the file within the repository",
                        required=True,
                    ),
                ],
            ),
            FunctionDefinition(
                name="write_file",
                description="Create or modify a file with the given content",
                parameters=[
                    FunctionParameter(
                        name="file_path",
                        type="string",
                        description="Relative path to the file within the repository",
                        required=True,
                    ),
                    FunctionParameter(
                        name="content",
                        type="string",
                        description="The content to write to the file",
                        required=True,
                    ),
                ],
            ),
            FunctionDefinition(
                name="list_directory",
                description="List files and directories in a path",
                parameters=[
                    FunctionParameter(
                        name="dir_path",
                        type="string",
                        description="Relative path to the directory (default: '.')",
                        required=False,
                    ),
                ],
            ),
        ]

    def _generate_commit_message(self, request: CodingAgentRequest, plan: ImplementationPlan) -> str:
        """Generate a commit message based on the task and implementation."""
        return f"""{request.task.title}

{request.task.description}

Implementation changes:
{chr(10).join(f"- {step}" for step in plan.steps[:5])}

Files created: {len(plan.files_to_create)}
Files modified: {len(plan.files_to_modify)}
"""

    async def _send_notification(
        self,
        request: CodingAgentRequest,
        notification_type: NotificationType,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Send notification to NATS server."""
        notification = WorkflowNotification(
            workflow_id=workflow.info().workflow_id,
            company_id=request.task.company_id,
            project_id=request.task.project_id,
            task_id=request.task.id,
            notification_type=notification_type,
            message=message,
            details=details or {},
            timestamp=workflow.now(),
        )

        await workflow.execute_activity(
            "send_nats_notification",
            args=[notification.model_dump()],
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=5),
                backoff_coefficient=2.0,
                maximum_attempts=3,
            ),
        )

    async def _store_activity(
        self,
        task_id: str,
        activity_type: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Store task activity in database."""
        await workflow.execute_activity(
            "store_task_activity",
            args=[task_id, activity_type, message, details],
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=5),
                backoff_coefficient=2.0,
                maximum_attempts=3,
            ),
        )

    async def _notify_elixir(
        self, workflow_id: str, result: dict[str, Any], status: str
    ) -> None:
        """Notify Elixir API about workflow completion or failure."""
        try:
            await workflow.execute_activity(
                "notify_elixir_api",
                args=[workflow_id, result, status],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                    backoff_coefficient=2.0,
                    maximum_attempts=3,
                ),
            )
        except Exception as e:
            # Don't fail the workflow if notification fails
            workflow.logger.warning(f"Failed to notify Elixir API: {e}")
