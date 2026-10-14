"""Tests must never load the developer's deployment database or email secrets."""
import os
import secrets

os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = secrets.token_urlsafe(48)
os.environ["JWT_REFRESH_SECRET_KEY"] = secrets.token_urlsafe(48)
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["FRONTEND_URL"] = "http://localhost:5173"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["EMAIL_PROVIDER"] = "console"
os.environ["STORAGE_PROVIDER"] = "local"
