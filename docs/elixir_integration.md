# Calling Temporal Workflows from Elixir/Phoenix Backend

This document outlines the best approaches for integrating the Automata Workflows Temporal system with an Elixir/Phoenix backend.

## Option 1: Direct Temporal Client (Recommended)

### 1.1 Add Dependencies

Add to your `mix.exs`:

```elixir
defp deps do
  [
    # Phoenix dependencies...
    {:temporal_client, "~> 0.1.0"},
    {:grpc, "~> 0.5"},
    {:jason, "~> 1.4"},
    {:tesla, "~> 1.7"}  # For HTTP calls
  ]
end
```

### 1.2 Create Temporal Client Module

```elixir
# lib/your_app/temporal_client.ex
defmodule YourApp.TemporalClient do
  @moduledoc """
  Temporal client for workflow execution.
  """

  use GenServer
  require Logger

  @default_host "localhost:7233"
  @default_namespace "default"

  # Client API

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def run_llm_inference(request_data, opts \\ []) do
    GenServer.call(__MODULE__, {:run_workflow, "llm_inference", request_data, opts})
  end

  def get_workflow_status(workflow_id, opts \\ []) do
    GenServer.call(__MODULE__, {:get_workflow_status, workflow_id, opts})
  end

  # Server Callbacks

  @impl true
  def init(opts) do
    host = Keyword.get(opts, :host, @default_host)
    namespace = Keyword.get(opts, :namespace, @default_namespace)
    
    state = %{
      host: host,
      namespace: namespace,
      connection: nil
    }
    
    {:ok, state}
  end

  @impl true
  def handle_call({:run_workflow, workflow_type, request_data, opts}, _from, state) do
    task_queue = Keyword.get(opts, :task_queue, "automata-workflows")
    
    case execute_workflow(state.host, state.namespace, workflow_type, task_queue, request_data) do
      {:ok, result} ->
        {:reply, {:ok, result}, state}
      {:error, reason} ->
        {:reply, {:error, reason}, state}
    end
  end

  @impl true
  def handle_call({:get_workflow_status, workflow_id, opts}, _from, state) do
    case get_workflow_execution(state.host, state.namespace, workflow_id) do
      {:ok, status} ->
        {:reply, {:ok, status}, state}
      {:error, reason} ->
        {:reply, {:error, reason}, state}
    end
  end

  # Private Functions

  defp execute_workflow(host, namespace, workflow_type, task_queue, request_data) do
    url = "http://#{host}/api/namespaces/#{namespace}/workflows/run"
    
    headers = [
      {"Content-Type", "application/json"}
    ]
    
    body = %{
      workflowType: workflow_type,
      taskQueue: task_queue,
      input: request_data
    }
    
    case Tesla.post(url, Jason.encode!(body), headers: headers) do
      {:ok, %Tesla.Env{status: 200, body: response_body}} ->
        {:ok, response_body}
      {:ok, %Tesla.Env{status: status, body: body}} ->
        Logger.error("Workflow execution failed: #{status} - #{inspect(body)}")
        {:error, %{status: status, body: body}}
      {:error, reason} ->
        Logger.error("HTTP request failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  defp get_workflow_execution(host, namespace, workflow_id) do
    url = "http://#{host}/api/namespaces/#{namespace}/workflows/#{workflow_id}"
    
    case Tesla.get(url) do
      {:ok, %Tesla.Env{status: 200, body: response_body}} ->
        {:ok, response_body}
      {:ok, %Tesla.Env{status: status, body: body}} ->
        {:error, %{status: status, body: body}}
      {:error, reason} ->
        {:error, reason}
    end
  end
end
```

### 1.3 Create Phoenix Context

```elixir
# lib/your_app/automata.ex
defmodule YourApp.Automata do
  @moduledoc """
  Context for interacting with Automata workflows.
  """

  alias YourApp.TemporalClient

  @doc """
  Run LLM inference workflow.
  """
  def run_llm_inference(model, messages, opts \\ []) do
    request_data = %{
      "model" => model,
      "messages" => messages,
      "parameters" => %{
        "max_tokens" => Keyword.get(opts, :max_tokens, 16384),
        "temperature" => Keyword.get(opts, :temperature, 0.7)
      }
    }
    
    TemporalClient.run_llm_inference(request_data, opts)
  end

  @doc """
  Run LLM inference with a simple prompt.
  """
  def run_llm_inference_simple(prompt, opts \\ []) do
    model = Keyword.get(opts, :model, "z-ai/glm-4.6")
    
    messages = [
      %{
        "role" => "user",
        "content" => prompt
      }
    ]
    
    run_llm_inference(model, messages, opts)
  end

  @doc """
  Check workflow execution status.
  """
  def workflow_status(workflow_id) do
    TemporalClient.get_workflow_status(workflow_id)
  end
end
```

