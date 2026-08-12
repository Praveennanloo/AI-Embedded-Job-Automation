from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI Embedded Job Automation"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    DATABASE_NAME: str = "jobs.db"

    SEARCH_INTERVAL_MINUTES: int = 15
    ENABLE_LOCATION_FILTER: bool = True
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
