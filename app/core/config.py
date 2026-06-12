"""
NOTES:
1. Pydantic V2 Shift: We are using SettingsConfigDict instead of the old class Config subclass for environment parsing. This is the modern, highly-performant standard in Pydantic V2.
2. Security Protocol: The extra="ignore" flag ensures that if our production server has extra environment variables injected by Docker or Caddy, the app won't crash on boot.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Core Application Variables
    PROJECT_NAME: str = "CrewSignal"
    API_V1_STR: str = "/api/v1"
    
    # Security & Authentication
    SECRET_KEY: str = "local-dev-secret-key-change-in-prod"
    
    # Twilio Integration (Default mock strings for local development)
    TWILIO_ACCOUNT_SID: str = "mock_sid"
    TWILIO_AUTH_TOKEN: str = "mock_token"
    TWILIO_FROM_NUMBER: str = "+12345678900"

    # Pydantic V2 Configuration for reading the .env file safely
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()