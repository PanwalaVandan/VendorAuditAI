"""Configuration management using Pydantic Settings."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    app_name: str = "VendorAuditAI"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production-use-secrets-generate"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "sqlite+aiosqlite:///./vendorauditai.db"
    database_echo: bool = False
    database_pool_size: int = 20

    # Storage
    storage_backend: str = "local"  # "local" or "minio"
    local_storage_path: str = "./uploads"
    minio_endpoint: str | None = None
    minio_access_key: str | None = None
    minio_secret_key: str | None = None
    minio_bucket: str = "documents"
    minio_secure: bool = False

    # AI/ML - Provider Selection
    llm_provider: str = "anthropic"  # "anthropic", "gemini", or "deepseek"
    embedding_provider: str = "openai"  # "openai" or "gemini"

    # Anthropic (Claude) - Using Claude Opus 4.5 (Latest as of Jan 2026)
    anthropic_api_key: str | None = None
    claude_model: str = "claude-opus-4-5-20251101"

    # OpenAI
    openai_api_key: str | None = None
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 3072

    # Google Gemini - Using Gemini 3.0 (latest, enhanced capabilities)
    google_api_key: str | None = None
    gemini_model: str = "gemini-3.0-flash"
    gemini_embedding_model: str = "text-embedding-005"

    # DeepSeek - OpenAI-compatible API
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"

    # Document Processing
    azure_doc_intel_endpoint: str | None = None
    azure_doc_intel_key: str | None = None
    use_azure_doc_intel: bool = False

    # Security - JWT
    jwt_secret_key: str = "jwt-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS - Include all known production and development origins
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "https://vendor-audit-ai.netlify.app",
        "https://vendorauditai.netlify.app",
        "https://vendorauditai-production.up.railway.app",
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Convert comma-separated origin string or JSON list string to list."""
        if isinstance(v, str):
            # Strip outer brackets if present
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                v = v[1:-1]
            
            # Split by comma and strip quotes and whitespace from each origin
            return [i.strip().strip("'").strip('"') for i in v.split(",") if i.strip()]
        return v

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # SSO/SAML 2.0
    sso_sp_entity_id: str = "https://vendorauditai.com/sso"
    sso_callback_url: str = "https://vendorauditai.com/api/v1/sso/acs"

    # Celery (optional - for async task processing)
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    use_celery: bool = False

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"

    @property
    def database_is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        return "sqlite" in self.database_url.lower()


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
