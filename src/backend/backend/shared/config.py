from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os

class Settings(BaseSettings):
    """
    Centralized configuration management using Pydantic Settings.
    Reads from environment variables or .env file.
    """
    # Security
    sisrua_auth_token: Optional[str] = Field(None, validation_alias="SISRUA_AUTH_TOKEN")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.sisrua_auth_token:
            import uuid
            self.sisrua_auth_token = uuid.uuid4().hex
            # Inject back to os.environ for child processes/legacy modules if needed
            os.environ["SISRUA_AUTH_TOKEN"] = self.sisrua_auth_token
    
    # External APIs
    groq_api_key: Optional[str] = Field(None, validation_alias="GROQ_API_KEY")
    opentopography_api_key: Optional[str] = Field(None, validation_alias="OPENTOPOGRAPHY_API_KEY")
    
    # Infrastructure
    environment: str = Field("dev", validation_alias="ENVIRONMENT")
    sentry_dsn: Optional[str] = Field(None, validation_alias="SENTRY_DSN")
    
    # CORS: comma-separated extra origins (Cloud Run, staging, etc.)
    # Example: "https://sisrua.app,https://staging.sisrua.app"
    sisrua_cors_origins: str = Field("", validation_alias="SISRUA_CORS_ORIGINS")

    @property
    def extra_cors_origins(self) -> List[str]:
        """Parse SISRUA_CORS_ORIGINS into a list of origin strings."""
        if not self.sisrua_cors_origins:
            return []
        return [o.strip() for o in self.sisrua_cors_origins.split(",") if o.strip()]

    # Paths (OS dependent)
    localappdata: str = Field(os.environ.get("LOCALAPPDATA", "."), validation_alias="LOCALAPPDATA")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

config = Settings()
