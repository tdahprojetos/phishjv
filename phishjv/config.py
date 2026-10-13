"""Configuração do Phishjv, lida do ambiente / arquivo .env."""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # Segredo para assinar tokens de tracking (HMAC).
    secret: str = Field("dev-secret-troque-em-producao", validation_alias="PHISHJV_SECRET")
    # URL pública base acessível aos alvos.
    base_url: str = Field("http://127.0.0.1:8000", validation_alias="PHISHJV_BASE_URL")
    # Banco de dados.
    database_url: str = Field("sqlite:///./phishjv.db", validation_alias="PHISHJV_DATABASE_URL")

    # SMTP (host vazio => modo dry-run, não envia de verdade).
    smtp_host: str = Field("", validation_alias="SMTP_HOST")
    smtp_port: int = Field(587, validation_alias="SMTP_PORT")
    smtp_user: str = Field("", validation_alias="SMTP_USER")
    smtp_password: str = Field("", validation_alias="SMTP_PASSWORD")
    smtp_from: str = Field("no-reply@exemplo-interno.local", validation_alias="SMTP_FROM")
    smtp_starttls: bool = Field(True, validation_alias="SMTP_STARTTLS")

    @property
    def dry_run(self) -> bool:
        return not self.smtp_host


settings = Settings()
