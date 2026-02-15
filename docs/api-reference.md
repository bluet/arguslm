# ArgusLM API Reference

This document provides a comprehensive reference for the ArgusLM REST API. The API allows you to programmatically manage providers, models, monitoring configurations, benchmarks, and alerts.

## Base URL

All API endpoints are prefixed with:
`/api/v1`

Interactive Swagger documentation is available at `/docs` when the server is running.

---

## Providers

Manage LLM provider accounts and credentials.

### List Providers
`GET /providers`

Returns a list of all configured provider accounts.

**Response Format:**
- `providers` (array): List of provider objects.
- `total` (int): Total number of providers.

**Example Request:**
```bash
curl http://localhost:8000/api/v1/providers
```

### Create Provider
`POST /providers`

Create a new provider account. Credentials are encrypted before storage.

**Request Body:**
- `provider_type` (string, required): Provider type (e.g., `openai`, `anthropic`, `ollama`).
- `display_name` (string, required): Human-readable name for this account.
- `credentials` (object): Provider-specific credentials (e.g., `{"api_key": "sk-..."}`).

**Response Format:**
- `id` (UUID): Created provider ID.
- `provider_type` (string): Provider type.
- `display_name` (string): Display name.
- `enabled` (boolean): Enabled status.
- `created_at` (datetime): Creation timestamp.

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/v1/providers \
  -H "Content-Type: application/json" \
  -d '{
    "provider_type": "openai",
    "display_name": "OpenAI Production",
    "credentials": {"api_key": "sk-..."}
  }'
```

### Get Provider Catalog
`GET /providers/catalog`

Get the list of supported providers and their configuration requirements.

**Response Format:**
- `providers` (object): Map of provider IDs to their specifications.
- `total` (int): Total number of supported providers.
- `tested_count` (int): Number of providers with verified support.

### Get Provider
`GET /providers/{provider_id}`

Get details for a specific provider account.

**Response Format:**
- `id` (UUID): Provider ID.
- `provider_type` (string): Provider type.
- `display_name` (string): Display name.
- `enabled` (boolean): Enabled status.
- `base_url` (string, optional): Provider base URL.
- `region` (string, optional): Provider region.

### Update Provider
`PATCH /providers/{provider_id}`

Update provider display name, credentials, or enabled status.

**Request Body:**
- `display_name` (string, optional): New display name.
- `credentials` (object, optional): Updated credentials.
- `enabled` (boolean, optional): Enable/disable the account.

### Delete Provider
`DELETE /providers/{provider_id}`

Delete a provider account. Fails if the provider has models with benchmark history.

### Test Connection
`POST /providers/test-connection` (New provider)
`POST /providers/{provider_id}/test` (Existing provider)

Test the connection to a provider.

**Response Format:**
- `success` (boolean): Whether the test succeeded.
- `message` (string): Result message.
- `details` (object): Additional test details (e.g., latency, model tested).

### Refresh Models
`POST /providers/{provider_id}/refresh-models`

Trigger model discovery for the specified provider.

**Response Format:**
- `success` (boolean): Whether the refresh succeeded.
- `models_discovered` (int): Number of models found.
- `message` (string): Result message.

---

## Models

Manage LLM models associated with provider accounts.

### List Models
`GET /models`

List all models with optional filtering and pagination.

**Query Parameters:**
- `provider_id` (UUID): Filter by provider account.
- `enabled_for_monitoring` (boolean): Filter by monitoring status.
- `enabled_for_benchmark` (boolean): Filter by benchmark status.
- `search` (string): Search in model ID and custom name.
- `limit` (int, default 50): Results per page.
- `offset` (int, default 0): Results to skip.

**Response Format:**
- `items` (array): List of model objects.
- `total` (int): Total matching models.
- `has_more` (boolean): Whether more pages exist.

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/models?enabled_for_monitoring=true"
```

### Get Model
`GET /models/{model_id}`

Get details for a specific model.

**Response Format:**
- `id` (UUID): Model ID.
- `provider_account_id` (UUID): Associated provider ID.
- `model_id` (string): Provider's model identifier.
- `custom_name` (string, optional): Custom display name.
- `enabled_for_monitoring` (boolean): Monitoring status.
- `enabled_for_benchmark` (boolean): Benchmark status.

### Update Model
`PATCH /models/{model_id}`

Update a model's custom name or toggle monitoring/benchmark status.

**Request Body:**
- `custom_name` (string, optional): New display name.
- `enabled_for_monitoring` (boolean, optional): Enable/disable monitoring.
- `enabled_for_benchmark` (boolean, optional): Enable/disable benchmarking.

### Create Manual Model
`POST /models`

Manually add a model that wasn't automatically discovered.

**Request Body:**
- `provider_account_id` (UUID, required): Provider ID.
- `model_id` (string, required): Model identifier.
- `custom_name` (string, optional): Display name.
- `metadata` (object, optional): Additional model metadata.

---

## Monitoring

Configure and view automated uptime and performance checks.

### Get Monitoring Configuration
`GET /monitoring/config`

Get the global monitoring settings.

**Response Format:**
- `interval_minutes` (int): Check interval.
- `prompt_pack` (string): Active prompt pack.
- `enabled` (boolean): Global monitoring status.
- `last_run_at` (datetime, optional): Last run timestamp.

