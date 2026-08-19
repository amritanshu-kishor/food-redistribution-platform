from fastapi import FastAPI, Depends, status, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.api import auth, donations, allocations, admin, notifications, qr, users

# Run table creation for direct, out-of-the-box local startup
# In production, Alembic handles migrations, but this ensures instant local execution
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="Backend API for the Food Redistribution Platform connecting Restaurant donors and NGOs."
)

# CORS Setup
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Mount local uploads directory if STORAGE_PROVIDER is local
if settings.STORAGE_PROVIDER == "local":
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection failure: {str(e)}"
        )

# Register Feature Routes
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users Profile"])
app.include_router(donations.router, prefix=f"{settings.API_V1_STR}/donations", tags=["Donations"])
app.include_router(allocations.router, prefix=f"{settings.API_V1_STR}/allocations", tags=["Allocations"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["Administrative Portal"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_STR}/notifications", tags=["In-App Notifications"])
app.include_router(qr.router, prefix=f"{settings.API_V1_STR}/qr", tags=["QR Scanning Verification"])
