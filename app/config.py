from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List

class Settings(BaseSettings):
    # Basic environment settings
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    HOST: str = Field("0.0.0.0", env="HOST")
    PORT: int = Field(8000, env="PORT")
    
    # CORS settings: Allowed origins should be provided as a comma-separated list in the env var.
    ALLOWED_ORIGINS: List[str] = Field(default=["http://localhost", "http://127.0.0.1"], env="ALLOWED_ORIGINS")

    # Logging configuration
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FILE_PATH: str = Field("logs/app.log", env="LOG_FILE_PATH")
    
    # Email service settings
    SENDGRID_API_KEY: str = Field(..., env="SENDGRID_API_KEY")
    FROM_EMAIL: str = Field(..., env="FROM_EMAIL")
    
    # Workflow and job processing settings
    MAX_CORRECTION_ATTEMPTS: int = Field(3, env="MAX_CORRECTION_ATTEMPTS")
    EXECUTION_TIMEOUT: int = Field(180, env="EXECUTION_TIMEOUT")
    ERROR_CACHE_TTL: int = Field(3600, env="ERROR_CACHE_TTL")
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    def assemble_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

# Create a single instance of the settings that can be imported anywhere in the project.
settings = Settings() 