# LLM Inference Workflow

This workflow provides reliable LLM inference using OpenRouter API with support for various models, function calling, and comprehensive error handling.

## Features

- **Multiple Model Support**: Access to all OpenRouter models (Claude, GPT, Gemini, etc.)
- **Reliable Execution**: Built-in retry logic and error handling
- **Batch Processing**: Concurrent processing of multiple requests
- **Token Estimation**: Estimate token usage before making requests
- **Function Calling**: Support for tool/function calling (in full version)
- **Performance Monitoring**: Track execution time and token usage

## Quick Start

### 1. Set up OpenRouter API Key

```bash
export OPENROUTER_API_KEY="your-api-key-here"
```

Get your API key from [OpenRouter.ai](https://openrouter.ai/keys)

### 2. Start the Worker

```bash
uv run python workers/llm_inference_worker.py
```

### 3. Run Examples

```bash
# Simple test
uv run python examples/simple_llm_test.py

# Full demo
uv run python examples/llm_inference_demo.py
```

## Usage

### Basic Chat Completion

```python
from temporalio.client import Client

client = await Client.connect("localhost:7233")

request_data = {
    "model": "glm-4.6",
    "messages": [
        {"role": "user", "content": "What is the capital of France?"}
    ],
    "credentials": {"api_key": "your-api-key"},
    "parameters": {
        "temperature": 0.7,
        "max_tokens": 100
    }
}

result = await client.execute_workflow(
    "SimpleLLMInferenceWorkflow",
    request_data,
    id="chat-example",
    task_queue="llm-inference"
)

if result["status"] == "completed":
    print(f"Response: {result['content']}")
    print(f"Tokens used: {result['tokens_used']}")
```

### Batch Processing

```python
batch_data = {
    "requests": [
        {
            "model": "glm-4.6",
            "messages": [{"role": "user", "content": "What is 2+2?"}],
            "credentials": {"api_key": "your-api-key"},
            "parameters": {"max_tokens": 50}
        },
        {
            "model": "glm-4.6", 
            "messages": [{"role": "user", "content": "Capital of Spain?"}],
            "credentials": {"api_key": "your-api-key"},
            "parameters": {"max_tokens": 50}
        }
    ],
    "max_concurrent": 2
}

result = await client.execute_workflow(
    "SimpleBatchLLMWorkflow",
    batch_data,
    id="batch-example",
    task_queue="llm-inference"
)

print(f"Successful: {result['successful_requests']}")
print(f"Total tokens: {result['total_tokens_used']}")
```

## Request Format

### Required Fields

- `model`: Model name (e.g., "glm-4.6")
- `messages`: List of message objects
- `credentials`: Object with `api_key` field

### Message Format

```python
{
    "role": "user",  # "system", "user", "assistant", "function"
    "content": "Your message here",
    "name": "optional-name",  # Optional
    "function_call": {...}  # Optional for function calling
}
```

### Optional Parameters

- `temperature`: 0.0-2.0 (default: 0.7)
- `max_tokens`: Maximum tokens to generate
- `top_p`: 0.0-1.0 (default: 1.0)
- `top_k`: Top-k sampling
- `frequency_penalty`: -2.0 to 2.0
- `presence_penalty`: -2.0 to 2.0
- `stop`: Stop sequences
- `stream`: Whether to stream responses

## Available Models

Some popular models available on OpenRouter:

### OpenRouter Models
- `glm-4.6` - best coding model

## Response Format

```python
{
    "status": "completed",  # "completed" or "failed"
    "content": "The response text",
    "tokens_used": 25,
    "execution_time_ms": 1250,
    "finish_reason": "stop",  # "stop", "length", "function_call"
    "error_message": null  # Only present if failed
}
```

## Error Handling

The workflow includes comprehensive error handling:

- **Network Errors**: Automatic retry with exponential backoff
- **API Errors**: Proper error reporting with status codes
- **Authentication**: Clear error messages for invalid API keys
- **Model Validation**: Checks if model is available
- **Timeout Protection**: Prevents hanging requests

## Performance Considerations

### Token Usage
- Monitor token usage to control costs
- Use `max_tokens` to limit response length
- Consider token estimation for large requests

### Concurrency
- Batch processing supports up to 10 concurrent requests
- Adjust `max_concurrent` based on your rate limits
- Monitor OpenRouter rate limits

### Model Selection
- Use smaller models for simple tasks
- Reserve larger models for complex reasoning
- Consider cost vs. performance trade-offs

## Configuration

### Environment Variables

```bash
export OPENROUTER_API_KEY="your-api-key"
# Optional: Custom OpenRouter base URL
export OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"
```

### Worker Configuration

The worker can be configured with:

- `max_concurrent_activities`: Maximum concurrent LLM requests
- Task queue name: `llm-inference`
- Custom timeouts and retry policies

## Monitoring

### Metrics to Track

- **Token Usage**: Monitor costs per workflow
- **Execution Time**: Performance optimization
- **Error Rates**: Reliability monitoring
- **Model Performance**: Compare different models

### Logging

The workflow provides structured logging for:

- Request start/completion
- Token usage statistics
- Error details
- Performance metrics

## Security

### API Key Management

- Never hardcode API keys in code
- Use environment variables or secret management
- Rotate API keys regularly
- Monitor API key usage

### Data Privacy

- Be aware of OpenRouter's data usage policies
- Avoid sending sensitive information
- Consider data retention policies

## Troubleshooting

### Common Issues

1. **Authentication Error**
   - Check API key is valid
   - Ensure API key has sufficient credits

2. **Model Not Available**
   - Verify model name is correct
   - Check model availability on OpenRouter

3. **Rate Limiting**
   - Reduce concurrent requests
   - Implement backoff logic

4. **Timeout Errors**
   - Increase timeout for complex requests
   - Check network connectivity

### Debug Mode

Enable debug logging by setting log level to DEBUG in your worker configuration.

## Examples

See the `examples/` directory for complete working examples:

- `simple_llm_test.py` - Basic usage
- `llm_inference_demo.py` - Comprehensive demo
- `llm_inference_example.py` - Advanced features (full version)

## Integration

### With Other Workflows

LLM inference can be integrated into other workflows:

```python
# Inside another workflow
llm_result = await workflow.execute_child_workflow(
    "SimpleLLMInferenceWorkflow",
    request_data,
    id="nested-llm-call",
    task_queue="llm-inference"
)
```

### Function Calling

The full version supports function calling for tool integration:

```python
functions = [
    {
        "name": "get_weather",
        "description": "Get weather information",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            },
            "required": ["location"]
        }
    }
]
```

## Elixir API Integration

The LLM Inference Workflow automatically notifies your Elixir backend when workflows complete via webhook callback.

### Configuration

Set these environment variables:

```bash
# Webhook endpoint URL
ELIXIR_WEBHOOK_URL=http://localhost:4000/api/webhooks/workflows

# Webhook authentication secret
ELIXIR_WEBHOOK_SECRET=dev-webhook-secret-12345
```

### Webhook Payload

The workflow sends a POST request to `{ELIXIR_WEBHOOK_URL}/{workflow_id}`:

```json
{
  "status": "completed",
  "result": {
    "request": { /* original request */ },
    "response": { /* LLM response */ },
    "status": "completed",
    "execution_time_ms": 1234,
    "tokens_used": 567,
    "finish_reason": "stop"
  }
}
```

Headers:
```
Authorization: Bearer {ELIXIR_WEBHOOK_SECRET}
Content-Type: application/json
```

### Elixir Phoenix Endpoint Example

```elixir
defmodule MyAppWeb.WorkflowWebhookController do
  use MyAppWeb, :controller

  def handle_completion(conn, %{"workflow_id" => workflow_id} = params) do
    # Verify webhook secret
    with {:ok, _} <- verify_webhook_auth(conn),
         {:ok, result} <- Map.fetch(params, "result"),
         :ok <- process_workflow_result(workflow_id, result) do
      json(conn, %{success: true})
    else
      error ->
        conn
        |> put_status(:bad_request)
        |> json(%{error: inspect(error)})
    end
  end

  defp verify_webhook_auth(conn) do
    expected_secret = Application.get_env(:my_app, :webhook_secret)
    
    case get_req_header(conn, "authorization") do
      ["Bearer " <> ^expected_secret] -> {:ok, :verified}
      _ -> {:error, :unauthorized}
    end
  end

  defp process_workflow_result(workflow_id, result) do
    # Store result, update database, trigger next steps, etc.
    Logger.info("Workflow #{workflow_id} completed: #{inspect(result)}")
    :ok
  end
end
```

### Error Handling

The webhook notification is non-fatal. If it fails:
- The workflow will still complete successfully
- Retries are attempted (3 attempts with exponential backoff)
- Errors are logged but don't affect the workflow result

This ensures LLM inference reliability even if the Elixir backend is temporarily unavailable.

## Contributing

To extend the LLM inference workflow:

1. Add new activities to `shared/activities/llm.py`
2. Update workflow logic in `workflows/llm_inference/`
3. Add examples to demonstrate new features
4. Update documentation

## License

This workflow is part of the Automata Workflows project. See the main project license for details.