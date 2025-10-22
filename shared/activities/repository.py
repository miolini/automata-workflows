"""
Repository management activities for Automata Workflows
"""

import asyncio
import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from temporalio import activity

from shared.models.github import (
    RepositoryCredentials,
    RepositoryIndex,
    RepositoryInfo,
)

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """Database manager for repository indexing."""

    def __init__(self, database_url: str = "sqlite+aiosqlite:///./repositories.db"):
        self.database_url = database_url
        self.engine = create_async_engine(database_url)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession)

    async def init_database(self):
        """Initialize database tables."""
        from sqlalchemy import text

        async with self.engine.begin() as conn:
            await conn.execute(
                text(
                    """
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
                    indexed_at TIMESTAMP NOT NULL,
                    file_paths TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                )
            )

            await conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS repository_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repository_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    language TEXT,
                    lines_count INTEGER,
                    last_modified TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (repository_id) REFERENCES repositories (id)
                )
            """
                )
            )

            await conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_repositories_owner_name ON repositories (owner, name)
            """
                )
            )

            await conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_repository_files_repository_id ON repository_files (repository_id)
            """
                )
            )

    async def save_repository_index(self, repo_index: RepositoryIndex) -> str:
        """Save repository index to database."""
        async with self.session_factory() as session:
            # Convert languages dict to JSON string
            import json

            languages_json = json.dumps(repo_index.languages)
            file_paths_json = json.dumps(repo_index.file_paths)

            # Check if repository already exists
            result = await session.execute(
                select(text("id")).where(text("id = :repo_id")),
                {"repo_id": repo_index.repository_id},
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing repository
                await session.execute(
                    text(
                        """
                        UPDATE repositories
                        SET name = :name, owner = :owner, remote_url = :remote_url,
                            branch = :branch, commit_hash = :commit_hash, file_count = :file_count,
                            total_lines = :total_lines, languages = :languages, indexed_at = :indexed_at,
                            file_paths = :file_paths, updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                    """
                    ),
                    {
                        "id": repo_index.repository_id,
                        "name": repo_index.name,
                        "owner": repo_index.owner,
                        "remote_url": repo_index.remote_url,
                        "branch": repo_index.branch,
                        "commit_hash": repo_index.commit_hash,
                        "file_count": repo_index.file_count,
                        "total_lines": repo_index.total_lines,
                        "languages": languages_json,
                        "indexed_at": repo_index.indexed_at,
                        "file_paths": file_paths_json,
                    },
                )
            else:
                # Insert new repository
                await session.execute(
                    text(
                        """
                        INSERT INTO repositories
                        (id, name, owner, remote_url, branch, commit_hash, file_count,
                         total_lines, languages, indexed_at, file_paths)
                        VALUES
                        (:id, :name, :owner, :remote_url, :branch, :commit_hash, :file_count,
                         :total_lines, :languages, :indexed_at, :file_paths)
                    """
                    ),
                    {
                        "id": repo_index.repository_id,
                        "name": repo_index.name,
                        "owner": repo_index.owner,
                        "remote_url": repo_index.remote_url,
                        "branch": repo_index.branch,
                        "commit_hash": repo_index.commit_hash,
                        "file_count": repo_index.file_count,
                        "total_lines": repo_index.total_lines,
                        "languages": languages_json,
                        "indexed_at": repo_index.indexed_at,
                        "file_paths": file_paths_json,
                    },
                )

            await session.commit()
            return repo_index.repository_id


class GitRepository:
    """Git repository operations."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    async def clone(
        self,
        remote_url: str,
        credentials: RepositoryCredentials | None = None,
        branch: str = "main",
    ):
        """Clone a repository."""
        # Prepare clone URL with credentials if provided
        clone_url = remote_url

        if credentials:
            if credentials.token:
                # For HTTPS with token
                if remote_url.startswith("https://"):
                    clone_url = remote_url.replace(
                        "https://", f"https://{credentials.token}@"
                    )
            elif credentials.username and credentials.password:
                # For HTTPS with username/password
                if remote_url.startswith("https://"):
                    clone_url = remote_url.replace(
                        "https://",
                        f"https://{credentials.username}:{credentials.password}@",
                    )
            elif credentials.ssh_key_path or credentials.ssh_key_content:
                # For SSH, we'll use environment variables
                env = os.environ.copy()
                if credentials.ssh_key_path:
                    env["GIT_SSH_COMMAND"] = f"ssh -i {credentials.ssh_key_path}"
                elif credentials.ssh_key_content:
                    # Create temporary SSH key file
                    ssh_key_file = (
                        self.repo_path.parent
                        / f"ssh_key_{hashlib.md5(credentials.ssh_key_content.encode()).hexdigest()}"
                    )
                    ssh_key_file.write_text(credentials.ssh_key_content)
                    ssh_key_file.chmod(0o600)
                    env["GIT_SSH_COMMAND"] = f"ssh -i {ssh_key_file}"

                # Clone with SSH environment
                cmd = [
                    "git",
                    "clone",
                    "--branch",
                    branch,
                    clone_url,
                    str(self.repo_path),
                ]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    raise Exception(f"Failed to clone repository: {stderr.decode()}")

                return

        # Standard clone without special authentication
        cmd = ["git", "clone", "--branch", branch, clone_url, str(self.repo_path)]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"Failed to clone repository: {stderr.decode()}")

    async def get_current_commit(self) -> str:
        """Get the current commit hash."""
        cmd = ["git", "rev-parse", "HEAD"]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=self.repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"Failed to get commit hash: {stderr.decode()}")

        return stdout.decode().strip()

    async def get_file_list(self) -> list[str]:
        """Get list of all files in the repository."""
        cmd = ["git", "ls-files"]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=self.repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"Failed to get file list: {stderr.decode()}")

        return [line.strip() for line in stdout.decode().splitlines() if line.strip()]

    def cleanup(self):
        """Clean up repository directory."""
        if self.repo_path.exists():
            shutil.rmtree(self.repo_path)


def detect_language(file_path: str) -> str | None:
    """Detect programming language based on file extension."""
    extension_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".java": "Java",
        ".cpp": "C++",
        ".c": "C",
        ".cs": "C#",
        ".go": "Go",
        ".rs": "Rust",
        ".php": "PHP",
        ".rb": "Ruby",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".scala": "Scala",
        ".r": "R",
        ".sql": "SQL",
        ".html": "HTML",
        ".css": "CSS",
        ".scss": "SCSS",
        ".sass": "Sass",
        ".less": "Less",
        ".xml": "XML",
        ".json": "JSON",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".toml": "TOML",
        ".md": "Markdown",
        ".txt": "Text",
        ".sh": "Shell",
        ".bash": "Bash",
        ".zsh": "Zsh",
        ".fish": "Fish",
        ".ps1": "PowerShell",
        ".dockerfile": "Docker",
        ".dockerignore": "Docker",
        ".gitignore": "Git",
        ".gitattributes": "Git",
    }

    ext = Path(file_path).suffix.lower()
    return extension_map.get(ext)


async def count_lines_in_file(file_path: Path) -> int:
    """Count lines in a file."""
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


@activity.defn
async def clone_repository(input: RepositoryInfo) -> str:
    """
    Clone a repository to a temporary location.

    Args:
        input: Repository information including URL and credentials

    Returns:
        str: Path to the cloned repository
    """
    activity.logger.info(f"Cloning repository {input.remote_url}")

    # Create temporary directory for cloning
    temp_dir = Path("/tmp/automata_repos")
    temp_dir.mkdir(exist_ok=True)

    # Create unique directory name
    repo_name = input.name.replace("/", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    repo_path = temp_dir / f"{repo_name}_{timestamp}"

    try:
        git_repo = GitRepository(repo_path)
        await git_repo.clone(input.remote_url, input.credentials, input.branch)

        activity.logger.info(f"Successfully cloned repository to {repo_path}")
        return str(repo_path)

    except Exception as e:
        # Clean up on failure
        if repo_path.exists():
            shutil.rmtree(repo_path)
        activity.logger.error(f"Failed to clone repository: {e}")
        raise


@activity.defn
async def index_repository(
    repo_path: str, repository_info: RepositoryInfo
) -> RepositoryIndex:
    """
    Index a cloned repository and extract metadata.

    Args:
        repo_path: Path to the cloned repository
        repository_info: Original repository information

    Returns:
        RepositoryIndex: Indexed repository information
    """
    activity.logger.info(f"Indexing repository at {repo_path}")

    repo_path_obj = Path(repo_path)
    git_repo = GitRepository(repo_path_obj)

    try:
        # Get current commit
        commit_hash = await git_repo.get_current_commit()

        # Get file list
        file_paths = await git_repo.get_file_list()

        # Analyze files
        languages: dict[str, int] = {}
        total_lines = 0
        valid_files = []

        for file_path in file_paths:
            full_path = repo_path_obj / file_path

            # Skip if file doesn't exist or is not a file
            if not full_path.is_file():
                continue

            # Skip binary files and very large files
            if full_path.stat().st_size > 10 * 1024 * 1024:  # 10MB
                continue

            # Detect language
            language = detect_language(file_path)
            if language:
                languages[language] = languages.get(language, 0) + 1

            # Count lines
            lines = await count_lines_in_file(full_path)
            total_lines += lines

            valid_files.append(file_path)

        # Create repository ID
        repo_id = f"{repository_info.owner}_{repository_info.name}_{commit_hash[:8]}"

        # Create repository index
        repo_index = RepositoryIndex(
            repository_id=repo_id,
            name=repository_info.name,
            owner=repository_info.owner,
            remote_url=repository_info.remote_url,
            branch=repository_info.branch,
            commit_hash=commit_hash,
            file_count=len(valid_files),
            total_lines=total_lines,
            languages=languages,
            file_paths=valid_files,
            indexed_at=datetime.now(),
        )

        activity.logger.info(
            f"Successfully indexed repository: {len(valid_files)} files, {total_lines} lines"
        )
        return repo_index

    except Exception as e:
        activity.logger.error(f"Failed to index repository: {e}")
        raise


@activity.defn
async def save_to_database(repo_index: RepositoryIndex) -> str:
    """
    Save repository index to database.

    Args:
        repo_index: Repository index to save

    Returns:
        str: Repository ID
    """
    activity.logger.info(f"Saving repository {repo_index.repository_id} to database")

    try:
        db_manager = DatabaseManager()
        await db_manager.init_database()

        repo_id = await db_manager.save_repository_index(repo_index)

        activity.logger.info(f"Successfully saved repository to database: {repo_id}")
        return repo_id

    except Exception as e:
        activity.logger.error(f"Failed to save to database: {e}")
        raise


@activity.defn
async def cleanup_repository(repo_path: str) -> None:
    """
    Clean up cloned repository.

    Args:
        repo_path: Path to the cloned repository
    """
    activity.logger.info(f"Cleaning up repository at {repo_path}")

    try:
        repo_path_obj = Path(repo_path)
        if repo_path_obj.exists():
            shutil.rmtree(repo_path_obj)
            activity.logger.info("Successfully cleaned up repository")

    except Exception as e:
        activity.logger.warning(f"Failed to cleanup repository: {e}")
