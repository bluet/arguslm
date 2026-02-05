"""Provider Account CRUD API endpoints."""

import logging
import time
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas.provider import (
    ProviderCreate,
    ProviderListResponse,
    ProviderRefreshResponse,
    ProviderResponse,
    ProviderTestResponse,
    ProviderUpdate,
)
from app.core.litellm_client import LiteLLMClient
from app.db.init import get_db
from app.discovery import get_source_for_provider
from app.discovery.anthropic import AnthropicModelSource
from app.discovery.azure import AzureOpenAIModelSource
from app.discovery.bedrock import BedrockModelSource
from app.discovery.google_ai_studio import GoogleAIStudioModelSource
from app.discovery.ollama import OllamaModelSource
from app.discovery.openai import OpenAIModelSource
from app.models.model import Model
from app.models.provider import ProviderAccount

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/providers", tags=["providers"])


@router.post("", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    provider_data: ProviderCreate,
    db: AsyncSession = Depends(get_db),
) -> ProviderResponse:
    """Create a new provider account.

    Args:
        provider_data: Provider creation data
        db: Database session

    Returns:
        Created provider account (without credentials)
    """
    # Create provider account
    provider = ProviderAccount(
        provider_type=provider_data.provider_type,
        display_name=provider_data.display_name,
        enabled=True,
    )
    # Set credentials (will be encrypted via property setter)
    provider.credentials = provider_data.credentials

    db.add(provider)
    await db.commit()
    await db.refresh(provider)

    logger.info(
        "Created provider account: %s (%s)",
        provider.display_name,
        provider.provider_type,
    )

    return ProviderResponse.model_validate(provider)


@router.get("", response_model=ProviderListResponse)
async def list_providers(
    db: AsyncSession = Depends(get_db),
) -> ProviderListResponse:
    """List all provider accounts.

    Args:
        db: Database session

    Returns:
        List of provider accounts (without credentials)
    """
    result = await db.execute(select(ProviderAccount).order_by(ProviderAccount.created_at))
    providers = result.scalars().all()

    return ProviderListResponse(
        providers=[ProviderResponse.model_validate(p) for p in providers],
        total=len(providers),
    )


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ProviderResponse:
    """Get a single provider account by ID.

    Args:
        provider_id: Provider account UUID
        db: Database session

    Returns:
        Provider account (without credentials)

    Raises:
        HTTPException: 404 if provider not found
    """
    result = await db.execute(select(ProviderAccount).where(ProviderAccount.id == provider_id))
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider account {provider_id} not found",
        )

    return ProviderResponse.model_validate(provider)


