import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Food Redistribution Platform"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/food_redistribution"
    
    # JWT Settings
    JWT_SECRET_KEY: str = "supersecretkeychangeinproduction12345!"
    JWT_REFRESH_SECRET_KEY: str = "supersecretrefreshkeychangeinproduction67890!"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS Configuration
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://localhost:3000"
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip().rstrip("/") for i in v.split(",") if i.strip()]
        return v
    
    # File Storage
    STORAGE_PROVIDER: str = "local"  # "local" or "s3"
    UPLOAD_DIR: str = "./uploads"
    
    # AWS Settings (Production storage)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET_NAME: str = ""
    AWS_REGION: str = "us-east-1"
    
    # Email Settings
    EMAIL_PROVIDER: str = "console"  # "console" or "smtp"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "no-reply@foodredistribution.org"
    
    # Maps Configuration
    MAPBOX_ACCESS_TOKEN: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    
    ENV: str = "development"
    
    model_config = {
        "env_file": "../.env",  # Check in parent directory
        "case_sensitive": True,
        "extra": "ignore"
    }

settings = Settings()
