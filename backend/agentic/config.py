"""
Centralised configuration loaded from environment variables / .env file.

Production deployments on Azure should inject these values via App Service
configuration / Key Vault references rather than a local file.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv  # type: ignore
    # Walk up from this file looking for the first .env we can find.
    _here = Path(__file__).resolve()
    for parent in [_here.parent, *_here.parents]:
        candidate = parent / ".env"
        if candidate.exists():
            load_dotenv(candidate, override=False)
            break
except Exception:  # pragma: no cover - dotenv is optional
    pass


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    return val


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    azure_endpoint: Optional[str] = field(
        default_factory=lambda: _env("AZURE_OPENAI_ENDPOINT")
    )
    azure_api_key: Optional[str] = field(
        default_factory=lambda: _env("AZURE_OPENAI_API_KEY")
    )
    azure_api_version: str = field(
        default_factory=lambda: _env("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")  # type: ignore[arg-type]
    )
    deployment_primary: str = field(
        default_factory=lambda: _env("AZURE_OPENAI_DEPLOYMENT_PRIMARY", "gpt-5.1")  # type: ignore[arg-type]
    )
    deployment_secondary: str = field(
        default_factory=lambda: _env("AZURE_OPENAI_DEPLOYMENT_SECONDARY", "gpt-5")  # type: ignore[arg-type]
    )
    openai_api_key: Optional[str] = field(
        default_factory=lambda: _env("OPENAI_API_KEY")
    )
    brand: str = field(default_factory=lambda: _env("BRAND", "Philips"))  # type: ignore[arg-type]
    api_port: int = field(default_factory=lambda: int(_env("AGENTIC_API_PORT", "5003")))  # type: ignore[arg-type]
    frontend_port: int = field(default_factory=lambda: int(_env("FRONTEND_PORT", "5000")))  # type: ignore[arg-type]
    cors_origins: str = field(default_factory=lambda: _env("CORS_ALLOWED_ORIGINS", "*"))  # type: ignore[arg-type]
    workspace_dir: Path = field(
        default_factory=lambda: Path(_env("WORKSPACE_DIR", "./.agent_workspace")).resolve()  # type: ignore[arg-type]
    )
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))  # type: ignore[arg-type]

    # ---- Authentication / sessions ----------------------------------------
    auth_enabled: bool = field(default_factory=lambda: _env_bool("AUTH_ENABLED", True))
    ldap_server: str = field(default_factory=lambda: _env("LDAP_SERVER", "161.85.28.34"))  # type: ignore[arg-type]
    ldap_port: int = field(default_factory=lambda: int(_env("LDAP_PORT", "389")))  # type: ignore[arg-type]
    ldap_base: str = field(
        default_factory=lambda: _env("LDAP_BASE", "DC=code1,DC=emi,DC=philips,DC=com")  # type: ignore[arg-type]
    )
    session_expire_seconds: int = field(
        default_factory=lambda: int(_env("SESSION_EXPIRE_SECONDS", "3600"))  # type: ignore[arg-type]
    )
    session_cookie_secure: bool = field(
        default_factory=lambda: _env_bool("SESSION_COOKIE_SECURE", False)
    )
    session_cookie_samesite: str = field(
        default_factory=lambda: _env("SESSION_COOKIE_SAMESITE", "lax")  # type: ignore[arg-type]
    )
    redis_host: str = field(default_factory=lambda: _env("REDIS_HOST", "localhost"))  # type: ignore[arg-type]
    redis_port: int = field(default_factory=lambda: int(_env("REDIS_PORT", "6379")))  # type: ignore[arg-type]
    redis_db: int = field(default_factory=lambda: int(_env("REDIS_DB", "0")))  # type: ignore[arg-type]

    def has_azure(self) -> bool:
        return bool(self.azure_endpoint and self.azure_api_key)

    def has_any_llm(self) -> bool:
        return self.has_azure() or bool(self.openai_api_key)


settings = Settings()
settings.workspace_dir.mkdir(parents=True, exist_ok=True)