@router.patch("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: UUID,
    update_data: ProviderUpdate,
    db: AsyncSession = Depends(get_db),
) -> ProviderResponse:
    """Update a provider account.

    Args:
        provider_id: Provider account UUID
        update_data: Fields to update
        db: Database session

    Returns:
        Updated provider account (without credentials)

    Raises:
        HTTPException: 404 if provider not found
    """
    result = await db.execute(select(ProviderAccount).where(ProviderAccount.id == provider_id))
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider account {provider_id} not found",
        )

    # Update fields if provided
    if update_data.display_name is not None:
        provider.display_name = update_data.display_name
    if update_data.credentials is not None:
        provider.credentials = update_data.credentials
    if update_data.enabled is not None:
        provider.enabled = update_data.enabled

    await db.commit()
    await db.refresh(provider)

    logger.info("Updated provider account: %s", provider.display_name)

    return ProviderResponse.model_validate(provider)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a provider account.

    Args:
        provider_id: Provider account UUID
        db: Database session

    Raises:
        HTTPException: 404 if provider not found
        HTTPException: 409 if provider has models with benchmark history
    """
    result = await db.execute(
        select(ProviderAccount)
        .where(ProviderAccount.id == provider_id)
        .options(selectinload(ProviderAccount.models).selectinload(Model.benchmark_results))
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider account {provider_id} not found",
        )

    # Check if any models have benchmark results
    has_benchmark_history = any(len(model.benchmark_results) > 0 for model in provider.models)

    if has_benchmark_history:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete provider with models that have benchmark history",
        )

    await db.delete(provider)
    await db.commit()

    logger.info("Deleted provider account: %s", provider.display_name)


# LiteLLM provider prefixes for model names
LITELLM_PROVIDER_PREFIXES: dict[str, str] = {
    "openai": "",
    "anthropic": "anthropic/",
    "azure_openai": "azure/",
    "aws_bedrock": "bedrock/",
    "google_vertex": "vertex_ai/",
    "google_ai_studio": "gemini/",
    "together_ai": "together_ai/",
    "groq": "groq/",
    "mistral": "mistral/",
    "ollama": "ollama/",
    "lm_studio": "openai/",
    "openrouter": "openrouter/",
    "custom_openai_compatible": "openai/",
}


async def _test_local_provider_ping(base_url: str, provider_type: str) -> ProviderTestResponse:
    """Test local provider (Ollama/LM Studio) by pinging its API endpoint."""
    if provider_type == "ollama":
        test_url = f"{base_url.rstrip('/')}/api/tags"
    else:
        test_url = f"{base_url.rstrip('/')}/models"

    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(test_url)
            latency_ms = (time.perf_counter() - start) * 1000

            if response.status_code == 200:
                data = response.json()
                model_count = len(data.get("models", data.get("data", [])))
                return ProviderTestResponse(
                    success=True,
                    message=f"Server reachable, {model_count} model(s) available ({int(latency_ms)}ms)",
                    details={"models_found": model_count, "latency_ms": int(latency_ms)},
                )
            else:
                return ProviderTestResponse(
                    success=False,
                    message=f"Server returned status {response.status_code}",
                    details={"status_code": response.status_code},
                )
    except httpx.ConnectError as e:
        return ProviderTestResponse(
            success=False,
            message=f"Cannot connect to {base_url}. Check if server is running.",
            details={"error_type": "ConnectError", "hint": str(e)},
        )
    except Exception as e:
        return ProviderTestResponse(
            success=False,
            message=f"Connection test failed: {str(e)}",
            details={"error_type": type(e).__name__},
        )


@router.post("/test-connection", response_model=ProviderTestResponse)
async def test_new_provider_connection(
    provider_data: ProviderCreate,
) -> ProviderTestResponse:
    """Test connection for a new provider before saving."""
    credentials = provider_data.credentials
    api_key = credentials.get("api_key")
    api_base = credentials.get("base_url")

    if provider_data.provider_type in ("ollama", "lm_studio"):
        if not api_base:
            return ProviderTestResponse(
                success=False,
                message="Base URL is required for local providers",
                details={},
            )
        return await _test_local_provider_ping(api_base, provider_data.provider_type)

    test_models = {
        "openai": "gpt-3.5-turbo",
        "anthropic": "anthropic/claude-3-haiku-20240307",
        "google_ai_studio": "gemini/gemini-1.5-flash",
        "groq": "groq/llama3-8b-8192",
        "mistral": "mistral/mistral-small-latest",
        "together_ai": "together_ai/meta-llama/Llama-3-8b-chat-hf",
        "openrouter": "openrouter/meta-llama/llama-3-8b-instruct",
    }
    test_model = test_models.get(provider_data.provider_type, "gpt-3.5-turbo")

    try:
        client = LiteLLMClient(default_timeout=10.0, default_max_retries=1)
        response = await client.complete(
            model=test_model,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=10,
            api_key=api_key,
            api_base=api_base,
        )

        logger.info("Connection test successful for new provider: %s", provider_data.display_name)

        return ProviderTestResponse(
            success=True,
            message=f"Successfully connected to {provider_data.provider_type}",
            details={"model_tested": test_model, "response_id": response.get("id")},
        )

    except Exception as e:
        logger.error(
            "Connection test failed for new provider %s: %s",
            provider_data.display_name,
            str(e),
        )
        return ProviderTestResponse(
            success=False,
            message=f"Connection test failed: {str(e)}",
            details={"error_type": type(e).__name__},
        )


@router.post("/{provider_id}/test", response_model=ProviderTestResponse)
async def test_provider_connection(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ProviderTestResponse:
    """Test provider connection using LiteLLM.

    Args:
        provider_id: Provider account UUID
        db: Database session

    Returns:
        Test result with success status and message

    Raises:
        HTTPException: 404 if provider not found
    """
    result = await db.execute(select(ProviderAccount).where(ProviderAccount.id == provider_id))
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider account {provider_id} not found",
        )

    if not provider.provider_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider type is missing or invalid",
        )

    credentials = provider.credentials
    api_key = credentials.get("api_key")
    api_base = credentials.get("base_url")

    if provider.provider_type in ("ollama", "lm_studio"):
        if not api_base:
            return ProviderTestResponse(
                success=False,
                message="Base URL is required for local providers",
                details={},
            )
        return await _test_local_provider_ping(api_base, provider.provider_type)

    test_models = {
        "openai": "gpt-3.5-turbo",
        "anthropic": "anthropic/claude-3-haiku-20240307",
        "google_ai_studio": "gemini/gemini-1.5-flash",
        "groq": "groq/llama3-8b-8192",
        "mistral": "mistral/mistral-small-latest",
        "together_ai": "together_ai/meta-llama/Llama-3-8b-chat-hf",
        "openrouter": "openrouter/meta-llama/llama-3-8b-instruct",
    }
    test_model = test_models.get(provider.provider_type, "gpt-3.5-turbo")

    try:
        client = LiteLLMClient(default_timeout=10.0, default_max_retries=1)
        response = await client.complete(
            model=test_model,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=10,
            api_key=api_key,
            api_base=api_base,
        )

        logger.info("Connection test successful for provider: %s", provider.display_name)

        return ProviderTestResponse(
            success=True,
            message=f"Successfully connected to {provider.provider_type}",
            details={"model_tested": test_model, "response_id": response.get("id")},
        )

    except Exception as e:
        logger.error(
            "Connection test failed for provider %s: %s",
            provider.display_name,
            str(e),
        )
        return ProviderTestResponse(
            success=False,
            message=f"Connection test failed: {str(e)}",
            details={"error_type": type(e).__name__},
        )


@router.post("/{provider_id}/refresh-models", response_model=ProviderRefreshResponse)
async def refresh_provider_models(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ProviderRefreshResponse:
    """Trigger model discovery for a provider.

    Args:
        provider_id: Provider account UUID
        db: Database session

    Returns:
        Refresh result with number of models discovered

    Raises:
        HTTPException: 404 if provider not found
    """
    result = await db.execute(select(ProviderAccount).where(ProviderAccount.id == provider_id))
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider account {provider_id} not found",
        )

    # Validate provider_type is not None
    if not provider.provider_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider type is missing or invalid",
        )

    model_source = None
    if provider.provider_type == "ollama":
        model_source = OllamaModelSource()
    elif provider.provider_type == "azure_openai":
        model_source = AzureOpenAIModelSource()
    elif provider.provider_type == "anthropic":
        model_source = AnthropicModelSource()
    elif provider.provider_type == "google_ai_studio":
        model_source = GoogleAIStudioModelSource()
    elif provider.provider_type == "aws_bedrock":
        model_source = BedrockModelSource()
    elif provider.provider_type in [
        "openai",
        "openrouter",
        "together_ai",
        "groq",
        "lm_studio",
        "custom_openai_compatible",
    ]:
        model_source = OpenAIModelSource()
    else:
        model_source = get_source_for_provider(provider.provider_type)

    if not model_source:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model discovery not supported for provider type: {provider.provider_type}",
        )

    # Discover models
    try:
        model_descriptors = await model_source.list_models(provider)

        # Get existing models for this provider
        existing_result = await db.execute(
            select(Model).where(Model.provider_account_id == provider_id)
        )
        existing_models = {m.model_id: m for m in existing_result.scalars().all()}

        # Add new models
        new_count = 0
        for descriptor in model_descriptors:
            if descriptor.id not in existing_models:
                new_model = Model(
                    provider_account_id=provider_id,
                    model_id=descriptor.id,
                    source="discovered",
                    enabled_for_benchmark=True,
                    enabled_for_monitoring=False,
                    model_metadata=descriptor.metadata,
                )
                db.add(new_model)
                new_count += 1

        await db.commit()

        logger.info(
            "Refreshed models for provider %s: %d discovered, %d new",
            provider.display_name,
            len(model_descriptors),
            new_count,
        )

        return ProviderRefreshResponse(
            success=True,
            models_discovered=len(model_descriptors),
            message=f"Discovered {len(model_descriptors)} models, added {new_count} new models",
        )

    except Exception as e:
        logger.error(
            "Model refresh failed for provider %s: %s",
            provider.display_name,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model refresh failed: {str(e)}",
        )
