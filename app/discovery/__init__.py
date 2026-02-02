"""Model discovery adapters for various LLM providers.

This module provides adapters for discovering available models from different
LLM providers, supporting:
- Discoverable providers (OpenAI, Ollama) via API calls
- Static/curated providers (Anthropic, Mistral) from built-in registry
"""

from app.discovery.base import ModelDescriptor, ModelSource
from app.discovery.ollama import OllamaModelSource
from app.discovery.openai import OpenAIModelSource
from app.discovery.static import StaticModelSource, get_source_for_provider

__all__ = [
    "ModelDescriptor",
    "ModelSource",
    "OpenAIModelSource",
    "OllamaModelSource",
    "StaticModelSource",
    "get_source_for_provider",
]
