from typing import Optional
import os

from .config import settings


def get_full_model_name(provider: str, model: str, base_url: Optional[str] = None) -> str:
    """
    Normalize model names for LiteLLM.

    - For OpenAI + OpenAI-compatible proxies (OpenRouter, Groq, DeepSeek, Custom),
      ensure models go through the `openai/` namespace so LiteLLM routes correctly.
    - For other providers (bedrock, huggingface, ollama, etc.) return the model as-is.
    """
    if provider == "openai":
        # For OpenAI proxies (like OpenRouter), we always prepend 'openai/'
        # to the model string so LiteLLM uses the OpenAI handler but
        # sends the full model name as expected by the proxy.
        if base_url and "api.openai.com" not in str(base_url):
            if not model.startswith("openai/"):
                return f"openai/{model}"
            return model

        # Normal OpenAI flow
        if not model.startswith("openai/"):
            return f"openai/{model}"
        return model

    # Other providers (bedrock, huggingface, ollama, etc.)
    return model


def configure_bedrock_env() -> None:
    """
    Configure AWS Bedrock environment for LiteLLM.

    We use Bedrock's API key flow:
    - API key is stored in LiteClaw config (LLM_API_KEY / VISION_LLM_API_KEY)
      and exported as AWS_BEARER_TOKEN_BEDROCK.
    - Region is taken from AWS_REGION_NAME in settings, if present.

    No AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY are required.
    """
    # Region applies to all Bedrock requests
    aws_region = getattr(settings, "AWS_REGION_NAME", None)
    if aws_region:
        os.environ.setdefault("AWS_REGION_NAME", aws_region)

    # Prefer explicit Bedrock keys if configured
    bedrock_api_key: Optional[str] = None

    if settings.LLM_PROVIDER == "bedrock" and settings.LLM_API_KEY:
        bedrock_api_key = settings.LLM_API_KEY

    if settings.VISION_LLM_PROVIDER == "bedrock" and settings.VISION_LLM_API_KEY:
        # Vision-specific key can override if provided
        bedrock_api_key = settings.VISION_LLM_API_KEY or bedrock_api_key

    if bedrock_api_key:
        os.environ.setdefault("AWS_BEARER_TOKEN_BEDROCK", bedrock_api_key)

