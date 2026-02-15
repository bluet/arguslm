# ArgusLM Python SDK Guide

The ArgusLM Python SDK provides a convenient way to interact with the ArgusLM API for monitoring and benchmarking LLM providers. It supports both synchronous and asynchronous operations.

## Installation

Install the SDK using pip:

```bash
pip install arguslm
```

## Quick Start

### Synchronous Client

The `ArgusLMClient` is used for synchronous operations. It can be used as a context manager to ensure the underlying HTTP client is properly closed.

```python
from arguslm import ArgusLMClient

with ArgusLMClient(base_url="http://localhost:8000") as client:
    # Get uptime history
    uptime = client.get_uptime_history(limit=5)
    for check in uptime.items:
        print(f"{check.model_name}: {check.status} ({check.ttft_ms}ms TTFT)")
```

### Asynchronous Client

For asynchronous applications, use `AsyncArgusLMClient`.

```python
import asyncio
from arguslm import AsyncArgusLMClient

async def main():
    async with AsyncArgusLMClient() as client:
        providers = await client.list_providers()
        for provider in providers.providers:
            print(f"Provider: {provider.name} ({provider.provider_type})")

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

The client can be configured via constructor arguments or environment variables.

| Parameter | Environment Variable | Default | Description |
| :--- | :--- | :--- | :--- |
| `base_url` | `ARGUSLM_BASE_URL` | `http://localhost:8000` | The URL of the ArgusLM server |
| `timeout` | - | 30.0s | Request timeout (float or `httpx.Timeout`) |
| `max_retries` | - | 2 | Number of retries for failed requests |

```python
client = ArgusLMClient(
    base_url="https://argus.example.com",
    timeout=60.0,
    max_retries=3
)
```

## Context Manager Usage

Using the client as a context manager is the recommended way to ensure that the underlying HTTP connections are closed properly.

### Synchronous Context Manager
```python
from arguslm import ArgusLMClient

with ArgusLMClient() as client:
    providers = client.list_providers()
    # ... do work ...
# client is automatically closed here
```

### Asynchronous Context Manager
```python
from arguslm import AsyncArgusLMClient

async def run():
    async with AsyncArgusLMClient() as client:
        models = await client.list_models()
        # ... do work ...
    # client is automatically closed here
```

## Providers

Manage LLM provider accounts and configurations.

### List Providers
```python
response = client.list_providers()
for provider in response.providers:
    print(f"{provider.display_name} ({provider.provider_type}) - Enabled: {provider.enabled}")
```

### Create Provider
```python
from arguslm.schemas import ProviderCreate

new_provider = client.create_provider(ProviderCreate(
    display_name="OpenAI Production",
    provider_type="openai",
    credentials={"api_key": "sk-..."},
))
```

### Test Connection
You can test a provider's credentials before creating it, or test an existing provider.
```python
# Test new configuration
test_result = client.test_provider_connection(ProviderCreate(...))
if test_result.success:
    print("Connection successful!")

# Test existing provider
test_result = client.test_existing_provider(provider_id)
```

### Refresh Models
Automatically discover and update models available for a provider.
```python
refresh_info = client.refresh_provider_models(provider_id)
print(f"Discovered {refresh_info.models_discovered} models")
```

## Models

Manage specific LLM models and their monitoring/benchmarking status.

### List Models
Filter models by provider or capability.
```python
models = client.list_models(
    provider_id="some-uuid",
    enabled_for_monitoring=True,
    limit=20
)
```

### Get Model
```python
model = client.get_model("model-uuid")
print(f"{model.model_id} — monitoring: {model.enabled_for_monitoring}")
```

### Update Model
Enable or disable models for specific tasks.
```python
from arguslm.schemas import ModelUpdate

client.update_model(model_id, ModelUpdate(
    custom_name="Primary GPT-4",
    enabled_for_monitoring=True,
    enabled_for_benchmark=True
))
```

## Monitoring

Configure and run automated health checks.

### Get/Update Configuration
```python
config = client.get_monitoring_config()
print(f"Monitoring every {config.interval_minutes} minutes")

from arguslm.schemas import MonitoringConfigUpdate
client.update_monitoring_config(MonitoringConfigUpdate(
    interval_minutes=15,
    enabled=True
))
```

### Run Monitoring Manually
Trigger an immediate health check across all enabled models.
```python
run_info = client.run_monitoring()
print(f"Monitoring run {run_info.run_id} is {run_info.status}")
```

### Uptime History
Retrieve historical uptime check results.
```python
history = client.get_uptime_history(
    model_id="some-uuid",
    status="down",
    limit=50
)
```

