from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: SecretStr
    openai_api_key: SecretStr
    supabase_url: str
    supabase_key: SecretStr

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="forbid",
        hide_input_in_errors=True,
    )


settings = Settings()