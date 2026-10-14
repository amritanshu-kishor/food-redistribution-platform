#!/usr/bin/env python3
import sys
import os

# Add the backend directory to the path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.models import User, UserRole, UserStatus

def update_admin_email_and_password(new_email: str, new_password: str, full_name: str = "Platform Administrator"):
    """Update the existing admin's email and password."""
    db = SessionLocal()
    try:
        # Find the existing admin (should be exactly one)
        admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
        if not admins:
            print("Error: No admin found")
            return False
        if len(admins) > 1:
            print(f"Error: Found {len(admins)} admins, expected exactly one")
            return False

        admin = admins[0]
        print(f"Found existing admin:")
        print(f"  ID: {admin.id}")
        print(f"  Current Email: {admin.email}")
        print(f"  Current Role: {admin.role}")
        print(f"  Current Status: {admin.status}")
        print(f"  Current Full Name: {admin.full_name}")

        # Validate password length
        if len(new_password) < 12 or len(new_password.encode("utf-8")) > 72:
            print(f"Error: Password must be between 12 and 72 UTF-8 bytes")
            return False

        # Update the admin
        old_email = admin.email
        admin.email = new_email.strip().lower()
        admin.hashed_password = get_password_hash(new_password)
        admin.full_name = full_name
        # Role and status should already be correct, but set explicitly
        admin.role = UserRole.ADMIN
        admin.status = UserStatus.ACTIVE

        db.commit()
        db.refresh(admin)

        print(f"\nSuccessfully updated admin:")
        print(f"  ID: {admin.id}")
        print(f"  Email: {old_email} → {admin.email}")
        print(f"  Role: {admin.role}")
        print(f"  Status: {admin.status}")
        print(f"  Full Name: {admin.full_name}")
        return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    # Use the credentials specified by the user
    NEW_EMAIL = "amritkis2006@gmail.com"
    NEW_PASSWORD = "Priyu@2005Sec"  # 12 characters to meet requirements
    FULL_NAME = "Platform Administrator"

    success = update_admin_email_and_password(NEW_EMAIL, NEW_PASSWORD, FULL_NAME)
    sys.exit(0 if success else 1)