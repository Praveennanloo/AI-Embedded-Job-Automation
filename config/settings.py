from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI Embedded Job Automation"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    DATABASE_NAME: str = "jobs.db"

    SEARCH_INTERVAL_MINUTES: int = 15
    PROVIDER_TIMEOUT_SECONDS: float = 20.0
    PROVIDER_MAX_RETRIES: int = 3
    PROVIDER_BASE_DELAY_SECONDS: float = 1.0
    PROVIDER_MAX_DELAY_SECONDS: float = 30.0
    ENABLE_LOCATION_FILTER: bool = True
    REQUIRE_ENTRY_LEVEL: bool = True
    LOCATION_KEYWORDS: list[str] = [
        "hyderabad",
        "bangalore",
        "bengaluru",
        "chennai",
        "pune",
        "visakhapatnam",
        "vizag",
        "remote",
        "india",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
