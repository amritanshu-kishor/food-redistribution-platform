#!/usr/bin/env python3
import sys
import os

# Add the backend directory to the path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.models.models import User, UserRole

def debug_bootstrap():
    """Debug what the bootstrap script sees."""
    print(f"DATABASE_URL: {settings.DATABASE_URL}")
    print(f"ADMIN_EMAIL: {settings.ADMIN_EMAIL}")
    print(f"ADMIN_PASSWORD set: {bool(settings.ADMIN_PASSWORD)}")

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Query for admins
        admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
        print(f"Found {len(admins)} admins via query")

        for i, admin in enumerate(admins):
            print(f"  Admin {i+1}:")
            print(f"    ID: {admin.id}")
            print(f"    Email: '{admin.email}'")
            print(f"    Role: {admin.role}")
            print(f"    Status: {admin.status}")

        # Also try a raw query to see what's in the users table
        from sqlalchemy import text
        result = db.execute(text("SELECT id, email, role, status FROM users"))
        rows = result.fetchall()
        print(f"\nRaw query found {len(rows)} users in users table:")
        for row in rows:
            print(f"  ID: {row[0]}, Email: '{row[1]}', Role: '{row[2]}', Status: '{row[3]}'")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_bootstrap()