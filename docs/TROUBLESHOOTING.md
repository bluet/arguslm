# Troubleshooting Guide

This document covers common issues you might encounter while using LLM-Perf-Mon and how to resolve them.

## Common Issues

### Provider Connection Failures
**Symptoms**: "Connection test failed" error when adding or testing a provider.
- **Check API Keys**: Ensure your API keys are correct and have not expired.
- **Network Access**: If running in Docker, ensure the container has internet access.
- **Base URL**: For local providers like Ollama or LM Studio, ensure the `base_url` is accessible from within the Docker container (use `host.docker.internal` instead of `localhost` if necessary).

### Model Discovery Not Working
**Symptoms**: No models appear after clicking "Refresh Models".
- **Provider Support**: Not all providers support dynamic model discovery. For Anthropic or Mistral, we use a curated list.
- **Permissions**: Ensure your API key has permissions to list models (e.g., OpenAI `v1/models` endpoint).
- **Logs**: Check the backend logs for specific discovery errors.

### Database Migration Issues
**Symptoms**: Application fails to start with database-related errors.
- **Alembic**: Ensure you have run `alembic upgrade head` to apply the latest schema changes.
- **Database URL**: Verify your `DATABASE_URL` is correct and the database server (if using PostgreSQL) is reachable.

### Docker Networking Problems
**Symptoms**: Frontend cannot connect to the backend, or backend cannot connect to local providers.
- **Internal Host**: Use `http://backend:8000` for frontend-to-backend communication within the Docker network.
- **Host Access**: To access services running on your host machine from Docker, use `http://host.docker.internal:[PORT]`.

## How to Check Logs

### Docker Compose
To view logs for all services:
```bash
docker compose logs -f
```

To view logs for a specific service:
```bash
docker compose logs -f backend
docker compose logs -f frontend
```

### Local Execution
Logs are printed to the standard output of the terminal where you started the `uvicorn` or `npm` process.

## How to Reset the Database

**⚠️ Warning: This will delete all your configuration, benchmark history, and monitoring data.**

### SQLite (Local)
1. Stop the application.
2. Delete the `llm_perf_mon.db` file in the project root.
3. Run `alembic upgrade head` to recreate the schema.

### Docker Compose
1. Stop the services and remove volumes:
   ```bash
   docker compose down -v
   ```
2. Start the services again:
   ```bash
   docker compose up -d
   ```

## Getting Help

If you encounter an issue not covered here, please:
1. Check the [GitHub Issues](https://github.com/your-repo/llm-perf-mon/issues) for similar problems.
2. Open a new issue with detailed steps to reproduce and relevant log output.
