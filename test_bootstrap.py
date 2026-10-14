#!/usr/bin/env python3
import sys
import os

# Add the backend directory to the path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.core.security import get_password_hash
from app.models.models import User, UserRole, UserStatus

def test_bootstrap(email: str, password: str):
    """Test bootstrap process with given credentials."""
    if not email or not password:
        raise RuntimeError("ADMIN_EMAIL and ADMIN_PASSWORD must be supplied to bootstrap the administrator")
    if len(password) < 12 or len(password.encode("utf-8")) > 72:
        raise RuntimeError("ADMIN_PASSWORD must be between 12 characters and 72 UTF-8 bytes")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
        print(f"Found {len(admins)} existing admins")
        if len(admins) > 1:
            raise RuntimeError("More than one administrator exists; stop and repair the database before deployment")
        if admins:
            configured_email = email.strip().lower()
            if admins[0].email != configured_email:
                raise RuntimeError(f"ADMIN_EMAIL does not match the existing administrator account: {admins[0].email}")
            print(f"Using existing admin: {admins[0].email}")
            return admins[0]

        print(f"Creating new admin with email: {email}")
        admin = User(
            email=email.strip().lower(),
            hashed_password=get_password_hash(password),
            role=UserRole.ADMIN,
            full_name="Platform Administrator",
            status=UserStatus.ACTIVE,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"Created admin with ID: {admin.id}")
        return admin
    finally:
        db.close()

if __name__ == "__main__":
    # Test with a different email first
    try:
        print("Testing with test@example.com...")
        admin = test_bootstrap("test@example.com", "TestPassword123")  # 18 chars
        print("SUCCESS: Test bootstrap worked")
    except Exception as e:
        print(f"ERROR with test email: {e}")

    print("\n" + "="*50 + "\n")

    # Now test with the target email
    try:
        print("Testing with amritkis2006@gmail.com...")
        admin = test_bootstrap("amritkis2006@gmail.com", "Priyu@2005Sec")  # 12 chars
        print("SUCCESS: Target email bootstrap worked")
    except Exception as e:
        print(f"ERROR with target email: {e}")