### Export Uptime History
Download uptime data as JSON or CSV for external analysis.
```python
resp = client.export_uptime_history(format="csv", model_id="some-uuid")
with open("uptime.csv", "wb") as f:
    f.write(resp.content)
```

## Benchmarks

Run performance benchmarks across multiple models.

### Start Benchmark
```python
from arguslm.schemas import BenchmarkCreate

benchmark = client.start_benchmark(BenchmarkCreate(
    model_ids=["uuid-1", "uuid-2"],
    prompt_pack="shakespeare",
    num_runs=5,
    max_tokens=200,
    name="Performance Comparison"
))
```

### List Benchmarks
```python
benchmarks = client.list_benchmarks(page=1, per_page=10)
for run in benchmarks.runs:
    print(f"Run: {run.name} - Status: {run.status}")
```

### Get Results
```python
results = client.get_benchmark_results(benchmark.id)
for res in results.results:
    print(f"Model: {res.model_name}")
    print(f"  TTFT: {res.ttft_ms}ms")
    print(f"  TPS: {res.tps}")
```

### Export Benchmark
Download benchmark results as JSON or CSV.
```python
resp = client.export_benchmark(benchmark.id, format="csv")
with open("benchmark.csv", "wb") as f:
    f.write(resp.content)
```

### Stream Benchmark (WebSocket)
Watch benchmark progress in real-time via the async client. Requires `pip install websockets`.
```python
async with AsyncArgusLMClient() as client:
    benchmark = await client.start_benchmark(BenchmarkCreate(...))
    async for msg in client.stream_benchmark(benchmark.id):
        if msg["type"] == "progress":
            print(f"Progress: {msg['completed']}/{msg['total']}")
        elif msg["type"] == "result":
            print(f"Result: {msg['data']['model_name']} — {msg['data']['ttft_ms']}ms")
        elif msg["type"] == "complete":
            print("Benchmark finished!")
```

## Alerts

Manage alert rules and view triggered alerts.

### List Alert Rules
```python
rules = client.list_alert_rules()
```

### Create Alert Rule
```python
from arguslm.schemas import AlertRuleCreate

rule = client.create_alert_rule(AlertRuleCreate(
    name="Critical Latency Alert",
    rule_type="performance_degradation",
    target_model_id=some_model_id,
    enabled=True
))
```

### View and Acknowledge Alerts
```python
alerts = client.list_alerts(acknowledged=False)
for alert in alerts.items:
    print(f"Alert: {alert.message}")
    client.acknowledge_alert(alert.id)
```

### Unread Count
Get the number of unacknowledged alerts (useful for notification badges).
```python
unread = client.get_unread_alert_count()
print(f"{unread.count} unread alerts")
```

### Recent Alerts
Get the most recent alerts for a notification dropdown.
```python
recent = client.get_recent_alerts(limit=5)
for alert in recent.items:
    print(f"{'🔴' if not alert.acknowledged else '⚪'} {alert.message}")
print(f"Total unread: {recent.total_unread}")
```

## Export

The SDK supports two export approaches:

### File Export (JSON/CSV)
Use the dedicated export methods to download data files:
```python
# Export benchmark results as CSV
resp = client.export_benchmark(run_id, format="csv")
with open("benchmark.csv", "wb") as f:
    f.write(resp.content)

# Export uptime history as JSON
resp = client.export_uptime_history(format="json", start_date="2025-01-01")
with open("uptime.json", "wb") as f:
    f.write(resp.content)
```

### Pydantic Model Serialization
All other SDK methods return Pydantic models with built-in serialization:
```python
results = client.get_benchmark_results(run_id)
json_data = results.model_dump_json(indent=2)
dict_data = results.model_dump()
```

## Error Handling

The SDK raises specific exceptions based on the API response. All exceptions inherit from `ArgusLMError`.

```python
from arguslm.exceptions import ArgusLMError, NotFoundError, RateLimitError

try:
    client.get_provider("invalid-id")
except NotFoundError:
    print("Provider not found")
except RateLimitError:
    print("Rate limit exceeded")
except ArgusLMError as e:
    print(f"An error occurred: {e}")
```

### Exception Hierarchy

- `ArgusLMError`
    - `APIError`
        - `APIStatusError`
            - `BadRequestError` (400)
            - `AuthenticationError` (401)
            - `PermissionDeniedError` (403)
            - `NotFoundError` (404)
            - `ConflictError` (409)
            - `UnprocessableEntityError` (422)
            - `RateLimitError` (429)
            - `InternalServerError` (5xx)
        - `APIConnectionError`
            - `APITimeoutError`
