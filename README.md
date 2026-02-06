# ArgusLM

**The hundred-eyed watcher for your LLM providers.**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](docker-compose.yml)

ArgusLM monitors and benchmarks LLM performance across 100+ providers. Track uptime, TTFT, and TPS for OpenAI, Anthropic, AWS Bedrock, Google Vertex, Azure, Ollama, LM Studio, and more—all through a single dashboard.

> *In Greek mythology, Argus Panoptes was a giant with a hundred eyes. ArgusLM watches over your hundred providers.*

---

## Quick Start

```bash
git clone https://github.com/bluet/arguslm.git && cd arguslm
cp .env.example .env

# Generate secrets
docker run --rm python:3.11-slim sh -c "pip install -q cryptography && python -c '
from cryptography.fernet import Fernet; import secrets
print(f\"ENCRYPTION_KEY={Fernet.generate_key().decode()}\")
print(f\"SECRET_KEY={secrets.token_urlsafe(32)}\")
print(f\"DB_PASSWORD={secrets.token_urlsafe(24)}\")
'" >> .env

docker compose up -d
```

**Dashboard**: http://localhost:3000 | **API Docs**: http://localhost:8000/docs

---

## Features

| Category | Capabilities |
|----------|-------------|
| **Monitoring** | Automated uptime checks, real-time status, availability tracking, configurable intervals |
| **Benchmarking** | Parallel multi-model tests, TTFT & TPS metrics, customizable prompt packs |
| **Dashboard** | Live performance charts, latency trends, model comparison, failure markers |
| **Alerting** | Downtime detection, performance degradation, in-app notifications |
| **Providers** | 100+ via LiteLLM: OpenAI, Anthropic, Bedrock, Vertex, Azure, Ollama, LM Studio, xAI, DeepSeek, Fireworks |

---

## Architecture

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

---

## Key Metrics

ArgusLM tracks metrics that matter for real-world LLM performance:

- **TTFT** (Time to First Token) — User-perceived responsiveness
- **TPS** (Tokens per Second) — Streaming throughput, excluding TTFT
- **Latency** — End-to-end request time
- **Availability** — Uptime percentage over time

---

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `SECRET_KEY` | Session encryption key | *required* |
| `ENCRYPTION_KEY` | Credential encryption (Fernet) | *required* |

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for provider setup and advanced options.

---

## Local Development

**Backend:**
```bash
pip install -e .
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend && npm install && npm run dev
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.11+, SQLAlchemy, Alembic |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts |
| Database | PostgreSQL (prod) / SQLite (dev) |
| Provider Abstraction | LiteLLM |

---

## Documentation

- [Configuration Guide](docs/CONFIGURATION.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [API Reference](http://localhost:8000/docs) *(when running)*

---

## Contributing

Contributions welcome! Please submit a Pull Request.

## License

[Apache License 2.0](LICENSE)

---

*Named after Argus Panoptes, the all-seeing giant of Greek mythology.*
