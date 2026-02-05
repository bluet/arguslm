"""Provider catalog - single source of truth for all provider configuration."""

from dataclasses import dataclass, field
from typing import Optional

from litellm.constants import LITELLM_CHAT_PROVIDERS


@dataclass(frozen=True)
class ProviderSpec:
    """Provider configuration specification."""

    id: str
    label: str
    tested: bool = False
    requires_api_key: bool = True
    requires_base_url: bool = False
    requires_region: bool = False
    show_org_fields: bool = False
    default_base_url: Optional[str] = None
    api_key_label: Optional[str] = None
    base_url_label: Optional[str] = None
    region_options: tuple[tuple[str, str], ...] = field(default_factory=tuple)


TESTED_PROVIDERS: set[str] = {
    "openai",
    "anthropic",
    "google_vertex",
    "google_ai_studio",
    "aws_bedrock",
    "azure_openai",
    "ollama",
    "lm_studio",
    "openrouter",
    "together_ai",
    "groq",
    "mistral",
    "xai",
    "fireworks_ai",
    "deepseek",
    "custom_openai_compatible",
}

AWS_REGIONS: tuple[tuple[str, str], ...] = (
    ("us-east-1", "US East (N. Virginia)"),
    ("us-east-2", "US East (Ohio)"),
    ("us-west-1", "US West (N. California)"),
    ("us-west-2", "US West (Oregon)"),
    ("ca-central-1", "Canada (Central)"),
    ("ca-west-1", "Canada West (Calgary)"),
    ("sa-east-1", "South America (Sao Paulo)"),
    ("eu-west-1", "Europe (Ireland)"),
    ("eu-west-2", "Europe (London)"),
    ("eu-west-3", "Europe (Paris)"),
    ("eu-central-1", "Europe (Frankfurt)"),
    ("eu-central-2", "Europe (Zurich)"),
    ("eu-north-1", "Europe (Stockholm)"),
    ("eu-south-1", "Europe (Milan)"),
    ("eu-south-2", "Europe (Spain)"),
    ("ap-northeast-1", "Asia Pacific (Tokyo)"),
    ("ap-northeast-2", "Asia Pacific (Seoul)"),
    ("ap-northeast-3", "Asia Pacific (Osaka)"),
    ("ap-southeast-1", "Asia Pacific (Singapore)"),
    ("ap-southeast-2", "Asia Pacific (Sydney)"),
    ("ap-southeast-3", "Asia Pacific (Jakarta)"),
    ("ap-southeast-4", "Asia Pacific (Melbourne)"),
    ("ap-southeast-5", "Asia Pacific (Malaysia)"),
    ("ap-southeast-7", "Asia Pacific (Thailand)"),
    ("ap-south-1", "Asia Pacific (Mumbai)"),
    ("ap-south-2", "Asia Pacific (Hyderabad)"),
    ("ap-east-2", "Asia Pacific (Taipei)"),
    ("af-south-1", "Africa (Cape Town)"),
    ("me-south-1", "Middle East (Bahrain)"),
    ("me-central-1", "Middle East (UAE)"),
    ("il-central-1", "Israel (Tel Aviv)"),
    ("mx-central-1", "Mexico (Central)"),
)