### 1.4 Create Phoenix Controller

```elixir
# lib/your_app_web/controllers/api/automata_controller.ex
defmodule YourAppWeb.Api.AutomataController do
  use YourAppWeb, :controller

  alias YourApp.Automata

  defp handle_error(conn, error) do
    conn
    |> put_status(:internal_server_error)
    |> json(%{error: error})
  end

  @doc """
  POST /api/automata/llm_inference
  """
  def llm_inference(conn, %{"prompt" => prompt} = params) do
    opts = [
      max_tokens: Map.get(params, "max_tokens", 16384),
      temperature: Map.get(params, "temperature", 0.7),
      model: Map.get(params, "model", "z-ai/glm-4.6")
    ]
    
    case Automata.run_llm_inference_simple(prompt, opts) do
      {:ok, result} ->
        conn
        |> put_status(:accepted)
        |> json(%{
          workflow_id: result["runId"],
          status: "started",
          message: "LLM inference workflow started"
        })
      
      {:error, reason} ->
        handle_error(conn, reason)
    end
  end

  @doc """
  POST /api/automata/llm_inference/detailed
  """
  def llm_inference_detailed(conn, %{"model" => model, "messages" => messages} = params) do
    opts = [
      max_tokens: Map.get(params, "max_tokens", 16384),
      temperature: Map.get(params, "temperature", 0.7)
    ]
    
    case Automata.run_llm_inference(model, messages, opts) do
      {:ok, result} ->
        conn
        |> put_status(:accepted)
        |> json(%{
          workflow_id: result["runId"],
          status: "started",
          message: "LLM inference workflow started"
        })
      
      {:error, reason} ->
        handle_error(conn, reason)
    end
  end

  @doc """
  GET /api/automata/workflow/:id/status
  """
  def workflow_status(conn, %{"id" => workflow_id}) do
    case Automata.workflow_status(workflow_id) do
      {:ok, status} ->
        conn
        |> json(%{
          workflow_id: workflow_id,
          status: status,
          execution_info: extract_execution_info(status)
        })
      
      {:error, reason} ->
        handle_error(conn, reason)
    end
  end

  defp extract_execution_info(status) do
    %{
      workflow_type: status["workflowType"]["name"],
      status: status["status"]["value"],
      start_time: status["status"]["timestamp"],
      completion_time: status.get("closeTime"),
      result: status.get("result")
    }
  end
end
```

### 1.5 Add Routes

```elixir
# lib/your_app_web/router.ex
defmodule YourAppWeb.Router do
  use YourAppWeb, :router

  pipeline :api do
    plug :accepts, ["json"]
  end

  scope "/api", YourAppWeb do
    pipe_through :api

    post "/automata/llm_inference", Api.AutomataController, :llm_inference
    post "/automata/llm_inference/detailed", Api.AutomataController, :llm_inference_detailed
    get "/automata/workflow/:id/status", Api.AutomataController, :workflow_status
  end
end
```

## Option 2: HTTP Client with Webhooks (Alternative)

### 2.1 Simple HTTP Client

```elixir
# lib/your_app/automata_http.ex
defmodule YourApp.AutomataHTTP do
  @moduledoc """
  Simple HTTP client for Temporal workflows.
  """

  @temporal_host "localhost:7233"
  @temporal_namespace "default"

  def run_llm_inference(prompt, opts \\ []) do
    url = "http://#{@temporal_host}/api/namespaces/#{@temporal_namespace}/workflows/run"
    
    request_data = %{
      "workflowType" => "llm_inference",
      "taskQueue" => "automata-workflows",
      "input" => %{
        "model" => Keyword.get(opts, :model, "z-ai/glm-4.6"),
        "messages" => [
          %{
            "role" => "user",
            "content" => prompt
          }
        ],
        "parameters" => %{
          "max_tokens" => Keyword.get(opts, :max_tokens, 16384),
          "temperature" => Keyword.get(opts, :temperature, 0.7)
        }
      }
    }
    
    headers = [
      {"Content-Type", "application/json"}
    ]
    
    case Tesla.post(url, Jason.encode!(request_data), headers: headers) do
      {:ok, %Tesla.Env{status: 200, body: body}} ->
        {:ok, body}
      {:ok, %Tesla.Env{status: status, body: body}} ->
        {:error, %{status: status, body: body}}
      {:error, reason} ->
        {:error, reason}
    end
  end
end
```

