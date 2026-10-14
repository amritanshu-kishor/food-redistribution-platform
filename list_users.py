#!/usr/bin/env python3
import sys
import os

# Add the backend directory to the path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.database import SessionLocal
from app.models.models import User

def list_all_users():
    """List all users in the database."""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"Found {len(users)} users:")
        for user in users:
            print(f"  ID: {user.id}")
            print(f"  Email: '{user.email}'")
            print(f"  Role: {user.role}")
            print(f"  Status: {user.status}")
            print(f"  Full Name: {user.full_name}")
            print("---")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    list_all_users()