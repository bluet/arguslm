"""Model discovery adapters for various LLM providers.

This module provides adapters for discovering available models from different
LLM providers, supporting:
- Discoverable providers (OpenAI, Azure OpenAI, Anthropic, Google AI Studio, Bedrock, Ollama)
- Static/curated providers (Google Vertex AI, Mistral) from built-in registry
"""

from arguslm.server.discovery.anthropic import AnthropicModelSource
from arguslm.server.discovery.azure import AzureOpenAIModelSource
from arguslm.server.discovery.base import ModelDescriptor, ModelSource
from arguslm.server.discovery.bedrock import BedrockModelSource
from arguslm.server.discovery.google_ai_studio import GoogleAIStudioModelSource
from arguslm.server.discovery.ollama import OllamaModelSource
from arguslm.server.discovery.openai import OpenAIModelSource
from arguslm.server.discovery.static import StaticModelSource, get_source_for_provider

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
