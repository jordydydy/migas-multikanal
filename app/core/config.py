import os
from typing import Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    
    # App Settings
    APP_NAME: str = "Multikarnal Orchestrator"
    LOG_LEVEL: str = "INFO"
    ENABLE_BACKGROUND_WORKER: bool = True 
    X_API_KEY: Optional[str] = None

    # Dify API Configuration
    DIFY_API_BASE_URL: str
    DIFY_API_KEY: str
    
    # Feature Flags
    EMAIL_POLL_INTERVAL_SECONDS: int = 15
    MAX_INPUT_CHARS: int = 6000

    # Social Media Credentials
    INSTAGRAM_PAGE_ACCESS_TOKEN: Optional[str] = None
    INSTAGRAM_CHATBOT_ID: Optional[str] = None
    INSTAGRAM_VERIFY_TOKEN: Optional[str] = None

    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_VERIFY_TOKEN: Optional[str] = None

    # Email Settings
    EMAIL_PROVIDER: Literal["gmail", "azure_oauth2", "unknown"] = "unknown"
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USER: Optional[str] = None
    EMAIL_PASS: Optional[str] = None
    
    # Azure OAuth2
    AZURE_CLIENT_ID: Optional[str] = None
    AZURE_CLIENT_SECRET: Optional[str] = None
    AZURE_TENANT_ID: Optional[str] = None
    AZURE_EMAIL_USER: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

settings = Settings()