"""AWS Bedrock model source adapter.

Discovers models via AWS Bedrock ListFoundationModels API.
Ref: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_ListFoundationModels.html
"""

import logging
from typing import TYPE_CHECKING

from app.discovery.base import ModelDescriptor

if TYPE_CHECKING:
    from app.models.provider import ProviderAccount

logger = logging.getLogger(__name__)

DEFAULT_REGION = "us-east-1"


class BedrockModelSource:
    """Model source for AWS Bedrock.

    Uses boto3 to call ListFoundationModels API.
    Requires AWS credentials (access key, secret key) or IAM role.
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    async def list_models(self, account: "ProviderAccount") -> list[ModelDescriptor]:
        """Fetch available models from AWS Bedrock ListFoundationModels API."""
        try:
            import asyncio

            import boto3
            from botocore.config import Config

            credentials = account.credentials
            region = credentials.get("region", DEFAULT_REGION)

            # Bedrock supports bearer token auth (from AWS console) or IAM credentials
            # ArgusLM stores bearer token in api_key field
            api_key = credentials.get("api_key", "")

            # Create boto3 client with timeout configuration
            config = Config(
                connect_timeout=self.timeout,
                read_timeout=self.timeout,
                retries={"max_attempts": 2},
            )

            # boto3 is synchronous - run in thread pool
            def _list_models() -> list[dict]:
                # If bearer token is provided, we can't use it directly with boto3
                # boto3 requires IAM credentials, not bearer tokens
                # For bearer token auth, users should configure AWS CLI credentials
                client = boto3.client(
                    "bedrock",
                    region_name=region,
                    config=config,
                )
                response = client.list_foundation_models()
                return response.get("modelSummaries", [])

            loop = asyncio.get_event_loop()
            model_summaries = await loop.run_in_executor(None, _list_models)

            models: list[ModelDescriptor] = []
            for model_data in model_summaries:
                model_id = model_data.get("modelId", "")
                if not model_id:
                    continue

                # Filter to only include models that support text generation
                output_modalities = model_data.get("outputModalities", [])
                if "TEXT" not in output_modalities:
                    continue

                # Extract provider from model ID (e.g., "anthropic.claude-3" -> "anthropic")
                provider_name = model_id.split(".")[0] if "." in model_id else "amazon"

                models.append(
                    ModelDescriptor(
                        id=model_id,
                        provider_type=account.provider_type,
                        owned_by=provider_name,
                        created=None,
                        metadata={
                            "model_name": model_data.get("modelName"),
                            "provider_name": model_data.get("providerName"),
                            "input_modalities": model_data.get("inputModalities", []),
                            "output_modalities": output_modalities,
                            "customizations_supported": model_data.get(
                                "customizationsSupported", []
                            ),
                            "inference_types_supported": model_data.get(
                                "inferenceTypesSupported", []
                            ),
                        },
                    )
                )

            logger.info(
                "Discovered %d text models from %s (aws_bedrock, region=%s)",
                len(models),
                account.display_name,
                region,
            )
            return models

        except ImportError:
            logger.error("boto3 not installed - required for AWS Bedrock model discovery")
            return []
        except Exception as e:
            logger.exception("Error discovering AWS Bedrock models: %s", str(e))
            return []

    def supports_discovery(self) -> bool:
        return True
