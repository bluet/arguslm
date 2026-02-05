"""Model discovery adapters for various LLM providers.

This module provides adapters for discovering available models from different
LLM providers, supporting:
- Discoverable providers (OpenAI, Azure OpenAI, Anthropic, Google AI Studio, Bedrock, Ollama)
- Static/curated providers (Google Vertex AI, Mistral) from built-in registry
"""

from app.discovery.anthropic import AnthropicModelSource
from app.discovery.azure import AzureOpenAIModelSource
from app.discovery.base import ModelDescriptor, ModelSource
from app.discovery.bedrock import BedrockModelSource
from app.discovery.google_ai_studio import GoogleAIStudioModelSource
from app.discovery.ollama import OllamaModelSource
from app.discovery.openai import OpenAIModelSource
from app.discovery.static import StaticModelSource, get_source_for_provider

__all__ = [
    "ModelDescriptor",
    "ModelSource",
    "OpenAIModelSource",
    "AzureOpenAIModelSource",
    "AnthropicModelSource",
    "GoogleAIStudioModelSource",
    "BedrockModelSource",
    "OllamaModelSource",
    "StaticModelSource",
    "get_source_for_provider",
]
