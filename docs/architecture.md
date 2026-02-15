# ArgusLM Architecture

ArgusLM is a comprehensive LLM monitoring and benchmarking platform designed to provide real-time visibility into the performance, availability, and reliability of various LLM providers. It supports both cloud-based APIs and local model deployments.

## System Overview

ArgusLM follows a decoupled architecture consisting of a React-based frontend, a FastAPI-based backend, and a shared Python SDK. The system leverages LiteLLM as a unified abstraction layer to communicate with over 100 LLM providers.

```
┌─────────────────────────────────────────────────────────────────┐
│                         ArgusLM                                 │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (React + Vite)           Backend (FastAPI)            │
│  ┌─────────────────────┐           ┌──────────────────────┐    │
│  │ Dashboard           │◄─────────►│ REST API + WebSocket │    │
│  │ Benchmarks          │           │ Background Scheduler │    │
│  │ Monitoring          │           │ Alert Engine         │    │
│  │ Providers           │           └──────────┬───────────┘    │
│  └─────────────────────┘                      │                 │
│                                               ▼                 │
│                              ┌─────────────────────────────┐   │
│                              │  LiteLLM Abstraction Layer  │   │
│                              └─────────────┬───────────────┘   │
│                                            │                    │
└────────────────────────────────────────────┼────────────────────┘
                                             ▼
              ┌──────────────────────────────────────────────────┐
              │                  LLM Providers                   │
              │  OpenAI │ Anthropic │ Bedrock │ Vertex │ Azure   │
              │  Ollama │ LM Studio │ xAI │ DeepSeek │ 100+     │
              └──────────────────────────────────────────────────┘
```

## Component Breakdown

### Frontend
- **Framework**: React with Vite for fast development and optimized builds.
- **Styling**: Tailwind CSS for responsive and maintainable UI components.
- **Visualization**: Recharts for rendering performance trends, latency charts, and benchmark comparisons.
- **State Management**: React hooks and context for managing application state and API interactions.

### Backend (Server)
- **API Framework**: FastAPI provides a high-performance, asynchronous REST API.
- **Task Scheduling**: An internal background scheduler manages periodic uptime checks and alert evaluations.
- **LLM Interaction**: LiteLLM handles the complexities of different provider APIs, providing a unified interface for streaming and non-streaming completions.
- **Security**: Fernet-based encryption for sensitive provider credentials and JWT for API authentication.

### Database
- **ORM**: SQLAlchemy with async support for database interactions.
- **Migrations**: Alembic for managing schema changes.
- **Engines**: Supports PostgreSQL for production deployments and SQLite for local development and testing.

### SDK Client
- **Unified Access**: Provides both synchronous (`ArgusLMClient`) and asynchronous (`AsyncArgusLMClient`) clients.
- **Shared Schemas**: Uses Pydantic v2 models for consistent data validation across the SDK and server.

## Package Structure

The project is organized into a core package that contains both the client SDK and the server implementation.

- `arguslm/`: Root package.
    - `client.py`: SDK client implementations.
    - `schemas/`: Shared Pydantic models for API requests and responses.
    - `server/`: FastAPI server implementation.
        - `api/`: REST API routers and endpoint definitions.
        - `core/`: Core business logic and services.
            - `uptime.py`: Health check and TTFT/TPS measurement logic.
            - `benchmark_engine.py`: Parallel benchmark orchestration and throttling.
            - `alert_evaluator.py`: Alert rule evaluation and deduplication.
            - `litellm_client.py`: Wrapper for LiteLLM with retries and error handling.
            - `providers/`: Provider catalog and model name mapping.
        - `db/`: Database initialization and session management.
        - `discovery/`: Provider-specific adapters for automatic model discovery.
        - `models/`: SQLAlchemy ORM model definitions.

## Key Data Flows

### Uptime Monitoring Flow
1. The background scheduler triggers a periodic check for enabled models.
2. `uptime.py` retrieves model credentials and constructs a health check prompt.
3. `LiteLLMClient` executes a streaming completion request.
4. `MetricsCollector` records the Time to First Token (TTFT) and calculates Tokens per Second (TPS).
5. The result is persisted as an `UptimeCheck` record in the database.

### Benchmark Execution Flow
1. A user or the SDK initiates a benchmark run with a set of models and a prompt pack.
2. `benchmark_engine.py` orchestrates parallel requests using `asyncio`.
3. Throttling is applied at three levels (global, per-provider, and per-model) using semaphores to prevent rate limiting.
4. Each model run performs multiple iterations (including warmups) to gather statistically significant data.
5. Results are aggregated and yielded via a stream or returned as a complete list.

### Alert Evaluation Flow
1. After uptime checks complete, `alert_evaluator.py` scans for matching alert rules.
2. Rules are evaluated against the latest check results (e.g., "any model down", "specific model down").
3. The system checks for active incidents to avoid duplicate alerts for the same ongoing issue.
4. New `Alert` records are created for unacknowledged incidents.

## Technology Stack

| Layer | Technology |
| :--- | :--- |
| Language | Python (Backend/SDK), TypeScript (Frontend) |
| Web Framework | FastAPI |
| Frontend | React, Vite, Tailwind CSS |
| Database | PostgreSQL, SQLAlchemy, Alembic |
| LLM Integration | LiteLLM |
| Validation | Pydantic v2 |
| Testing | Pytest |

## Deployment Architecture

ArgusLM supports two primary installation modes:

1. **SDK Only**: `pip install arguslm`
   - Lightweight installation for interacting with a remote ArgusLM server.
2. **Full Server**: `pip install arguslm[server]`
   - Includes all dependencies required to host the ArgusLM platform, including the API server and background workers.

For production environments, a Docker-based deployment using `docker-compose` is recommended to manage the FastAPI server, PostgreSQL database, and the React frontend.
