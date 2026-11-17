import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


logger = logging.getLogger(__name__)


class DiaryConfig(BaseModel):
    label: str
    sheet: str
    required_fields: list[str] = Field(default_factory=list)
    columns: dict[str, str] = Field(default_factory=dict)
    supports_invoice_items: bool = False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str
    telegram_bot_token: str
    google_sheets_credentials_path: str = "./service-account.json"
    google_spreadsheet_id: str
    timezone: str = "Europe/Sofia"
    pending_ttl_seconds: int = 600
    sqlite_path: str = "./data/haccp.db"
    users_config_path: str = "./config/users.yaml"
    diaries_config_path: str = "./config/diaries.yaml"
    openai_model: str = "gpt-4o-mini"


_settings: Settings | None = None
_diaries: dict[str, DiaryConfig] | None = None
_users: dict[str, str] | None = None
_classification_hints: dict[str, list[str]] | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def load_diaries_config(path: str | None = None) -> dict[str, DiaryConfig]:
    global _diaries, _classification_hints
    config_path = Path(path or get_settings().diaries_config_path)
    with config_path.open(encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    _classification_hints = raw.get("classification_hints", {})
    _diaries = {key: DiaryConfig(**value) for key, value in raw["diaries"].items()}
    return _diaries


def get_diaries() -> dict[str, DiaryConfig]:
    if _diaries is None:
        load_diaries_config()
    assert _diaries is not None
    return _diaries


def get_classification_hints() -> dict[str, list[str]]:
    if _classification_hints is None:
        load_diaries_config()
    assert _classification_hints is not None
    return _classification_hints


def load_users(path: str | None = None) -> dict[str, str]:
    global _users
    config_path = Path(path or get_settings().users_config_path)
    if not config_path.exists():
        # Fail closed: a missing allowlist authorizes nobody (the example file is never loaded).
        logger.warning("Users config not found at %s; no Telegram user is authorized.", config_path)
        _users = {}
        return _users

    with config_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    _users = {str(k): str(v) for k, v in (raw.get("users") or {}).items()}
    return _users


def get_users() -> dict[str, str]:
    if _users is None:
        load_users()
    assert _users is not None
    return _users
