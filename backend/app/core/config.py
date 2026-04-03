"""Application configuration via environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # API keys
    anthropic_api_key: str = ""
    entrez_email: str = "researcher@example.com"

    # Database
    database_url: str = "postgresql://biometa:biometa_secret@localhost:5432/biometa_db"

    # App
    debug: bool = False
    log_level: str = "INFO"
    max_pubmed_results: int = 5000

    # Search
    pubmed_search_terms: list[str] = [
        "microbe metabolite",
        "bacteria metabolite",
        "gut microbiome metabolite",
        "microbial metabolism",
        "fungal metabolite",
    ]
    semantic_search_top_k: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",        # silently ignore POSTGRES_USER/PASSWORD/DB etc.
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