_TESTED_PROVIDER_SPECS: dict[str, ProviderSpec] = {
    "openai": ProviderSpec(
        id="openai",
        label="OpenAI",
        tested=True,
        show_org_fields=True,
        default_base_url="https://api.openai.com/v1",
    ),
    "anthropic": ProviderSpec(
        id="anthropic",
        label="Anthropic",
        tested=True,
        default_base_url="https://api.anthropic.com",
    ),
    "google_vertex": ProviderSpec(
        id="google_vertex",
        label="Google Vertex AI",
        tested=True,
    ),
    "google_ai_studio": ProviderSpec(
        id="google_ai_studio",
        label="Google AI Studio",
        tested=True,
        default_base_url="https://generativelanguage.googleapis.com/v1beta",
    ),
    "aws_bedrock": ProviderSpec(
        id="aws_bedrock",
        label="AWS Bedrock",
        tested=True,
        requires_region=True,
        api_key_label="Bearer Token (from AWS Bedrock Console)",
        region_options=AWS_REGIONS,
    ),
    "azure_openai": ProviderSpec(
        id="azure_openai",
        label="Azure OpenAI",
        tested=True,
        requires_base_url=True,
    ),
    "ollama": ProviderSpec(
        id="ollama",
        label="Ollama",
        tested=True,
        requires_api_key=False,
        requires_base_url=True,
        base_url_label="Base URL",
        default_base_url="http://host.docker.internal:11434",
    ),
    "lm_studio": ProviderSpec(
        id="lm_studio",
        label="LM Studio",
        tested=True,
        requires_api_key=False,
        requires_base_url=True,
        base_url_label="Base URL",
        default_base_url="http://host.docker.internal:1234/v1",
    ),
    "openrouter": ProviderSpec(
        id="openrouter",
        label="OpenRouter",
        tested=True,
        default_base_url="https://openrouter.ai/api/v1",
    ),
    "together_ai": ProviderSpec(
        id="together_ai",
        label="Together AI",
        tested=True,
        default_base_url="https://api.together.xyz/v1",
    ),
    "groq": ProviderSpec(
        id="groq",
        label="Groq",
        tested=True,
        default_base_url="https://api.groq.com/openai/v1",
    ),
    "mistral": ProviderSpec(
        id="mistral",
        label="Mistral AI",
        tested=True,
        default_base_url="https://api.mistral.ai/v1",
    ),
    "xai": ProviderSpec(
        id="xai",
        label="xAI (Grok)",
        tested=True,
        default_base_url="https://api.x.ai/v1",
    ),
    "fireworks_ai": ProviderSpec(
        id="fireworks_ai",
        label="Fireworks AI",
        tested=True,
        default_base_url="https://api.fireworks.ai/inference/v1",
    ),
    "deepseek": ProviderSpec(
        id="deepseek",
        label="DeepSeek",
        tested=True,
        default_base_url="https://api.deepseek.com",
    ),
    "custom_openai_compatible": ProviderSpec(
        id="custom_openai_compatible",
        label="Custom OpenAI Compatible",
        tested=True,
        requires_base_url=True,
    ),
}


def _generate_label(provider_id: str) -> str:
    """Generate human-readable label from provider ID."""
    return provider_id.replace("_", " ").title().replace("Ai", "AI").replace("Openai", "OpenAI")


def _build_catalog() -> dict[str, ProviderSpec]:
    """Build complete catalog from tested specs + LiteLLM providers."""
    catalog: dict[str, ProviderSpec] = dict(_TESTED_PROVIDER_SPECS)

    for provider_id in LITELLM_CHAT_PROVIDERS:
        if provider_id not in catalog:
            catalog[provider_id] = ProviderSpec(
                id=provider_id,
                label=_generate_label(provider_id),
                tested=False,
            )

    return catalog


PROVIDER_CATALOG: dict[str, ProviderSpec] = _build_catalog()


def get_provider_spec(provider_type: str) -> ProviderSpec:
    """Get provider spec, returning default for unknown providers."""
    if provider_type in PROVIDER_CATALOG:
        return PROVIDER_CATALOG[provider_type]
    return ProviderSpec(
        id=provider_type,
        label=_generate_label(provider_type),
        tested=False,
    )


def get_litellm_model_name(provider_type: str, model_id: str) -> str:
    """Format model name with LiteLLM provider prefix."""
    if provider_type == "openai":
        prefix = ""
    elif provider_type == "azure_openai":
        prefix = "azure/"
    elif provider_type == "aws_bedrock":
        prefix = "bedrock/"
    elif provider_type == "google_vertex":
        prefix = "vertex_ai/"
    elif provider_type == "google_ai_studio":
        prefix = "gemini/"
    elif provider_type == "custom_openai_compatible":
        prefix = "openai/"
    else:
        prefix = f"{provider_type}/"

    if prefix and not model_id.startswith(prefix):
        return f"{prefix}{model_id}"
    return model_id


def get_all_provider_types() -> list[str]:
    """Get sorted list of all provider type IDs."""
    tested = sorted(p for p in PROVIDER_CATALOG if PROVIDER_CATALOG[p].tested)
    untested = sorted(p for p in PROVIDER_CATALOG if not PROVIDER_CATALOG[p].tested)
    return tested + untested
