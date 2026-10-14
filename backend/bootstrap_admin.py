"""Create the one administrator account from deployment secrets.

Run from the repository root or backend directory with ADMIN_EMAIL and
ADMIN_PASSWORD supplied through the environment. The command is idempotent:
it never creates a second administrator and never resets an existing password.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import Base, engine, SessionLocal
from app.core.security import get_password_hash
from app.core.config import settings
from app.models.models import User, UserRole, UserStatus


def bootstrap_admin() -> User:
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        raise RuntimeError("ADMIN_EMAIL and ADMIN_PASSWORD must be supplied to bootstrap the administrator")
    if len(settings.ADMIN_PASSWORD) < 12 or len(settings.ADMIN_PASSWORD.encode("utf-8")) > 72:
        raise RuntimeError("ADMIN_PASSWORD must be between 12 characters and 72 UTF-8 bytes")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
        if len(admins) > 1:
            raise RuntimeError("More than one administrator exists; stop and repair the database before deployment")
        if admins:
            configured_email = settings.ADMIN_EMAIL.strip().lower()
            if admins[0].email != configured_email:
                raise RuntimeError("ADMIN_EMAIL does not match the existing administrator account")
            return admins[0]

        admin = User(
            email=settings.ADMIN_EMAIL.strip().lower(),
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
            role=UserRole.ADMIN,
            full_name="Platform Administrator",
            status=UserStatus.ACTIVE,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin
    finally:
        db.close()


if __name__ == "__main__":
    administrator = bootstrap_admin()
    print(f"Administrator ready: {administrator.email}")
