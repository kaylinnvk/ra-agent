import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).split("#", 1)[0].strip()
    return int(raw_value or default)

def _env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name, str(default)).split("#", 1)[0].strip().lower()
    return raw_value in {"1", "true", "yes", "on"}

def _env_str(name: str, default: str = "") -> str:
    raw_value = os.getenv(name, default).split("#", 1)[0].strip()
    return raw_value or default

@dataclass(frozen=True)
class Settings:
    ra_website_url: str = field(default_factory=lambda: _env_str("RA_WEBSITE_URL"))
    check_interval_minutes: int = field(default_factory=lambda: _env_int("CHECK_INTERVAL_MINUTES", 360))
    min_score: int = field(default_factory=lambda: _env_int("MIN_SCORE", 2))
    use_system_proxy: bool = field(default_factory=lambda: _env_bool("USE_SYSTEM_PROXY"))
    use_llm_classifier: bool = field(default_factory=lambda: _env_bool("USE_LLM_CLASSIFIER"))
    gemini_api_key: str = field(default_factory=lambda: _env_str("GEMINI_API_KEY"))
    gemini_model: str = field(default_factory=lambda: _env_str("GEMINI_MODEL", "gemini-2.0-flash"))
    gemini_base_url: str = field(default_factory=lambda: _env_str("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"))
    db_backend: str = field(default_factory=lambda: _env_str("DB_BACKEND", "sqlite").lower())
    sqlite_path: str = field(default_factory=lambda: _env_str("SQLITE_PATH", "data/ra_agent.sqlite"))
    database_url: str = field(default_factory=lambda: _env_str("DATABASE_URL"))
    data_retention_days: int = field(default_factory=lambda: _env_int("DATA_RETENTION_DAYS", 90))
    seen_post_touch_interval_hours: int = field(
        default_factory=lambda: _env_int("SEEN_POST_TOUCH_INTERVAL_HOURS", 24)
    )
    use_outlook_source: bool = field(default_factory=lambda: _env_bool("USE_OUTLOOK_SOURCE"))
    microsoft_tenant_id: str = field(default_factory=lambda: _env_str("MICROSOFT_TENANT_ID"))
    microsoft_client_id: str = field(default_factory=lambda: _env_str("MICROSOFT_CLIENT_ID"))
    microsoft_client_secret: str = field(default_factory=lambda: _env_str("MICROSOFT_CLIENT_SECRET"))
    outlook_mailbox: str = field(default_factory=lambda: _env_str("OUTLOOK_MAILBOX"))
    outlook_folder: str = field(default_factory=lambda: _env_str("OUTLOOK_FOLDER", "inbox"))
    outlook_max_messages: int = field(default_factory=lambda: _env_int("OUTLOOK_MAX_MESSAGES", 25))
    outlook_search_query: str = field(default_factory=lambda: _env_str("OUTLOOK_SEARCH_QUERY"))
    graph_base_url: str = field(default_factory=lambda: _env_str("GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0"))
    microsoft_token_url: str = field(default_factory=lambda: _env_str(
        "MICROSOFT_TOKEN_URL",
        f"https://login.microsoftonline.com/{os.getenv('MICROSOFT_TENANT_ID', '').strip()}/oauth2/v2.0/token",
    ))
    gmail_host: str = field(default_factory=lambda: _env_str("GMAIL_HOST", "smtp.gmail.com"))
    gmail_port: int = field(default_factory=lambda: _env_int("GMAIL_PORT", 587))
    gmail_user: str = field(default_factory=lambda: _env_str("GMAIL_USER"))
    gmail_app_password: str = field(default_factory=lambda: _env_str("GMAIL_APP_PASSWORD"))
    gmail_to: str = field(default_factory=lambda: _env_str("GMAIL_TO"))
    gmail_from: str = field(default_factory=lambda: _env_str("GMAIL_FROM"))

settings = Settings()
