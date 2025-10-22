"""
Repository Indexing Workflow

This workflow fetches a repository from a remote URL, indexes its contents, 
and stores the metadata in a database.
"""

from datetime import timedelta
from typing import Dict, Any, Optional
from pathlib import Path

from temporalio import workflow, activity
from temporalio.common import RetryPolicy


@activity.defn
async def clone_repository(input_data: Dict[str, Any]) -> str:
    """Clone repository activity."""
    import tempfile
    import subprocess
    from pathlib import Path
    import structlog
    
    logger = structlog.get_logger(__name__)
    
    repo_url = input_data["remote_url"]
    branch = input_data.get("branch", "main")
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix="repo_"))
    
    try:
        # Clone repository
        result = subprocess.run([
            "git", "clone", "--depth", "1", "--branch", branch, repo_url, str(temp_dir)
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise Exception(f"Failed to clone repository: {result.stderr}")
        
        logger.info(f"Successfully cloned repository to {temp_dir}")
        return str(temp_dir)
        
    except Exception as e:
        # Cleanup on failure
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise e


@activity.defn
async def index_repository(repo_path: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Index repository activity."""
    import subprocess
    from pathlib import Path
    import os
    import structlog
    
    logger = structlog.get_logger(__name__)
    repo_path_obj = Path(repo_path)
    
    try:
        # Get commit hash
        result = subprocess.run([
            "git", "rev-parse", "HEAD"
        ], cwd=repo_path_obj, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Failed to get commit hash: {result.stderr}")
        
        commit_hash = result.stdout.strip()
        
        # Get file list
        result = subprocess.run([
            "git", "ls-files"
        ], cwd=repo_path_obj, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Failed to get file list: {result.stderr}")
        
        file_paths = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        
        # Analyze files
        languages = {}
        total_lines = 0
        valid_files = []
        
        for file_path in file_paths:
            full_path = repo_path_obj / file_path
            
            if not full_path.is_file():
                continue
            
            # Skip large files
            if full_path.stat().st_size > 10 * 1024 * 1024:  # 10MB
                continue
            
            # Detect language
            ext = Path(file_path).suffix.lower()
            language_map = {
                '.py': 'Python',
                '.js': 'JavaScript',
                '.ts': 'TypeScript',
                '.java': 'Java',
                '.cpp': 'C++',
                '.c': 'C',
                '.cs': 'C#',
                '.go': 'Go',
                '.rs': 'Rust',
                '.php': 'PHP',
                '.rb': 'Ruby',
            }
            
            language = language_map.get(ext)
            if language:
                languages[language] = languages.get(language, 0) + 1
            
            # Count lines
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = sum(1 for _ in f)
                    total_lines += lines
            except Exception:
                pass
            
            valid_files.append(file_path)
        
        # Create repository index data
        repo_index = {
            "repository_id": f"{input_data['owner']}_{input_data['name']}_{commit_hash[:8]}",
            "name": input_data["name"],
            "owner": input_data["owner"],
            "remote_url": input_data["remote_url"],
            "branch": input_data.get("branch", "main"),
            "commit_hash": commit_hash,
            "file_count": len(valid_files),
            "total_lines": total_lines,
            "languages": languages,
            "file_paths": valid_files,
        }
        
        import structlog
        logger = structlog.get_logger(__name__)
        logger.info(f"Successfully indexed repository: {len(valid_files)} files, {total_lines} lines")
        return repo_index
        
    except Exception as e:
        logger.error(f"Failed to index repository: {e}")
        raise e


@activity.defn
async def save_to_database(repo_index: Dict[str, Any]) -> str:
    """Save to database activity."""
    import json
    import sqlite3
    from datetime import datetime
    import structlog
    
    logger = structlog.get_logger(__name__)
    
    db_path = "repositories.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                owner TEXT NOT NULL,
                remote_url TEXT NOT NULL,
                branch TEXT NOT NULL,
                commit_hash TEXT NOT NULL,
                file_count INTEGER NOT NULL,
                total_lines INTEGER NOT NULL,
                languages TEXT NOT NULL,
                file_paths TEXT NOT NULL,
                indexed_at TIMESTAMP NOT NULL
            )
        """)
        
        # Insert or update repository
        cursor.execute("""
            INSERT OR REPLACE INTO repositories 
            (id, name, owner, remote_url, branch, commit_hash, file_count, 
             total_lines, languages, file_paths, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            repo_index["repository_id"],
            repo_index["name"],
            repo_index["owner"],
            repo_index["remote_url"],
            repo_index["branch"],
            repo_index["commit_hash"],
            repo_index["file_count"],
            repo_index["total_lines"],
            json.dumps(repo_index["languages"]),
            json.dumps(repo_index["file_paths"]),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully saved repository to database: {repo_index['repository_id']}")
        return repo_index["repository_id"]
        
    except Exception as e:
        logger.error(f"Failed to save to database: {e}")
        raise e


@activity.defn
async def cleanup_repository(repo_path: str) -> None:
    """Cleanup repository activity."""
    import shutil
    from pathlib import Path
    import structlog
    
    logger = structlog.get_logger(__name__)
    
    try:
        repo_path_obj = Path(repo_path)
        if repo_path_obj.exists():
            shutil.rmtree(repo_path_obj)
            logger.info(f"Successfully cleaned up repository")
    except Exception as e:
        logger.warning(f"Failed to cleanup repository: {e}")


@workflow.defn
class RepositoryIndexingWorkflow:
    """Working repository indexing workflow using dict-based data."""

    @workflow.run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the repository indexing process.
        
        Args:
            input_data: Repository information as dict
            
        Returns:
            Dict with indexing result
        """
        start_timestamp = workflow.time()
        workflow.logger.info(f"Starting repository indexing for {input_data.get('owner', 'unknown')}/{input_data.get('name', 'unknown')}")
        
        repo_path: Optional[str] = None
        repository_index = None
        
        try:
            # Step 1: Clone the repository
            workflow.logger.info("Step 1: Cloning repository")
            repo_path = await workflow.execute_activity(
                clone_repository,
                input_data,
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    maximum_interval=timedelta(minutes=2),
                    backoff_coefficient=2.0,
                    maximum_attempts=3,
                )
            )
            
            # Step 2: Index the repository contents
            workflow.logger.info("Step 2: Indexing repository contents")
            repository_index = await workflow.execute_activity(
                index_repository,
                args=[repo_path, input_data],
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=2),
                    maximum_interval=timedelta(minutes=1),
                    backoff_coefficient=2.0,
                    maximum_attempts=3
                )
            )
            
            # Step 3: Save to database
            workflow.logger.info("Step 3: Saving to database")
            saved_repo_id = await workflow.execute_activity(
                save_to_database,
                args=[repository_index],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=30),
                    backoff_coefficient=2.0,
                    maximum_attempts=5
                )
            )
            
            # Calculate execution time
            end_timestamp = workflow.time()
            execution_time_ms = int((end_timestamp - start_timestamp) * 1000)
            
            # Create successful result
            result = {
                "repository_info": input_data,
                "repository_index": repository_index,
                "status": "completed",
                "execution_time_ms": execution_time_ms,
                "files_processed": repository_index["file_count"],
                "files_skipped": 0,
                "saved_repo_id": saved_repo_id
            }
            
            workflow.logger.info(
                f"Repository indexing completed successfully. "
                f"Repository ID: {saved_repo_id}, "
                f"Files processed: {repository_index['file_count']}, "
                f"Total lines: {repository_index['total_lines']}, "
                f"Execution time: {execution_time_ms}ms"
            )
            
            return result
            
        except Exception as e:
            # Calculate execution time even for failures
            end_timestamp = workflow.time()
            execution_time_ms = int((end_timestamp - start_timestamp) * 1000)
            
            # Create error result
            result = {
                "repository_info": input_data,
                "repository_index": repository_index,
                "status": "failed",
                "error_message": str(e),
                "execution_time_ms": execution_time_ms,
                "files_processed": repository_index["file_count"] if repository_index else 0,
                "files_skipped": 0,
            }
            
            workflow.logger.error(
                f"Repository indexing failed: {e}. "
                f"Execution time: {execution_time_ms}ms"
            )
            
            # Re-raise the exception to mark workflow as failed
            raise
            
        finally:
            # Step 4: Cleanup (always run this, even on failure)
            if repo_path:
                try:
                    workflow.logger.info("Step 4: Cleaning up repository")
                    await workflow.execute_activity(
                        cleanup_repository,
                        args=[repo_path],
                        start_to_close_timeout=timedelta(minutes=2),
                        retry_policy=RetryPolicy(
                            initial_interval=timedelta(seconds=1),
                            maximum_attempts=2
                        )
                    )
                except Exception as cleanup_error:
                    workflow.logger.warning(f"Failed to cleanup repository: {cleanup_error}")