from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase
    supabase_url: str
    supabase_key: str

    # OpenAI
    openai_api_key: str

    # VAPI (Voice API)
    vapi_api_key: str
    vapi_webhook_secret: str = ""   # optional — leave blank to skip verification

    # Sarvam AI
    sarvam_api_key: str

    # Doctor Contact
    doctor_phone_number: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of the Settings object."""
    return Settings()
