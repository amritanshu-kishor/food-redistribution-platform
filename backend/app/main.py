import logging
import os
from fastapi import FastAPI, Depends, status, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.api import auth, donations, allocations, admin, notifications, qr, users
from app.core.rate_limit import RateLimitMiddleware

logger = logging.getLogger("foodshare")

# Run table creation for direct, out-of-the-box local startup
# In production, Alembic handles migrations, but this ensures instant local execution
if settings.ENV.lower() not in {"production", "staging"}:
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=None if settings.ENV.lower() == "production" else f"{settings.API_V1_STR}/openapi.json",
    docs_url=None if settings.ENV.lower() == "production" else "/docs",
    redoc_url=None if settings.ENV.lower() == "production" else "/redoc",
    description="Backend API for the Food Redistribution Platform connecting Restaurant donors and NGOs."
)

app.add_middleware(RateLimitMiddleware)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(self), geolocation=(self), microphone=()")
    csp = "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'"
    if settings.ENV.lower() not in {"production", "staging"}:
        csp += "; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'"
    response.headers.setdefault("Content-Security-Policy", csp)
    if settings.ENV.lower() in {"production", "staging"}:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

@app.exception_handler(RequestValidationError)
async def request_validation_error(_request: Request, exc: RequestValidationError):
    # Keep field-level validation useful without exposing server internals.
    safe_errors = []
    for error in exc.errors():
        safe_error = {
            key: value for key, value in error.items()
            if key not in {"ctx", "input"}
        }
        safe_error["msg"] = str(error.get("msg", "Invalid input"))
        safe_errors.append(safe_error)
    return JSONResponse(status_code=422, content={"detail": safe_errors})

@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    logger.exception("Unhandled server error for %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred."})

# CORS Setup
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
         allow_origins=settings.CORS_ORIGINS,
         allow_credentials=False,
         allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
         allow_headers=["Authorization", "Content-Type", "Accept"],
    )

# Mount local uploads directory if STORAGE_PROVIDER is local
if settings.STORAGE_PROVIDER == "local":
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "images"), exist_ok=True)
    # Verification documents are private and are served through an authorized
    # endpoint rather than a guessable public static path.
    app.mount("/uploads/images", StaticFiles(directory=os.path.join(settings.UPLOAD_DIR, "images")), name="public-images")

# Root redirect to API docs
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

# Core Health Check Endpoint
@app.get("/health", status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint validating server run state and DB persistence connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "environment": settings.ENV
        }
    except Exception:
        logger.exception("Health check database failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection failure"
        )

# Register Feature Routes
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users Profile"])
app.include_router(donations.router, prefix=f"{settings.API_V1_STR}/donations", tags=["Donations"])
app.include_router(allocations.router, prefix=f"{settings.API_V1_STR}/allocations", tags=["Allocations"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["Administrative Portal"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_STR}/notifications", tags=["In-App Notifications"])
app.include_router(qr.router, prefix=f"{settings.API_V1_STR}/qr", tags=["QR Scanning Verification"])
