#!/usr/bin/env python3
import sys
import os

# Add the backend directory to the path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.models import User, UserRole, UserStatus

def make_user_admin(email: str, password: str, full_name: str = "Platform Administrator"):
    """Make an existing user an admin with the given password."""
    db = SessionLocal()
    try:
        # Find the user by email
        user = db.query(User).filter(User.email == email.strip().lower()).first()
        if not user:
            print(f"Error: No user found with email {email}")
            return False

        # Check if password meets requirements
        if len(password) < 12 or len(password.encode("utf-8")) > 72:
            print(f"Error: Password must be between 12 and 72 UTF-8 bytes")
            return False

        # Update the user to be an admin
        user.email = email.strip().lower()
        user.hashed_password = get_password_hash(password)
        user.role = UserRole.ADMIN
        user.full_name = full_name
        user.status = UserStatus.ACTIVE

        db.commit()
        db.refresh(user)

        print(f"Successfully made user {email} an admin")
        print(f"User ID: {user.id}")
        print(f"Role: {user.role}")
        print(f"Status: {user.status}")
        return True

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    # Use the credentials specified by the user
    EMAIL = "amritkis2006@gmail.com"
    PASSWORD = "Priyu@2005Sec"  # 12 characters to meet requirements
    FULL_NAME = "Platform Administrator"

    success = make_user_admin(EMAIL, PASSWORD, FULL_NAME)
    sys.exit(0 if success else 1)