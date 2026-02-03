# Configuration Reference

ArgusLM is configured primarily through environment variables. This document provides a comprehensive list of available settings and guidance on how to configure various LLM providers.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string. Supports SQLite and PostgreSQL. | `sqlite+aiosqlite:///./arguslm.db` |
| `ENCRYPTION_KEY` | **Required.** Base64-encoded Fernet key for encrypting credentials at rest. | None |
| `SECRET_KEY` | Secret key for session security and internal signing. | `dev-secret-key` |
| `API_TITLE` | Title shown in the API documentation. | `ArgusLM API` |
| `CORS_ORIGINS` | Comma-separated list of allowed CORS origins. | `http://localhost:5173,http://localhost:3000` |
| `LITELLM_LOG_LEVEL` | Logging level for the LiteLLM library. | `INFO` |

### Generating an ENCRYPTION_KEY

You can generate a valid encryption key using the following Python command:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Provider Configuration

When adding a new provider account through the UI or API, you need to provide a `credentials` dictionary. The required fields vary by provider.

### OpenAI
- `api_key`: Your OpenAI API key.
- `base_url` (optional): Custom endpoint if using a proxy.

### Anthropic
- `api_key`: Your Anthropic API key.

### Google Gemini / Vertex AI
- `api_key`: Your Google API key (for Gemini API).
- For Vertex AI, ensure your environment is authenticated with Google Cloud.

### AWS Bedrock
- `aws_access_key_id`: AWS access key.
- `aws_secret_access_key`: AWS secret key.
- `aws_region_name`: AWS region (e.g., `us-east-1`).

### Ollama (Local)
- `base_url`: The URL where Ollama is running (default: `http://localhost:11434`).

### OpenRouter
- `api_key`: Your OpenRouter API key.

### Custom OpenAI-Compatible
- `api_key`: API key for the service.
- `base_url`: The full URL to the V1 API (e.g., `https://my-proxy.com/v1`).

## Monitoring Intervals

Monitoring intervals are configured per-system in the Monitoring settings.
- **Default**: 15 minutes
- **Minimum**: 1 minute
- **Recommended**: 5-30 minutes depending on your budget and needs.

## Alert Rules

Alerts can be configured for:
1. **Any Model Down**: Triggers if any enabled model fails its health check.
2. **Specific Model Down**: Triggers if a specific selected model fails.
3. **Model Unavailable Everywhere**: Triggers if a model (e.g., `gpt-4o`) fails across all configured accounts/providers.
