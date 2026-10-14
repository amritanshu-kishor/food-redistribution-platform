import secrets
from pathlib import Path
from typing import List, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    PROJECT_NAME: str = "Food Redistribution Platform"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str = "sqlite:///./food_redist.db"
    
    # JWT Settings
    JWT_SECRET_KEY: str = ""
    JWT_REFRESH_SECRET_KEY: str = ""
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS Configuration
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://localhost:3000"
    FRONTEND_URL: str = "http://localhost:5173"

    # Secure administrator bootstrap. These values are only consumed by the
    # server-side bootstrap command and are never returned by the API.
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip().rstrip("/") for i in v.split(",") if i.strip()]
        return [i.strip().rstrip("/") for i in v if i.strip()]
    
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
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_LOGIN_MAX_REQUESTS: int = 10
    RATE_LIMIT_REGISTER_MAX_REQUESTS: int = 5
    RATE_LIMIT_UPLOAD_MAX_REQUESTS: int = 20
    RATE_LIMIT_QR_MAX_REQUESTS: int = 30

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "case_sensitive": True,
        "extra": "ignore"
    }

    @model_validator(mode="after")
    def validate_runtime_configuration(self):
        """Reject unsafe production defaults while keeping local startup easy."""
        self.ENV = self.ENV.lower()
        if self.ENV in {"production", "staging"} and (not self.JWT_SECRET_KEY or not self.JWT_REFRESH_SECRET_KEY):
            raise ValueError("Production requires configured JWT secrets")
        if not self.JWT_SECRET_KEY:
            self.JWT_SECRET_KEY = secrets.token_urlsafe(32)
        if not self.JWT_REFRESH_SECRET_KEY:
            self.JWT_REFRESH_SECRET_KEY = secrets.token_urlsafe(32)

        if self.ENV.lower() in {"production", "staging"}:
            if len(self.JWT_SECRET_KEY) < 32 or len(self.JWT_REFRESH_SECRET_KEY) < 32:
                raise ValueError("JWT secrets must each be at least 32 characters in production")
            if self.JWT_SECRET_KEY == self.JWT_REFRESH_SECRET_KEY or "supersecret" in self.JWT_SECRET_KEY.lower() or "supersecret" in self.JWT_REFRESH_SECRET_KEY.lower():
                raise ValueError("JWT secrets must be distinct, randomly generated values")
            if not self.CORS_ORIGINS:
                raise ValueError("CORS_ORIGINS must contain an explicit frontend origin in production")
            if "*" in self.CORS_ORIGINS:
                raise ValueError("Wildcard CORS origins are not allowed in production")
            if self.STORAGE_PROVIDER not in {"local", "s3"}:
                raise ValueError("STORAGE_PROVIDER must be 'local' or 's3'")
            if self.STORAGE_PROVIDER == "s3" and not all(
                [self.AWS_S3_BUCKET_NAME, self.AWS_REGION]
            ):
                raise ValueError("S3 storage requires AWS_S3_BUCKET_NAME and AWS_REGION")
        return self

settings = Settings()
