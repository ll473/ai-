from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "AI 智能商城"
    app_env: str = "development"
    app_debug: bool = False
    api_v1_prefix: str = "/api/v1"

    secret_key: str = "development-only-change-me-at-least-32-bytes"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120

    database_url: str = (
        "mysql+asyncmy://root:password@127.0.0.1:3306/ai_commerce?charset=utf8mb4"
    )
    database_echo: bool = False
    cors_origins: str = "http://localhost:5173"
    upload_dir: Path = PROJECT_ROOT / "uploads"
    max_upload_size_mb: int = 5
    enable_demo_recharge: bool = False
    seed_demo_data: bool = False

    ai_base_url: str | None = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ai_api_key: str | None = None
    ai_chat_model: str | None = "qwen3.7-plus"
    ai_shopping_model: str = "qwen3.7-flash"
    ai_embedding_model: str | None = "qwen3.7-text-embedding"
    ai_embedding_dimensions: int = 1024
    ai_allowed_hosts: str = "dashscope.aliyuncs.com,api.deepseek.com"
    ai_max_runs_per_hour: int = 20
    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "product_knowledge"
    rag_score_threshold: float = 0.2

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if (
            self.app_env.lower() == "production"
            and self.secret_key == "development-only-change-me-at-least-32-bytes"
        ):
            raise ValueError("Production requires an explicit SECRET_KEY")
        return self

    @field_validator("upload_dir", mode="before")
    @classmethod
    def resolve_upload_dir(cls, value: object) -> object:
        if isinstance(value, str):
            path = Path(value)
            return path if path.is_absolute() else PROJECT_ROOT / path
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        """Use SQLAlchemy's async PostgreSQL driver for hosted database URLs."""
        if isinstance(value, str):
            if value.startswith("postgresql://"):
                return value.replace("postgresql://", "postgresql+asyncpg://", 1)
            if value.startswith("postgres://"):
                return value.replace("postgres://", "postgresql+asyncpg://", 1)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def ai_allowed_host_list(self) -> set[str]:
        return {item.strip().lower() for item in self.ai_allowed_hosts.split(",") if item.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
