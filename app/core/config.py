"""
NOTES:
1. This file is the settings panel for the whole app. Instead of hardcoding things like
   phone numbers and passwords directly in the code, we store them here and read them
   from a .env file. That way we can change settings without touching any code.
2. extra="ignore" means if the server has extra environment variables we didn't ask for
   (like ones Docker or Caddy add automatically), the app just ignores them and keeps
   running instead of crashing.
3. USE_MOCK_SMS defaults to True so the app always uses the fake SMS sender during
   development and tests. Flip it to False in your production .env once you have real
   Twilio credentials set up.
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

    # Set False only in production with real Twilio credentials; always True in tests
    USE_MOCK_SMS: bool = True

    # Pydantic V2 Configuration for reading the .env file safely
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()