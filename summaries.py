"""LiteLLM orchestration helpers for NewsNow Neon article summaries.

Updates: v0.50 - 2025-01-07 - Moved summarisation adapters and LiteLLM executor management from the legacy script.
Updates: v0.51 - 2025-10-29 - Honoured provider/API defaults so Azure and other backends configure automatically.
Updates: v0.51.2 - 2025-10-29 - Forced LiteLLM logger levels to track the UI debug toggle so DEBUG noise stops leaking.
Updates: v0.51.1 - 2025-10-29 - Removed unsupported LiteLLM kwargs when targeting Azure deployments.
"""

from __future__ import annotations

import atexit
import logging
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Dict, Optional, Sequence

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    import litellm  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    litellm = None  # type: ignore
else:  # pragma: no cover - debug aid
    if hasattr(litellm, "drop_params"):
        litellm.drop_params = True  # type: ignore[attr-defined]
    if hasattr(litellm, "response_cost_calculator"):

        def _noop_response_cost_calculator(**_kwargs: object) -> None:
            return None

        litellm.response_cost_calculator = _noop_response_cost_calculator  # type: ignore[assignment]


_LITELLM_EXECUTOR = ThreadPoolExecutor(max_workers=4)


def shutdown_executor() -> None:
    _LITELLM_EXECUTOR.shutdown(wait=False)


def configure_litellm_debug(enabled: bool) -> None:
    logger_level = logging.DEBUG if enabled else logging.INFO
    for logger_name in ("LiteLLM", "litellm"):
        llm_logger = logging.getLogger(logger_name)
        # Ensure LiteLLM honours the requested verbosity regardless of its internals.
        llm_logger.setLevel(logger_level)
        for handler in llm_logger.handlers:
            handler.setLevel(logger_level)

    if litellm is None:
        return
    try:
        if enabled:
            if hasattr(litellm, "_turn_on_debug"):
                litellm._turn_on_debug()
            elif hasattr(litellm, "set_verbose"):
                litellm.set_verbose(True)  # type: ignore[attr-defined]
            elif hasattr(litellm, "debug"):
                setattr(litellm, "debug", True)
        else:
            if hasattr(litellm, "_turn_off_debug"):
                litellm._turn_off_debug()
            elif hasattr(litellm, "set_verbose"):
                litellm.set_verbose(False)  # type: ignore[attr-defined]
            elif hasattr(litellm, "debug"):
                setattr(litellm, "debug", False)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.debug("Unable to update LiteLLM debug flag: %s", exc)


def _configured_model_name() -> str:
    explicit = os.getenv("LITELLM_MODEL")
    if explicit:
        return explicit
    specialty_azure = os.getenv("AZURE_CHAT_DEPLOYMENT_GPT5MINI")
    if specialty_azure:
        return f"azure/{specialty_azure}"
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    if deployment:
        return f"azure/{deployment}"
    return ""


def is_gpt5_target(model_name: Optional[str] = None) -> bool:
    if model_name is None:
        model_name = _configured_model_name()
    if not model_name:
        return False
    base = model_name.split("/", 1)[-1].lower()
    return base.startswith("gpt-5")


def prepare_completion_kwargs(
    *,
    messages: Sequence[Dict[str, Any]],
    temperature: float,
    timeout: int,
    max_tokens: Optional[int] = None,
    model_override: Optional[str] = None,
    provider_override: Optional[str] = None,
    api_base_override: Optional[str] = None,
    api_key_override: Optional[str] = None,
    azure_deployment_override: Optional[str] = None,
    azure_api_version_override: Optional[str] = None,
    azure_ad_token_override: Optional[str] = None,
) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        "messages": list(messages),
        "temperature": temperature,
        "max_tokens": max_tokens,
        "request_timeout": timeout,
    }
    if model_override:
        kwargs["model"] = model_override
    if provider_override:
        kwargs["provider"] = provider_override
    if api_base_override:
        kwargs["api_base"] = api_base_override
    if api_key_override:
        kwargs["api_key"] = api_key_override
    if azure_deployment_override:
        kwargs["azure_deployment"] = azure_deployment_override
    if azure_api_version_override:
        kwargs["azure_api_version"] = azure_api_version_override
    if azure_ad_token_override:
        kwargs["azure_ad_token"] = azure_ad_token_override

    final_model = kwargs.get("model")
    if not final_model:
        configured_model = _configured_model_name()
        if configured_model:
            final_model = configured_model
            kwargs["model"] = configured_model

    provider_choice = provider_override or os.getenv("LITELLM_PROVIDER") or os.getenv("NEWS_SUMMARY_PROVIDER")
    provider_choice = (provider_choice or "").lower()
    if not provider_choice and isinstance(final_model, str) and final_model.startswith("azure/"):
        provider_choice = "azure"
    provider = provider_choice or ""

    api_base = kwargs.get("api_base")
    api_key = kwargs.get("api_key")

    if provider == "azure":
        azure_deployment = azure_deployment_override or (
            final_model.split("/", 1)[1] if isinstance(final_model, str) and final_model.startswith("azure/") else None
        ) or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if azure_deployment:
            kwargs["model"] = f"azure/{azure_deployment}"
        api_base = api_base or os.getenv("AZURE_OPENAI_API_BASE") or os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("LITELLM_API_BASE")
        api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("LITELLM_API_KEY")
        api_version = azure_api_version_override or os.getenv("AZURE_OPENAI_API_VERSION") or "2024-10-01-preview"
        kwargs["api_version"] = api_version
        azure_ad_token = kwargs.get("azure_ad_token") or azure_ad_token_override or os.getenv("AZURE_OPENAI_AD_TOKEN")
        if azure_ad_token:
            kwargs["azure_ad_token"] = azure_ad_token
    else:
        api_base = api_base or os.getenv("NEWS_SUMMARY_API_BASE") or os.getenv("LITELLM_API_BASE")
        api_key = api_key or os.getenv("NEWS_SUMMARY_API_KEY") or os.getenv("LITELLM_API_KEY")

    if api_base:
        kwargs["api_base"] = api_base.rstrip("/")
    if api_key:
        kwargs["api_key"] = api_key

    final_model = kwargs.get("model")
    normalized_model = (final_model or "").lower()
    if normalized_model.startswith(("gpt-5-mini", "gpt5-mini")):
        if "temperature" in kwargs:
            kwargs.pop("temperature", None)
            logger.debug("Dropping temperature for %s; not supported.", final_model)
        if "stop" in kwargs:
            kwargs.pop("stop", None)
            logger.debug("Dropping stop parameter for %s; not supported.", final_model)

    return {key: value for key, value in kwargs.items() if value is not None}


