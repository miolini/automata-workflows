# Repository Indexing Workflow

This workflow fetches a repository from a remote URL using provided credentials, indexes its contents, and stores the metadata in a database for further analysis.

## Features

- **Repository Cloning**: Supports both public and private repositories with various authentication methods
- **Content Indexing**: Analyzes repository structure, counts lines of code, detects programming languages
- **Database Storage**: Persists repository metadata and file information in SQLite database
- **Batch Processing**: Supports indexing multiple repositories in parallel
- **Error Handling**: Comprehensive error handling with retry policies and cleanup
- **Scalable**: Built on Temporal.io for fault tolerance and scalability

## Authentication Methods

The workflow supports multiple authentication methods:

1. **Token-based Authentication**: Use personal access tokens for GitHub/GitLab
2. **Username/Password**: Basic authentication for HTTPS repositories
3. **SSH Key Authentication**: Use SSH keys for secure access

## Workflow Components

### Models

- `RepositoryInfo`: Repository metadata including URL, credentials, and branch information
- `RepositoryCredentials`: Authentication credentials for repository access
- `RepositoryIndex`: Indexed repository information including file counts and language statistics
- `RepositoryIndexingResult`: Workflow execution result with status and metrics

### Activities

1. **clone_repository**: Clones repository to temporary location
2. **index_repository**: Analyzes repository contents and extracts metadata
3. **save_to_database**: Persists repository index to database
4. **cleanup_repository**: Cleans up temporary files

### Workflows

1. **RepositoryIndexingWorkflow**: Single repository indexing
2. **BatchRepositoryIndexingWorkflow**: Multiple repository indexing

## Database Schema

The workflow creates two tables:

### repositories
- `id`: Repository unique identifier
- `name`: Repository name
- `owner`: Repository owner
- `remote_url`: Git remote URL
- `branch`: Branch name
- `commit_hash`: Current commit hash
- `file_count`: Number of files indexed
- `total_lines`: Total lines of code
- `languages`: JSON object with language statistics
- `indexed_at`: Indexing timestamp
- `file_paths`: JSON array of indexed file paths

### repository_files
- `id`: File record ID
- `repository_id`: Reference to repository
- `file_path`: Relative file path
- `file_hash`: File content hash
- `file_size`: File size in bytes
- `language`: Detected programming language
- `lines_count`: Number of lines in file
- `last_modified`: File modification timestamp

## Usage

### Single Repository Indexing

```python
from shared.models.github import RepositoryInfo, RepositoryCredentials

# Public repository
repo_info = RepositoryInfo(
    remote_url="https://github.com/octocat/Hello-World.git",
    name="Hello-World",
    owner="octocat",
    branch="master",
    credentials=None
)

# Private repository with token
private_repo = RepositoryInfo(
    remote_url="https://github.com/your-org/your-repo.git",
    name="your-repo",
    owner="your-org",
    branch="main",
    credentials=RepositoryCredentials(
        token="your-github-token"
    )
)
```

### Batch Repository Indexing

```python
repositories = [
    RepositoryInfo(
        remote_url="https://github.com/octocat/Hello-World.git",
        name="Hello-World",
        owner="octocat",
        branch="master",
        credentials=None
    ),
    RepositoryInfo(
        remote_url="https://github.com/octocat/Spoon-Knife.git",
        name="Spoon-Knife",
        owner="octocat",
        branch="main",
        credentials=None
    )
]
```

## Running the Workflow

### 1. Start Temporal Server

```bash
# Using Docker
docker-compose up -d

# Or download and run Temporal server
# https://docs.temporal.io/docs/server/quick-start
```

### 2. Start the Worker

```bash
python workers/repository_indexing_worker.py
```

### 3. Run the Example

```bash
python examples/repository_indexing_example.py
```

## Configuration

### Environment Variables

- `TEMPORAL_HOST_URL`: Temporal server URL (default: localhost:7233)
- `DATABASE_URL`: Database connection URL (default: sqlite+aiosqlite:///./repositories.db)

### Activity Timeouts

- `clone_repository`: 30 minutes
- `index_repository`: 15 minutes
- `save_to_database`: 5 minutes
- `cleanup_repository`: 2 minutes

### Retry Policies

Activities are configured with exponential backoff retry policies:

- Initial interval: 1-5 seconds
- Maximum interval: 30 seconds - 2 minutes
- Backoff coefficient: 2.0
- Maximum attempts: 2-5

## Security Considerations

1. **Credential Management**: Never hardcode credentials in code. Use environment variables or secret management systems.
2. **Temporary Files**: Repository clones are stored in `/tmp/automata_repos` and automatically cleaned up.
3. **Database Security**: Ensure proper access controls on the database file.
4. **Network Security**: Use HTTPS URLs when possible and validate SSL certificates.

## Performance Considerations

1. **File Size Limits**: Files larger than 10MB are skipped during indexing.
2. **Concurrent Processing**: Worker supports up to 10 concurrent activities.
3. **Memory Usage**: Large repositories are processed in streaming fashion to minimize memory usage.
4. **Database Indexing**: Proper indexes are created for efficient querying.

## Error Handling

The workflow includes comprehensive error handling:

- **Authentication Errors**: Non-retryable for invalid credentials
- **Network Errors**: Retryable with exponential backoff
- **Repository Not Found**: Non-retryable
- **Database Errors**: Retryable with limited attempts
- **File System Errors**: Logged but don't fail the workflow

## Monitoring and Logging

- Structured JSON logging with correlation IDs
- Workflow execution metrics and timing
- Activity success/failure rates
- Resource usage monitoring
- Database operation tracking

## Extending the Workflow

### Adding New Authentication Methods

1. Extend `RepositoryCredentials` model
2. Update `GitRepository.clone()` method
3. Add validation logic

### Adding New Analysis Features

1. Create new activities for specific analysis
2. Update `index_repository` activity
3. Extend database schema if needed
4. Update models accordingly

### Supporting New Repository Types

1. Add support for additional Git hosting services
2. Update URL parsing and authentication logic
3. Add service-specific features

## Troubleshooting

### Common Issues

1. **Authentication Failures**: Check token validity and permissions
2. **Network Timeouts**: Increase activity timeouts for large repositories
3. **Database Locks**: Ensure proper connection pooling
4. **Memory Issues**: Limit concurrent activities for large repositories

### Debug Mode

Enable debug logging by setting the log level:

```python
import structlog
structlog.configure(
    processors=[structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
```

## Examples

See `examples/repository_indexing_example.py` for complete usage examples including:

- Public repository indexing
- Private repository indexing with authentication
- Batch repository processing
- Error handling examples