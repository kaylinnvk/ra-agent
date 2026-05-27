import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).split("#", 1)[0].strip()
    return int(raw_value or default)

def _env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name, str(default)).split("#", 1)[0].strip().lower()
    return raw_value in {"1", "true", "yes", "on"}

@dataclass(frozen=True)
class Settings:
    ra_website_url: str = os.getenv("RA_WEBSITE_URL", "").strip()
    check_interval_minutes: int = _env_int("CHECK_INTERVAL_MINUTES", 360)
    min_score: int = _env_int("MIN_SCORE", 2)
    use_system_proxy: bool = _env_bool("USE_SYSTEM_PROXY")
    use_llm_classifier: bool = _env_bool("USE_LLM_CLASSIFIER")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
    gemini_base_url: str = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").strip()
    use_outlook_source: bool = _env_bool("USE_OUTLOOK_SOURCE")
    microsoft_tenant_id: str = os.getenv("MICROSOFT_TENANT_ID", "").strip()
    microsoft_client_id: str = os.getenv("MICROSOFT_CLIENT_ID", "").strip()
    microsoft_client_secret: str = os.getenv("MICROSOFT_CLIENT_SECRET", "").strip()
    outlook_mailbox: str = os.getenv("OUTLOOK_MAILBOX", "").strip()
    outlook_folder: str = os.getenv("OUTLOOK_FOLDER", "inbox").strip()
    outlook_max_messages: int = _env_int("OUTLOOK_MAX_MESSAGES", 25)
    outlook_search_query: str = os.getenv("OUTLOOK_SEARCH_QUERY", "").strip()
    graph_base_url: str = os.getenv("GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0").strip()
    microsoft_token_url: str = os.getenv(
        "MICROSOFT_TOKEN_URL",
        f"https://login.microsoftonline.com/{os.getenv('MICROSOFT_TENANT_ID', '').strip()}/oauth2/v2.0/token",
    ).strip()
    gmail_host: str = os.getenv("GMAIL_HOST", "smtp.gmail.com").strip()
    gmail_port: int = int(os.getenv("GMAIL_PORT", "587"))
    gmail_user: str = os.getenv("GMAIL_USER", "").strip()
    gmail_app_password: str = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    gmail_to: str = os.getenv("GMAIL_TO", "").strip()
    gmail_from: str = os.getenv("GMAIL_FROM", "").strip()

settings = Settings()
