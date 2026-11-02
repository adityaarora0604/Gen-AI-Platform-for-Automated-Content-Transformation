"""Central configuration. All secrets come from environment variables (.env)."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


@dataclass
class Settings:
    llm_provider: str = "demo"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 2
    llm_max_tokens: int = 2500
    max_upload_mb: int = 10
    max_source_chars: int = 60000
    cors_origins: str = "http://localhost:5173"
    database_path: str = "data/jobs.sqlite3"


def get_settings() -> Settings:
    """Read settings fresh each call so tests can override env vars."""
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "demo").strip().lower(),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5").strip(),
        llm_timeout_seconds=_int("LLM_TIMEOUT_SECONDS", 60),
        llm_max_retries=_int("LLM_MAX_RETRIES", 2),
        llm_max_tokens=_int("LLM_MAX_TOKENS", 2500),
        max_upload_mb=_int("MAX_UPLOAD_MB", 10),
        max_source_chars=_int("MAX_SOURCE_CHARS", 60000),
        cors_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173"),
        database_path=os.getenv("DATABASE_PATH", "data/jobs.sqlite3"),
    )