## Option 3: Elixir Temporal SDK (Advanced)

### 3.1 Use Official Elixir Temporal SDK

```elixir
# In mix.exs
{:temporalio, "~> 1.0"}

# Usage
defmodule YourApp.Workflows do
  use Temporalio.Workflow

  def run_llm_inference(request) do
    Temporalio.execute_workflow("LLMInferenceWorkflow", request)
  end
end
```

## Option 4: Phoenix LiveView Integration

### 4.1 LiveView Component

```elixir
# lib/your_app_web/live/automata_live.ex
defmodule YourAppWeb.AutomataLive do
  use YourAppWeb, :live_view

  alias YourApp.Automata

  @impl true
  def mount(_params, _session, socket) do
    {:ok, assign(socket, :prompt, "", :response: nil, :loading: false)}
  end

  @impl true
  def handle_event("submit_prompt", %{"prompt" => prompt}, socket) do
    if String.trim(prompt) != "" do
      send(self(), :run_inference)
      
      {:noreply, 
       socket
       |> assign(:prompt, prompt)
       |> assign(:loading: true)}
    else
      {:noreply, socket}
    end
  end

  @impl true
  def handle_info(:run_inference, socket) do
    case Automata.run_llm_inference_simple(socket.assigns.prompt) do
      {:ok, result} ->
        # Poll for result
        schedule_result_check(result["runId"])
        
        {:noreply, socket}
      
      {:error, reason} ->
        {:noreply, 
         socket
         |> assign(:loading, false)
         |> put_flash(:error, "Failed to start workflow: #{inspect(reason)}")}
    end
  end

  @impl true
  def handle_info({:workflow_result, result}, socket) do
    {:noreply,
     socket
     |> assign(:loading, false)
     |> assign(:response, result)}
  end

  defp schedule_result_check(workflow_id) do
    Process.send_after(self(), {:check_workflow, workflow_id}, 2000)
  end
end
```

## Usage Examples

### Basic API Call

```elixir
# Simple prompt
{:ok, result} = Automata.run_llm_inference_simple("Write a Python function to sort a list")

# With custom parameters
{:ok, result} = Automata.run_llm_inference_simple(
  "Explain quantum computing", 
  max_tokens: 8000, 
  temperature: 0.5
)

# Detailed request
messages = [
  %{"role" => "system", "content" => "You are a helpful assistant."},
  %{"role" => "user", "content" => "What is the meaning of life?"}
]

{:ok, result} = Automata.run_llm_inference("z-ai/glm-4.6", messages)
```

### HTTP API Usage

```bash
# Simple prompt
curl -X POST http://localhost:4000/api/automata/llm_inference \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a Hello World function in Python"}'

# Detailed request
curl -X POST http://localhost:4000/api/automata/llm_inference/detailed \
  -H "Content-Type: application/json" \
  -d '{
    "model": "z-ai/glm-4.6",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Explain machine learning"}
    ],
    "max_tokens": 5000,
    "temperature": 0.7
  }'

# Check workflow status
curl http://localhost:4000/api/automata/workflow/{workflow_id}/status
```

## Error Handling and Monitoring

### Error Handling

```elixir
defmodule YourApp.Automata do
  def run_llm_inference_with_retry(prompt, opts \\ []) do
    case run_llm_inference_simple(prompt, opts) do
      {:ok, result} ->
        {:ok, result}
      
      {:error, %{status: 500}} ->
        # Retry logic
        :timer.sleep(1000)
        run_llm_inference_with_retry(prompt, opts)
      
      {:error, reason} ->
        {:error, reason}
    end
  end
end
```

### Telemetry Integration

```elixir
# In your application start
:telemetry.execute(
  [:automata, :workflow, :started],
  %{workflow_type: "llm_inference"},
  %{prompt_length: String.length(prompt)}
)
```

## Deployment Considerations

1. **Environment Variables**: Configure Temporal host/namespace
2. **Connection Pooling**: Use Broadway for concurrent requests
3. **Circuit Breaking**: Implement circuit breaker pattern
4. **Rate Limiting**: Add rate limiting for API endpoints
5. **Monitoring**: Integrate with AppSignal/New Relic

## Recommendation

**Option 1 (Direct Temporal Client)** is recommended because:
- Full control over workflow execution
- Better error handling
- Easier testing and debugging
- More maintainable codebase
- Direct integration with Temporal features

This approach provides the best balance of functionality, maintainability, and performance for production use.