def call_litellm(completion_kwargs: Dict[str, Any]) -> Any:
    if litellm is None:
        raise RuntimeError("LiteLLM is not installed")

    future = _LITELLM_EXECUTOR.submit(litellm.completion, **completion_kwargs)
    try:
        return future.result(timeout=completion_kwargs.get("request_timeout"))
    except FuturesTimeoutError:
        future.cancel()
        raise


def extract_completion_text(response: Any) -> Optional[str]:
    choices: Any
    if isinstance(response, dict):
        choices = response.get("choices")
    else:
        choices = getattr(response, "choices", None)

    if not isinstance(choices, list) or not choices:
        return None

    first = choices[0]
    message: Any
    if isinstance(first, dict):
        message = first.get("message")
    else:
        message = getattr(first, "message", None)

    content = None
    if isinstance(message, dict):
        content = message.get("content")
    else:
        content = getattr(message, "content", None)

    if isinstance(content, str):
        stripped = content.strip()
        return stripped if stripped else None

    if isinstance(content, Sequence):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        result = "".join(parts).strip()
        return result if result else None

    return None


def summarize_article(title: str, article_text: str, *, timeout: int) -> str:
    clean_text = article_text.strip()
    if not clean_text:
        return "No article content available to summarize."

    summary_model_env = os.getenv("NEWS_SUMMARY_MODEL")
    summary_provider_env = os.getenv("NEWS_SUMMARY_PROVIDER")
    summary_api_base_env = os.getenv("NEWS_SUMMARY_API_BASE")
    summary_api_key_env = os.getenv("NEWS_SUMMARY_API_KEY")
    summary_azure_deployment_env = os.getenv("NEWS_SUMMARY_AZURE_DEPLOYMENT")
    summary_azure_api_version_env = os.getenv("NEWS_SUMMARY_AZURE_API_VERSION")
    summary_azure_ad_token_env = os.getenv("NEWS_SUMMARY_AZURE_AD_TOKEN")

    summary_model_hint = summary_model_env or (
        f"azure/{summary_azure_deployment_env}" if summary_azure_deployment_env else None
    )

    use_developer_role = (
        is_gpt5_target(summary_model_hint)
        if summary_model_hint
        else is_gpt5_target()
    )
    system_role = "developer" if use_developer_role else "system"

    fallback = "\n\n".join(clean_text.splitlines()[:4])
    if len(fallback) > 800:
        fallback = fallback[:800] + "…"

    if litellm is None:
        logger.info("LiteLLM not installed; returning truncated article excerpt.")
        return fallback

    messages = [
        {
            "role": system_role,
            "content": (
                "Summarize incoming news articles accurately. "
                "Respond with important concise bullet points followed by a final line labelled 'Takeaway:'. "
                "Do not invent facts and avoid marketing language."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Title: {title}\n\n"
                "Article:\n"
                f"{clean_text}"
            ),
        },
    ]

    try:
        completion_kwargs = prepare_completion_kwargs(
            messages=messages,
            temperature=0.2,
            timeout=timeout,
            max_tokens=None,
            model_override=summary_model_env,
            provider_override=summary_provider_env,
            api_base_override=summary_api_base_env,
            api_key_override=summary_api_key_env,
            azure_deployment_override=summary_azure_deployment_env,
            azure_api_version_override=summary_azure_api_version_env,
            azure_ad_token_override=summary_azure_ad_token_env,
        )
        logger.info("Requesting LiteLLM summary using model '%s'.", completion_kwargs.get("model"))
        response = call_litellm(completion_kwargs)
        summary = extract_completion_text(response)
        if summary:
            return summary
        logger.info("LiteLLM article summary missing content; using fallback.")
        return fallback
    except Exception as exc:  # pragma: no cover - network/LLM failure
        logger.warning("LiteLLM article summarization failed: %s", exc)
        return fallback


__all__ = [
    "summarize_article",
    "configure_litellm_debug",
    "prepare_completion_kwargs",
    "call_litellm",
    "extract_completion_text",
    "is_gpt5_target",
    "shutdown_executor",
]

atexit.register(shutdown_executor)
