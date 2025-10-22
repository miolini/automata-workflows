# GitHub Copilot Instructions for Automata Workflows

## Project Context

This is the Python workflow engine for the Automata platform, built on Temporal.io. Each workflow runs as a durable, fault-tolerant process that orchestrates complex multi-agent operations.

## Architecture Guidelines

### Workflow Structure
- Each workflow lives in its own directory under `workflows/`
- Workflows must be deterministic and idempotent
- Use activities for all external service calls
- Implement proper error handling with exponential backoff
- Design for long-running operations (hours to days)

### Code Patterns

#### Workflow Definition
```python
@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self, input: MyInput) -> MyOutput:
        # Workflow logic here
        pass
```

#### Activity Definition
```python
@activity.defn
async def my_activity(input: MyInput) -> MyOutput:
    # Activity logic here
    # Keep activities short-lived (< 5 minutes)
    pass
```

#### Error Handling
```python
try:
    result = await workflow.execute_activity(
        activity,
        input,
        start_to_close_timeout=timedelta(minutes=5),
        retry_policy=RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(minutes=1),
            backoff_coefficient=2.0,
            maximum_attempts=3
        )
    )
except Exception as e:
    # Handle error appropriately
    workflow.logger.error(f"Activity failed: {e}")
    raise
```

## Development Standards

### Python Version
- Use Python 3.14+ features (type hints, async/await, structural pattern matching, advanced typing)
- Follow PEP 8 style guidelines
- Use Black for code formatting
- Use isort for import sorting
- Leverage modern Python syntax and performance improvements

### Type Safety
- Use Pydantic models for all input/output data structures
- Implement strict type checking with mypy
- Use generic types where appropriate
- Document all public APIs with proper type hints

### Testing Requirements
- Unit tests for all activities (pytest)
- Integration tests for workflows (Temporal test environment)
- Mock external services in tests
- Achieve minimum 80% code coverage

### Logging Standards
- Use structured JSON logging
- Include correlation IDs for request tracing
- Log at appropriate levels (DEBUG, INFO, WARNING, ERROR)
- Never log sensitive data (PII, tokens, passwords)

## Workflow Categories

### Coding Automation Workflows
- Focus on software development processes
- Integrate with GitHub, GitLab, Jira
- Handle code review, PR management, CI/CD
- Generate documentation and reports

### ML Fine-Tuning Workflows
- Manage Modal.com integration
- Handle QLoRA adapter training
- Implement model evaluation pipelines
- Track training metrics and results

### Agent Orchestration Workflows
- Coordinate multiple AI agents
- Manage agent state and context
- Handle conflict resolution
- Implement task distribution logic

### Billing Workflows
- Track resource usage accurately
- Generate invoices and reports
- Handle subscription management
- Implement cost optimization

## Security Guidelines

### Credential Management
- Never hardcode secrets in code
- Use environment variables for configuration
- Implement proper secret rotation
- Audit all credential access

### Data Protection
- Encrypt sensitive data at rest and in transit
- Implement proper access controls
- Log all data access operations
- Follow GDPR and SOC 2 compliance

### Input Validation
- Validate all inputs using Pydantic models
- Sanitize external data before processing
- Implement rate limiting for external APIs
- Use parameterized queries for database operations

## Performance Guidelines

### Workflow Optimization
- Minimize workflow state size
- Use continue_as_new for long-running workflows
- Implement proper timeout handling
- Batch operations where possible

### Activity Performance
- Keep activities short and focused
- Use connection pooling for external services
- Implement circuit breakers for resilience
- Cache frequently accessed data

### Resource Management
- Use async/await for I/O operations
- Implement proper resource cleanup
- Monitor memory usage in long-running workflows
- Use streaming for large data processing

## Integration Patterns

### External Service Clients
- Implement retry logic with exponential backoff
- Use circuit breakers for fault tolerance
- Handle rate limiting gracefully
- Implement proper error mapping

### Database Operations
- Use connection pooling
- Implement transaction management
- Handle connection failures gracefully
- Use read replicas for read-heavy operations

### Message Queue Integration
- Implement at-least-once delivery semantics
- Handle duplicate message processing
- Use dead letter queues for failed messages
- Monitor queue depth and processing latency

## Monitoring and Observability

### Metrics Collection
- Track workflow execution duration
- Monitor activity success/failure rates
- Measure resource utilization
- Track business KPIs

### Health Checks
- Implement workflow health endpoints
- Monitor external service connectivity
- Track database connection health
- Implement proper alerting

### Debugging Support
- Include correlation IDs in all logs
- Implement workflow tracing
- Provide debugging endpoints
- Use structured logging for analysis

## Deployment Considerations

### Configuration Management
- Use environment-specific configurations
- Implement feature flags
- Support configuration hot-reloading
- Validate configuration on startup

### Scalability
- Design for horizontal scaling
- Implement proper load balancing
- Use worker pools for activity processing
- Monitor resource utilization

### Reliability
- Implement graceful shutdown
- Handle database connection failures
- Support rolling deployments
- Implement proper backup and recovery

## Code Review Guidelines

### Review Checklist
- [ ] Workflow is deterministic and idempotent
- [ ] Proper error handling with retries
- [ ] No hardcoded secrets or credentials
- [ ] Comprehensive test coverage
- [ ] Proper logging and monitoring
- [ ] Type hints and documentation
- [ ] Security best practices followed
- [ ] Performance considerations addressed

### Approval Process
- All workflows require peer review
- Security-sensitive changes require security team review
- Performance-critical changes require performance team review
- Breaking changes require architecture team approval

## Common Pitfalls to Avoid

### Workflow Anti-patterns
- Don't make external API calls directly in workflows
- Don't use time-dependent logic in workflows
- Don't rely on global state in workflows
- Don't create infinite loops without proper termination

### Activity Anti-patterns
- Don't make activities long-running (> 5 minutes)
- Don't implement retry logic manually (use Temporal's retry policy)
- Don't ignore activity timeouts
- Don't mix synchronous and asynchronous code

### Testing Anti-patterns
- Don't test against production services
- Don't ignore flaky tests
- Don't skip integration tests
- Don't mock Temporal framework itself

## Resources and References

### Documentation
- [Temporal Python SDK Documentation](https://docs.temporal.io/dev-guide/python)
- [Automata Platform Architecture](https://confluence.sentientwave.com/display/AUT)
- [Internal Development Guidelines](https://confluence.sentientwave.com/display/DEV)

### Tools and Libraries
- temporalio: Temporal Python SDK
- pydantic: Data validation and serialization
- asyncpg: Async PostgreSQL driver
- httpx: Async HTTP client
- structlog: Structured logging

### Internal Resources
- Slack: #automata-workflows
- Jira: AUT project
- Confluence: Automata Workflows space
- PagerDuty: Automata-Workflows rotation