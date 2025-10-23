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

  def list_workflows(opts \\ []) do
    GenServer.call(__MODULE__, {:list_workflows, opts})
  end

  def list_recent_workflows(opts \\ []) do
    GenServer.call(__MODULE__, {:list_recent_workflows, opts})
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

  @impl true
  def handle_call({:list_workflows, opts}, _from, state) do
    max_results = Keyword.get(opts, :max_results, 100)
    workflow_type = Keyword.get(opts, :workflow_type)
    status = Keyword.get(opts, :status)
    
    case list_workflow_executions(state.host, state.namespace, workflow_type, status, max_results) do
      {:ok, workflows} ->
        {:reply, {:ok, workflows}, state}
      {:error, reason} ->
        {:reply, {:error, reason}, state}
    end
  end

  @impl true
  def handle_call({:list_recent_workflows, opts}, _from, state) do
    hours = Keyword.get(opts, :hours, 24)
    workflow_type = Keyword.get(opts, :workflow_type)
    max_results = Keyword.get(opts, :max_results, 100)
    
    case list_recent_workflow_executions(state.host, state.namespace, workflow_type, hours, max_results) do
      {:ok, workflows} ->
        {:reply, {:ok, workflows}, state}
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

  defp list_workflow_executions(host, namespace, workflow_type, status, max_results) do
    query_params = build_workflow_query_params(workflow_type, status, max_results)
    url = "http://#{host}/api/namespaces/#{namespace}/workflows/list?#{URI.encode_query(query_params)}"
    
    case Tesla.get(url) do
      {:ok, %Tesla.Env{status: 200, body: response_body}} ->
        {:ok, Jason.decode!(response_body)}
      {:ok, %Tesla.Env{status: status, body: body}} ->
        {:error, %{status: status, body: body}}
      {:error, reason} ->
        {:error, reason}
    end
  end

  defp list_recent_workflow_executions(host, namespace, workflow_type, hours, max_results) do
    start_time = DateTime.utc_now() |> DateTime.add(-hours * 3600, :second) |> DateTime.to_iso8601()
    query_params = build_workflow_query_params(workflow_type, nil, max_results)
    query_params = Map.put(query_params, :start_time, start_time)
    
    url = "http://#{host}/api/namespaces/#{namespace}/workflows/list?#{URI.encode_query(query_params)}"
    
    case Tesla.get(url) do
      {:ok, %Tesla.Env{status: 200, body: response_body}} ->
        {:ok, Jason.decode!(response_body)}
      {:ok, %Tesla.Env{status: status, body: body}} ->
        {:error, %{status: status, body: body}}
      {:error, reason} ->
        {:error, reason}
    end
  end

  defp build_workflow_query_params(workflow_type, status, max_results) do
    params = %{max_results: max_results}
    
    params =
      if workflow_type do
        Map.put(params, :workflow_type, workflow_type)
      else
        params
      end
    
    if status do
      Map.put(params, :status, status)
    else
      params
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

  @doc """
  List all workflows with optional filtering.
  """
  def list_workflows(opts \\ []) do
    TemporalClient.list_workflows(opts)
  end

  @doc """
  List recent workflows (last N hours).
  """
  def list_recent_workflows(opts \\ []) do
    hours = Keyword.get(opts, :hours, 24)
    workflow_type = Keyword.get(opts, :workflow_type)
    max_results = Keyword.get(opts, :max_results, 100)
    
    TemporalClient.list_recent_workflows(
      hours: hours,
      workflow_type: workflow_type,
      max_results: max_results
    )
  end

  @doc """
  List running workflows.
  """
  def list_running_workflows(opts \\ []) do
    workflow_type = Keyword.get(opts, :workflow_type)
    max_results = Keyword.get(opts, :max_results, 100)
    
    TemporalClient.list_workflows(
      workflow_type: workflow_type,
      status: "RUNNING",
      max_results: max_results
    )
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

  @doc """
  GET /api/automata/workflows/list
  List recent workflow executions (for page reload)
  """
  def list_workflows(conn, params) do
    opts = [
      workflow_type: Map.get(params, "workflow_type"),
      status: Map.get(params, "status"),
      max_results: Map.get(params, "max_results", 100) |> String.to_integer()
    ]
    |> Enum.filter(fn {_k, v} -> v != nil end)
    
    case Automata.list_workflows(opts) do
      {:ok, workflows} ->
        conn
        |> json(%{
          workflows: workflows,
          count: length(workflows)
        })
      
      {:error, reason} ->
        handle_error(conn, reason)
    end
  end

  @doc """
  GET /api/automata/workflows/recent
  List recent workflows (last N hours)
  """
  def list_recent_workflows(conn, params) do
    opts = [
      hours: Map.get(params, "hours", "24") |> String.to_integer(),
      workflow_type: Map.get(params, "workflow_type"),
      max_results: Map.get(params, "max_results", "100") |> String.to_integer()
    ]
    |> Enum.filter(fn {_k, v} -> v != nil end)
    
    case Automata.list_recent_workflows(opts) do
      {:ok, workflows} ->
        conn
        |> json(%{
          workflows: workflows,
          count: length(workflows)
        })
      
      {:error, reason} ->
        handle_error(conn, reason)
    end
  end

  @doc """
  GET /api/automata/workflows/running
  List currently running workflows
  """
  def list_running_workflows(conn, params) do
    opts = [
      workflow_type: Map.get(params, "workflow_type"),
      max_results: Map.get(params, "max_results", "100") |> String.to_integer()
    ]
    |> Enum.filter(fn {_k, v} -> v != nil end)
    
    case Automata.list_running_workflows(opts) do
      {:ok, workflows} ->
        conn
        |> json(%{
          workflows: workflows,
          count: length(workflows)
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

    # Start workflows
    post "/automata/llm_inference", Api.AutomataController, :llm_inference
    post "/automata/llm_inference/detailed", Api.AutomataController, :llm_inference_detailed
    
    # Query workflows
    get "/automata/workflow/:id/status", Api.AutomataController, :workflow_status
    get "/automata/workflows/list", Api.AutomataController, :list_workflows
    get "/automata/workflows/recent", Api.AutomataController, :list_recent_workflows
    get "/automata/workflows/running", Api.AutomataController, :list_running_workflows
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

## Loading Workflows on Page Reload

When a user reloads the page, you need to restore the list of existing workflow executions from Temporal's database. Here's how to implement this:

### Phoenix LiveView Example

```elixir
defmodule YourAppWeb.WorkflowsLive do
  use YourAppWeb, :live_view
  alias YourApp.Automata

  @impl true
  def mount(_params, _session, socket) do
    # Load recent workflows on page load
    workflows = load_recent_workflows()
    
    {:ok, 
     socket
     |> assign(:workflows, workflows)
     |> assign(:loading, false)}
  end

  @impl true
  def handle_event("start_workflow", %{"prompt" => prompt}, socket) do
    case Automata.run_llm_inference_simple(prompt) do
      {:ok, result} ->
        workflow_id = result["runId"]
        
        # Add to local state immediately
        new_workflow = %{
          workflow_id: workflow_id,
          status: "RUNNING",
          prompt: prompt,
          start_time: DateTime.utc_now()
        }
        
        workflows = [new_workflow | socket.assigns.workflows]
        
        # Start polling for result
        schedule_status_check(workflow_id)
        
        {:noreply, assign(socket, :workflows, workflows)}
      
      {:error, reason} ->
        {:noreply, put_flash(socket, :error, "Failed: #{inspect(reason)}")}
    end
  end

  @impl true
  def handle_event("refresh_workflows", _params, socket) do
    workflows = load_recent_workflows()
    {:noreply, assign(socket, :workflows, workflows)}
  end

  @impl true
  def handle_info({:check_status, workflow_id}, socket) do
    case Automata.workflow_status(workflow_id) do
      {:ok, status} ->
        workflows = update_workflow_status(socket.assigns.workflows, workflow_id, status)
        
        # Continue polling if still running
        if status["status"]["value"] == "RUNNING" do
          schedule_status_check(workflow_id)
        end
        
        {:noreply, assign(socket, :workflows, workflows)}
      
      {:error, _reason} ->
        {:noreply, socket}
    end
  end

  defp load_recent_workflows do
    case Automata.list_recent_workflows(hours: 24, workflow_type: "LLMInferenceWorkflow") do
      {:ok, workflows} ->
        Enum.map(workflows, fn w ->
          %{
            workflow_id: w["workflow_id"],
            workflow_type: w["workflow_type"],
            status: w["status"],
            start_time: w["start_time"],
            close_time: w["close_time"]
          }
        end)
      
      {:error, _reason} ->
        []
    end
  end

  defp update_workflow_status(workflows, workflow_id, status) do
    Enum.map(workflows, fn w ->
      if w.workflow_id == workflow_id do
        %{w | status: status["status"]["value"]}
      else
        w
      end
    end)
  end

  defp schedule_status_check(workflow_id) do
    Process.send_after(self(), {:check_status, workflow_id}, 2000)
  end
end
```

### React/JavaScript Example

```javascript
// WorkflowList.jsx
import { useEffect, useState } from 'react';

function WorkflowList() {
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);

  // Load workflows on page mount
  useEffect(() => {
    loadRecentWorkflows();
  }, []);

  async function loadRecentWorkflows() {
    try {
      const response = await fetch('/api/automata/workflows/recent?hours=24&workflow_type=LLMInferenceWorkflow');
      const data = await response.json();
      setWorkflows(data.workflows);
      setLoading(false);
      
      // Start polling for running workflows
      data.workflows
        .filter(w => w.status === 'RUNNING')
        .forEach(w => pollWorkflowStatus(w.workflow_id));
    } catch (error) {
      console.error('Failed to load workflows:', error);
      setLoading(false);
    }
  }

  async function pollWorkflowStatus(workflowId) {
    try {
      const response = await fetch(`/api/automata/workflow/${workflowId}/status`);
      const data = await response.json();
      
      // Update workflow in list
      setWorkflows(prev => 
        prev.map(w => 
          w.workflow_id === workflowId 
            ? { ...w, status: data.status }
            : w
        )
      );
      
      // Continue polling if still running
      if (data.execution_info.status === 'RUNNING') {
        setTimeout(() => pollWorkflowStatus(workflowId), 2000);
      }
    } catch (error) {
      console.error('Failed to poll workflow:', error);
    }
  }

  async function startNewWorkflow(prompt) {
    const response = await fetch('/api/automata/llm_inference', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt })
    });
    
    const data = await response.json();
    
    // Add to local state
    const newWorkflow = {
      workflow_id: data.workflow_id,
      status: 'RUNNING',
      start_time: new Date().toISOString()
    };
    
    setWorkflows(prev => [newWorkflow, ...prev]);
    
    // Start polling
    pollWorkflowStatus(data.workflow_id);
  }

  if (loading) {
    return <div>Loading workflows...</div>;
  }

  return (
    <div>
      <button onClick={() => startNewWorkflow("Hello, AI!")}>
        Start New Workflow
      </button>
      
      <button onClick={loadRecentWorkflows}>
        Refresh
      </button>
      
      <ul>
        {workflows.map(w => (
          <li key={w.workflow_id}>
            {w.workflow_id} - {w.status}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Python API Server Example

If you need a REST API server to expose workflow listing:

```python
# scripts/api_server.py
from fastapi import FastAPI, Query
from typing import Optional
import uvicorn

from shared.services.workflow_query import create_workflow_query_service

app = FastAPI(title="Automata Workflows API")

@app.get("/api/workflows/list")
async def list_workflows(
    workflow_type: Optional[str] = None,
    status: Optional[str] = None,
    max_results: int = Query(100, le=1000)
):
    """List workflow executions."""
    service = await create_workflow_query_service()
    workflows = await service.list_workflows(
        workflow_type=workflow_type,
        max_results=max_results
    )
    return {"workflows": workflows, "count": len(workflows)}

@app.get("/api/workflows/recent")
async def list_recent_workflows(
    hours: int = Query(24, le=168),
    workflow_type: Optional[str] = None,
    max_results: int = Query(100, le=1000)
):
    """List recent workflows (last N hours)."""
    service = await create_workflow_query_service()
    workflows = await service.list_recent_workflows(
        workflow_type=workflow_type,
        hours=hours,
        max_results=max_results
    )
    return {"workflows": workflows, "count": len(workflows)}

@app.get("/api/workflows/running")
async def list_running_workflows(
    workflow_type: Optional[str] = None,
    max_results: int = Query(100, le=1000)
):
    """List currently running workflows."""
    service = await create_workflow_query_service()
    workflows = await service.list_running_workflows(
        workflow_type=workflow_type,
        max_results=max_results
    )
    return {"workflows": workflows, "count": len(workflows)}

@app.get("/api/workflows/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get detailed workflow status."""
    service = await create_workflow_query_service()
    status = await service.get_workflow_status(workflow_id)
    return status

@app.get("/api/workflows/{workflow_id}/result")
async def get_workflow_result(workflow_id: str):
    """Get workflow result (if completed)."""
    service = await create_workflow_query_service()
    try:
        result = await service.get_workflow_result(workflow_id)
        return {"status": "completed", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Key Points for Page Reload

1. **On Page Load**: Call `list_recent_workflows()` to load existing executions from Temporal database
2. **Filter by Type**: Use `workflow_type` parameter to only load relevant workflows
3. **Time Range**: Use `hours` parameter to limit how far back to search (e.g., last 24 hours)
4. **Poll Running Workflows**: After loading, check status of any `RUNNING` workflows and poll for updates
5. **Update UI**: When status changes from RUNNING to COMPLETED/FAILED, update the UI accordingly
6. **Persist Locally**: Consider caching in browser localStorage to reduce API calls

This ensures users see their workflow history even after page reload, providing a seamless experience.

## Recommendation

**Option 1 (Direct Temporal Client)** is recommended because:
- Full control over workflow execution
- Better error handling
- Easier testing and debugging
- More maintainable codebase
- Direct integration with Temporal features

This approach provides the best balance of functionality, maintainability, and performance for production use.
