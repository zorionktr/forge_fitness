"""Typed application settings (12-factor). See docs/09 §6."""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FORGE_", extra="ignore")

    env: Literal["local", "dev", "staging", "prod"] = "local"
    debug: bool = True

    # --- Database / cache ---
    database_url: str = "postgresql+asyncpg://forge:forge@localhost:5432/forge"
    redis_url: str = "redis://localhost:6379/0"
    auto_init_db: bool = False  # on startup, create the vector extension + any missing tables

    # --- Auth ---
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_min: int = 15
    refresh_token_ttl_days: int = 30
    google_client_id: str | None = None
    apple_client_id: str | None = None

    # --- Email (SMTP) for transactional mail like password-reset OTPs ---
    smtp_host: str | None = None         # e.g. smtp.gmail.com; when unset, mail is logged not sent
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True            # STARTTLS (port 587); set False if using SSL or none
    smtp_use_ssl: bool = False           # implicit SSL (port 465)
    smtp_from: str = "no-reply@forge.app"
    smtp_from_name: str = "Forge"
    password_reset_otp_ttl_min: int = 10  # OTP validity window
    password_reset_max_attempts: int = 5  # wrong-code guesses before an OTP is burned

    # --- LLM (provider abstraction, docs/03) ---
    llm_provider: Literal["anthropic", "openai", "gemini", "grok", "local"] = "anthropic"
    anthropic_api_key: str | None = None
    model_chat: str = "claude-sonnet-4-6"
    model_small: str = "claude-haiku-4-5-20251001"
    model_premium: str = "claude-opus-4-8"
    embedding_model: str = "BAAI/bge-m3"  # local sentence-transformers model (docs/04 §3)
    embedding_dim: int = 1024  # BGE-M3 dense dim; keep in sync with the pgvector column

    # --- Local LLM (Ollama) — structures DocTR OCR text into nutrition fields (docs/05 §3.1) ---
    ocr_use_llm: bool = True  # parse OCR text with a local LLM; heuristic parser is the fallback
    local_llm_base_url: str = "http://localhost:11434"  # Ollama endpoint (reachable via host networking)
    ocr_model: str = "qwen2.5:7b"  # local model that turns OCR text into structured macros
    ocr_llm_timeout_s: float = 120.0  # CPU generation is slow; startup warm-up avoids cold-start hits

    # --- Storage / events ---
    s3_bucket: str = "forge-media-local"
    s3_endpoint_url: str | None = None  # MinIO for local
    s3_access_key: str = "forge"        # MinIO root user (local); IAM role in prod
    s3_secret_key: str = "forgeforge"   # MinIO root password (local)
    s3_public_base_url: str | None = None  # public base for media URLs; defaults to endpoint
    aws_region: str = "us-east-1"
    kafka_bootstrap: str = "localhost:9092"
    celery_broker_url: str = "redis://localhost:6379/1"

    # --- Agent budgets ---
    agent_max_tool_calls: int = 8
    agent_max_tokens: int = 4096
    rag_top_k: int = 12


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
