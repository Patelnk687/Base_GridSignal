"""Runtime configuration. Secrets stay in the environment, never in source."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Public client id published by ERCOT in the registration guide. Not a user secret.
PUBLISHED_CLIENT_ID = "fec253ea-0d06-4272-a5e6-b478baeecd70"
TOKEN_URL = "https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token"
API_ROOT = "https://api.ercot.com/api/public-reports"
TOKEN_SCOPE = f"openid {PUBLISHED_CLIENT_ID} offline_access"


class Settings(BaseSettings):
    """Environment-backed settings.

    The documented auth flow needs a username, password, and APIM subscription key.
    ``ERCOT_CLIENT_SECRET`` is intentionally absent: ERCOT's ROPC examples do not use one.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ercot_username: str = ""
    ercot_password: str = ""
    ercot_subscription_key: str = ""
    ercot_client_id: str = PUBLISHED_CLIENT_ID

    data_mode: str = Field(default="demo", alias="GRIDSIGNAL_DATA_MODE")
    cache_path: Path = Path("data/cache/ercot.sqlite")
    request_timeout_s: float = 30.0
    max_retries: int = 4
    min_request_interval_s: float = 2.1
    page_size: int = 1000

    anomaly_window: int = 12
    anomaly_min_periods: int = 8
    anomaly_z_threshold: float = 3.5
    correlation_window_minutes: int = 90

    llm_provider: str = Field(default="template", alias="GRIDSIGNAL_LLM_PROVIDER")
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1"

    @property
    def live_credentials_ready(self) -> bool:
        return bool(self.ercot_username and self.ercot_password and self.ercot_subscription_key)

    @property
    def resolved_mode(self) -> str:
        if self.data_mode.lower() == "live" and self.live_credentials_ready:
            return "live"
        return "demo"


def load_settings(**overrides: object) -> Settings:
    if not overrides:
        return Settings()
    overrides.setdefault("_env_file", None)
    return Settings(**overrides)  # type: ignore[arg-type]
