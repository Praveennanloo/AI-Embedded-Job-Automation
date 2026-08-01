from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI Embedded Job Automation"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    DATABASE_NAME: str = "jobs.db"

    SEARCH_INTERVAL_MINUTES: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
