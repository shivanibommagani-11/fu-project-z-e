"""
Application configuration management using Pydantic Settings.
Loads from environment variables or .env file.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration with environment variable overrides."""

    # LiteLLM Configuration
    litellm_jwt_token: str
    litellm_gateway_url: str = "https://vz-ai-gateway-gke-test-east.ebiz.verizon.com/v1"
    litellm_model: str = "gemini-2.5-flash"
    litellm_temperature: float = 0.7
    litellm_max_tokens: int = 2048

    # Database Configuration
    db_url: str = "oracle+oracledb://NETSITES_APP:<url_encoded_password>@txslofuzedd1v.nss.vzwnet.com:1521/?service_name=fuzedev.nss.vzwnet.com"

    # Logging Configuration
    log_level: str = "INFO"

    # API Configuration
    api_title: str = "Fuze Real Estate Agentic Service"
    api_version: str = "1.0.0"
    api_debug: bool = False
    api_port: int = 8000

    # Agent Configuration
    agent_temperature: float = 0.7
    agent_max_retries: int = 3
    agent_timeout: int = 300  # seconds

    # Validation Configuration
    csv_max_rows: int = 10000
    csv_max_file_size: int = 50 * 1024 * 1024  # 50 MB

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()  # type: ignore
