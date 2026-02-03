# ArgusLM

**The hundred-eyed watcher for your LLM providers.**

ArgusLM is a comprehensive, self-hosted tool designed to benchmark and monitor the performance of Large Language Models (LLMs) across 100+ providers. Built on top of [LiteLLM](https://github.com/BerriAI/litellm), it provides a unified interface to track uptime, Time to First Token (TTFT), and Tokens Per Second (TPS) for both local and remote LLM endpoints.

> *In Greek mythology, Argus Panoptes was a giant with a hundred eyes. ArgusLM watches over your hundred providers.*

## 🚀 Features

- **Multi-Provider Support**: Seamlessly integrate with OpenAI, Anthropic, AWS Bedrock, Google Vertex, Azure OpenAI, Ollama, LM Studio, and more via LiteLLM.
- **Parallel Benchmarking**: Run performance tests across multiple models simultaneously to compare latency and throughput.
- **Performance Metrics**: Track Time to First Token (TTFT) and Tokens Per Second (TPS) for meaningful cross-model comparison—metrics that matter regardless of output length.
- **Uptime Monitoring**: Configure automated health checks at custom intervals to ensure your LLM services are always available.
- **Real-time Dashboard**: Visualize current status, latency trends, TTFT, and TPS history with interactive charts.
- **Intelligent Alerting**: Receive in-app notifications for model downtime, performance degradation, or global unavailability.
- **Model Discovery**: Automatically detect available models from supported providers or manually configure custom endpoints.
- **Custom Model Naming**: Organize your models with human-readable names for better tracking.
- **Export Results**: Download benchmark data and monitoring history in JSON or CSV formats for further analysis.

## 🛠 Technology Stack

- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: React + TypeScript + Vite
- **Database**: SQLite (Local) / PostgreSQL (Production)
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **Provider Abstraction**: LiteLLM

## 🚦 Quick Start

### Method 1: Docker Compose (Recommended)

The easiest way to get started is using Docker Compose, which sets up the backend, frontend, and database automatically.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/bluet/arguslm.git
   cd arguslm
   ```

2. **Start the services**:
   ```bash
   docker compose up -d
   ```

3. **Access the application**:
   - Web UI: [http://localhost:3000](http://localhost:3000)
   - API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

### Method 2: Local Development

#### Backend Setup

1. **Install dependencies**:
   ```bash
   pip install -e .
   ```

2. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

3. **Start the FastAPI server**:
   ```bash
   uvicorn app.main:app --reload
   ```

#### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start the development server**:
   ```bash
   npm run dev
   ```

## ⚙️ Configuration

ArgusLM can be configured using environment variables. See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for a full reference.

Key variables:
- `DATABASE_URL`: Database connection string (default: `sqlite+aiosqlite:///./arguslm.db`)
- `SECRET_KEY`: Secret key for encryption and security.
- `ENCRYPTION_KEY`: Key used to encrypt provider credentials at rest.

## 📖 Documentation

- [Configuration Guide](docs/CONFIGURATION.md) - Detailed environment and provider setup.
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions.
- **API Reference**: Available at `/docs` when the backend is running.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---

*Named after Argus Panoptes, the all-seeing giant of Greek mythology who had a hundred eyes.*
