import os

try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic import BaseSettings
    except ImportError:
        class BaseSettings:
            pass

class Settings(BaseSettings):
    # Core settings
    PROJECT_NAME: str = "Betting Platform Data Lakehouse"
    API_V1_STR: str = "/api"
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-key-101")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Databases
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgrespassword@localhost:5432/betting_lakehouse")

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    # MinIO
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9005")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "admin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "supersecretpassword")

    # Nessie
    NESSIE_URI: str = os.getenv("NESSIE_URI", "http://localhost:19120/api/v1")

    # AI & LLM settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")  # "ollama" or "gemini"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")

    class Config:
        case_sensitive = True

settings = Settings()
