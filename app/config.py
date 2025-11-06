from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # API info
    APP_NAME: str = "DocuGenAI+"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"

    # Thresholds
    DUPLICATE_THRESHOLD: float = 0.70
    VAGUE_DESCRIPTION_MIN_LENGTH: int = 20

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

@lru_cache()
def get_settings():
    return Settings()
