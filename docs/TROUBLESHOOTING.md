# Troubleshooting Guide

This document covers common issues you might encounter while using ArgusLM and how to resolve them.

## Common Issues

### Provider Connection Failures
**Symptoms**: "Connection test failed" error when adding or testing a provider.
- **API Keys**: Verify keys are correct and active.
- **Network Access**: Ensure the environment (or Docker container) has internet access.
- **Base URL**: For local providers (Ollama, LM Studio), use `host.docker.internal` instead of `localhost` if running ArgusLM in Docker.

### LM Studio models not responding
**Symptoms**: Requests to LM Studio time out or return errors.
- **Model Loading**: Ensure the model is loaded in LM Studio and the Local Server is started.
- **Base URL**: Verify the `base_url` includes the `/v1` suffix (e.g., `http://host.docker.internal:1234/v1`).
- **CORS**: Ensure LM Studio's CORS settings allow the ArgusLM dashboard origin.

### Model Discovery Not Working
**Symptoms**: No models appear after clicking "Refresh Models".
- **Provider Support**: Some providers (Anthropic, Mistral) use curated lists instead of dynamic discovery.
- **Permissions**: Ensure the API key has permissions to list models.
- **Logs**: Check backend logs for specific discovery errors.

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

**Warning: This will delete all your configuration, benchmark history, and monitoring data.**

### SQLite (Local)
1. Stop the application.
2. Delete the `arguslm.db` file in the project root.
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
1. Check the [GitHub Issues](https://github.com/bluet/arguslm/issues) for similar problems.
2. Open a new issue with detailed steps to reproduce and relevant log output.