### Update Monitoring Configuration
`PATCH /monitoring/config`

Update global monitoring settings.

**Request Body:**
- `interval_minutes` (int, optional): How often to run checks (min 1).
- `prompt_pack` (string, optional): The prompt pack to use.
- `enabled` (boolean, optional): Globally enable/disable monitoring.

### Trigger Monitoring Run
`POST /monitoring/run`

Manually trigger an uptime check for all enabled models. Runs in the background.

**Response Format:**
- `run_id` (string): Unique run identifier.
- `status` (string): `queued`.
- `message` (string): Status message.

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/v1/monitoring/run
```

### Get Uptime History
`GET /monitoring/uptime`

Get historical uptime check results.

**Query Parameters:**
- `model_id` (UUID): Filter by model.
- `status` (string): Filter by status (`up`, `down`, `degraded`).
- `since` (datetime): Filter by timestamp.
- `limit` (int, default 100): Results per page.

**Response Format:**
- `items` (array): List of uptime check objects.
- `total` (int): Total number of checks.

### Export Uptime History
`GET /monitoring/uptime/export`

Export history as JSON or CSV.

**Query Parameters:**
- `format` (string, required): `json` or `csv`.
- `start_date` (datetime): Filter by start date.
- `end_date` (datetime): Filter by end date.

### List Prompt Packs
`GET /monitoring/prompt-packs`

List available prompt suites for monitoring and benchmarking.

**Response Format:**
- Array of prompt pack objects containing `id`, `name`, `prompt`, and `expected_tokens`.

---

## Benchmarks

Run detailed performance comparisons between models.

### Start Benchmark
`POST /benchmarks`

Start a new benchmark run for one or more models.

**Request Body:**
- `model_ids` (list[UUID], required): Models to benchmark.
- `prompt_pack` (string, required): Prompt suite to use.
- `name` (string, optional): Descriptive name for the run.
- `max_tokens` (int, default 200): Max tokens per request.
- `num_runs` (int, default 3): Number of iterations per model.

**Response Format:**
- `id` (UUID): Benchmark run ID.
- `status` (string): `pending`.
- `message` (string): Status message.

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/v1/benchmarks \
  -H "Content-Type: application/json" \
  -d '{
    "model_ids": ["uuid-1", "uuid-2"],
    "prompt_pack": "health_check",
    "num_runs": 5
  }'
```

### List Benchmarks
`GET /benchmarks`

List historical benchmark runs.

**Response Format:**
- `runs` (array): List of benchmark run summaries.
- `total` (int): Total number of runs.

### Get Benchmark Details
`GET /benchmarks/{run_id}`

Get a summary of a benchmark run, including aggregate statistics (P50, P95, P99).

**Response Format:**
- `id` (UUID): Run ID.
- `status` (string): `pending`, `running`, `completed`, or `failed`.
- `results` (array): List of individual result objects.
- `statistics` (object): Aggregate performance metrics.

### Get Benchmark Results
`GET /benchmarks/{run_id}/results`

Get the individual request results for a benchmark run.

### Export Benchmark Results
`GET /benchmarks/{run_id}/export`

Export results as JSON or CSV.

### Live Stream (WebSocket)
`WS /benchmarks/{run_id}/stream`

Connect via WebSocket to receive real-time progress updates and results as they are generated.

**Message Types:**
- `progress`: Current completion status.
- `result`: Individual model result as it completes.
- `complete`: Final completion signal.
- `error`: Failure notification.

---

## Alerts

Manage alert rules and view triggered alerts.

### List Alert Rules
`GET /alerts/rules`

**Response Format:**
- Array of alert rule objects.

### Create Alert Rule
`POST /alerts/rules`

Create a new rule for triggering alerts.

**Request Body:**
- `name` (string, required): Rule name.
- `rule_type` (string, required): `any_model_down`, `specific_model_down`, `model_unavailable_everywhere`, or `performance_degradation`.
- `target_model_id` (UUID, optional): Required for `specific_model_down`.
- `target_model_name` (string, optional): Required for `model_unavailable_everywhere`.
- `enabled` (boolean, default true): Active status.
- `notify_in_app` (boolean, default true): Dashboard notifications.

### Update Alert Rule
`PATCH /alerts/rules/{rule_id}`

### Delete Alert Rule
`DELETE /alerts/rules/{rule_id}`

### List Alerts
`GET /alerts`

List triggered alerts with optional filtering by rule or acknowledgment status.

**Response Format:**
- `items` (array): List of alert objects.
- `unacknowledged_count` (int): Count of unread alerts.

### Acknowledge Alert
`PATCH /alerts/{alert_id}/acknowledge`

Mark an alert as acknowledged.

### Unread Alert Count
`GET /alerts/unread-count`

Returns the number of unacknowledged alerts for notification badge display.

**Response:** `{ "count": 3 }`

### Recent Alerts
`GET /alerts/recent`

Returns the most recent alerts for notification dropdown.

**Query Parameters:**
- `limit` (int, default 10, max 50): Maximum alerts to return.

**Response Format:**
- `items` (array): Recent alert objects.
- `total_unread` (int): Total unacknowledged count.

---

## System

### Root Status
`GET /`

Returns `{"status": "ok"}`.

### Health Check
`GET /health`

Returns `{"status": "healthy"}`.
