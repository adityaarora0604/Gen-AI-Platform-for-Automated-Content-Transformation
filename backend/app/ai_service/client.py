"""AI service: the only module that talks to an LLM provider. (Owner: Anishk)

* API keys come from environment variables only.
* Handles rate limits, timeouts, connection errors and empty responses with retries.
* Never logs prompts or source content.
"""
import logging
import time

from app.config import get_settings
from app.schemas import AppError

log = logging.getLogger("ai_service")

SUPPORTED_PROVIDERS = {"anthropic", "demo"}


class LLMError(AppError):
    """Error raised for LLM failures. `retryable` tells the retry loop whether to try again."""

    def __init__(self, message: str, status_code: int = 502, retryable: bool = False):
        super().__init__(message, status_code)
        self.retryable = retryable


def provider() -> str:
    return get_settings().llm_provider


def is_demo() -> bool:
    return provider() == "demo"


def model_name() -> str:
    return "demo-rule-based" if is_demo() else get_settings().anthropic_model


def check_configuration() -> None:
    """Raise a clear setup message if the provider is not usable."""
    s = get_settings()
    if s.llm_provider not in SUPPORTED_PROVIDERS:
        raise AppError(
            f"Unsupported LLM_PROVIDER '{s.llm_provider}'. Use 'anthropic' or 'demo' in backend/.env.", 500
        )
    if s.llm_provider == "anthropic" and not s.anthropic_api_key:
        raise AppError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to backend/.env and add your key, "
            "or set LLM_PROVIDER=demo to use the clearly labelled demo mode.",
            503,
        )


def _call_anthropic(system: str, user: str, max_tokens: int, timeout: int) -> str:
    """One raw call to the Anthropic Messages API. Translates SDK errors into LLMError."""
    try:
        import anthropic
    except ImportError as e:  # pragma: no cover
        raise LLMError("The 'anthropic' package is not installed (pip install -r requirements.txt).", 500) from e

    s = get_settings()
    client = anthropic.Anthropic(api_key=s.anthropic_api_key, timeout=timeout, max_retries=0)
    try:
        resp = client.messages.create(
            model=s.anthropic_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.RateLimitError as e:
        raise LLMError("The AI provider rate limit was reached. Please wait a moment and try again.", 429, True) from e
    except anthropic.APITimeoutError as e:
        raise LLMError("The AI provider timed out. Try again or shorten the source text.", 504, True) from e
    except anthropic.APIConnectionError as e:
        raise LLMError("Could not connect to the AI provider. Check your internet connection.", 502, True) from e
    except anthropic.AuthenticationError as e:
        raise LLMError("The AI provider rejected the API key. Check ANTHROPIC_API_KEY in backend/.env.", 502, False) from e
    except anthropic.APIStatusError as e:
        raise LLMError(f"The AI provider returned an error (HTTP {e.status_code}).", 502, e.status_code >= 500) from e
    return "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")


def complete(system: str, user: str, max_tokens: int = None) -> str:
    """Call the configured LLM with retries and return the response text."""
    check_configuration()
    if is_demo():
        raise LLMError("complete() must not be used in demo mode.", 500)
    s = get_settings()
    attempts = 1 + max(0, s.llm_max_retries)
    last_error = None
    for i in range(attempts):
        try:
            text = _call_anthropic(system, user, max_tokens or s.llm_max_tokens, s.llm_timeout_seconds)
            if not text or not text.strip():
                raise LLMError("The AI provider returned an empty response.", 502, True)
            return text.strip()
        except LLMError as e:
            last_error = e
            log.warning("LLM call failed (attempt %s/%s): %s", i + 1, attempts, e.message)
            if not e.retryable or i == attempts - 1:
                raise
            time.sleep(min(2**i, 8))
    raise last_error  # pragma: no cover
