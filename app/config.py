from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    proxyapi_key: str = ""
    proxyapi_base_url: str = "https://api.proxyapi.ru/v1"
    llm_model: str = "openai/gpt-4.1-mini"
    llm_temperature: float = 0.2
    llm_timeout_seconds: float = 20.0

    db_path: str = "tickets.db"

    rate_limit_per_minute: int = 5

    log_level: str = "INFO"


settings = Settings()
