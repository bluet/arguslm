# ArgusLM

**The hundred-eyed watcher for your LLM providers.**

[![License](https://img.shields.io/github/license/bluet/arguslm?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue?style=flat-square)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue?style=flat-square)](docker-compose.yml)

![ArgusLM Dashboard Overview](docs/images/dashboard-overview.png)

ArgusLM provides comprehensive monitoring and benchmarking for the modern LLM ecosystem. Gain deep visibility into uptime, Time to First Token (TTFT), and Tokens per Second (TPS) across 100+ providers—including OpenAI, Anthropic, AWS Bedrock, Google Vertex, and local instances like Ollama and LM Studio—all through a single, unified dashboard.

> *In Greek mythology, Argus Panoptes was a giant with a hundred eyes. ArgusLM watches over your hundred providers.*

---

## Quick Start

Deploy ArgusLM in under a minute:

```bash
git clone https://github.com/bluet/arguslm.git && cd arguslm
cp .env.example .env

# Generate secrets (requires cryptography package, or use the Docker one-liner in .env.example)
python3 scripts/generate-secrets.py >> .env

docker compose up -d
```

**Dashboard**: [http://localhost:3000](http://localhost:3000)
**API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Features

| Category | Capabilities |
| :--- | :--- |
| Monitoring | Automated uptime checks, real-time status tracking, and configurable availability intervals. |
| Benchmarking | Parallel multi-model testing with deep metrics for TTFT, TPS, and total latency. |
| Visualization | Live performance charts, historical trends, and side-by-side model comparisons. |
| Alerting | Proactive downtime detection and performance degradation notifications. |
| Integration | Native support for 100+ providers via LiteLLM abstraction. |

---

## Performance Insights

![Performance Trends](docs/images/dashboard-performance.png)
*Real-time tracking of latency and throughput trends across all configured providers.*

![Model Comparison](docs/images/dashboard-comparison.png)
*Side-by-side performance comparison to identify the most efficient models for your workload.*

---

## Monitoring and Benchmarking

![Monitoring Configuration](docs/images/monitoring.png)
*Configure granular monitoring intervals and thresholds for each provider.*

![Benchmark Runner](docs/images/benchmarks.png)
*Execute standardized benchmark suites to validate provider performance under load.*

---

## Architecture

ArgusLM is built for scale and reliability, leveraging a modern asynchronous stack.

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

ArgusLM tracks the metrics that define real-world LLM performance:

- **Time to First Token (TTFT)**: Measure user-perceived responsiveness and cold-start latency.
- **Tokens per Second (TPS)**: Evaluate sustained streaming throughput independent of initial latency.
- **End-to-End Latency**: Track total request duration for non-streaming workloads.
- **Availability**: Monitor uptime and reliability trends with granular failure analysis.

---

## Configuration

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `SECRET_KEY` | Session encryption key | *required* |
| `ENCRYPTION_KEY` | Credential encryption (Fernet) | *required* |

Detailed setup instructions are available in the [Configuration Guide](docs/CONFIGURATION.md).

---

## Local Development

### Backend
```bash
pip install -e .
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| Backend | FastAPI, Python 3.11+, SQLAlchemy, Alembic |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts |
| Database | PostgreSQL (Production) / SQLite (Development) |
| Abstraction | LiteLLM |

---

## Documentation

- [Configuration Guide](docs/CONFIGURATION.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [API Reference](http://localhost:8000/docs)

---

## Contributing

We welcome contributions from the community. Please review our [Contributing Guidelines](CONTRIBUTING.md) before submitting a Pull Request.

---

## Author

**Matthew (BlueT) Lien**
- Twitter: [@BlueT](https://twitter.com/BlueT)
- LinkedIn: [bluet](https://www.linkedin.com/in/bluet/)
- GitHub: [@BlueT](https://github.com/bluet)

---

## License

ArgusLM is released under the [Apache License 2.0](LICENSE).

---

*Named after Argus Panoptes, the all-seeing giant of Greek mythology.*
