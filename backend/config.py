# backend/config.py
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import List

load_dotenv()

class Settings(BaseSettings):
    # API Keys
    deepgram_api_key: str = ""
    gemini_api_key: str = ""
    elevenlabs_api_key: str = ""
    
    # Database
    mongodb_url: str = ""
    database_name: str = "doctalk_ai"
    
    # JWT Settings
    jwt_secret_key: str = "your-super-secret-jwt-key-change-this-in-production"
    
    # Server Configuration
    host: str = "localhost"
    port: int = 8000
    debug: bool = True
    
    # CORS Settings
    allowed_origins: str = "http://localhost:3000"
    
    # Voice Settings
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    deepgram_model: str = "nova-2"
    
    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    def validate_api_keys(self) -> None:
        """Validate that required API keys are present"""
        missing_keys = []
        
        if not self.deepgram_api_key:
            missing_keys.append("DEEPGRAM_API_KEY")
        if not self.gemini_api_key:
            missing_keys.append("GEMINI_API_KEY")
        if not self.elevenlabs_api_key:
            missing_keys.append("ELEVENLABS_API_KEY")
        
        if missing_keys:
            raise ValueError(f"Missing required API keys: {', '.join(missing_keys)}")
    
    class Config:
        env_file = ".env"

settings = Settings()