"""Configuration management with Pydantic validation."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_OUTPUT_DIR = Path("./outreach_results")
"""Default directory for output files."""


class Config(BaseSettings):
    """Application configuration from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Ocean.io API
    ocean_api_key: str = Field(description="Ocean.io API key")
    ocean_base_url: str = "https://api.ocean.io/v3"

    # Prospeo API
    prospeo_api_key: str = Field(description="Prospeo API key")
    prospeo_base_url: str = "https://api.prospeo.io"

    # Brevo (Sendinblue) API
    brevo_api_key: str = Field(description="Brevo API key")
    brevo_base_url: str = "https://api.brevo.com/v3"

    # Email defaults (can be overridden via CLI flags)
    from_email: str = "hello@example.com"  # Default sender email address
    from_name: str = "Outreach Team"       # Default sender display name
    email_subject: str = "Exciting Opportunity Awaits You"
    email_html: str = '<html><body><p>Hi {{first_name}},</p><p>We noticed your impressive work at {{company_name}} and think you might be interested in what we have to offer.</p><p>Looking forward to hearing from you!</p></body></html>'  # noqa: E501

    # Rate limits & pagination
    requests_per_second: float = 1.0
    max_retries: int = 5
    retry_backoff_factor: float = 1.5
    retry_statuses: tuple[int, ...] = (429, 500, 502, 503, 504)
    page_size: int = 50
    max_pages: int = 10

    # Application limits
    max_companies: int = 100
    max_contacts_per_company: int = 5
    email_deduplication_window_days: int = 30

    # Output
    output_dir: Path = DEFAULT_OUTPUT_DIR
    log_level: str = "INFO"

    @field_validator("output_dir", mode="before")
    @classmethod
    def _resolve_output_dir(cls, v: str | Path) -> Path:
        """Ensure output_dir is a Path."""
        if isinstance(v, str):
            return Path(v)
        return v

    def ensure_dirs(self) -> None:
        """Create required directories."""
        self.output_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Return the cached application config."""
    cfg = Config()  # type: ignore[call-arg]
    cfg.ensure_dirs()
    return cfg
