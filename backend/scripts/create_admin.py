"""Create (or promote) an administrator account. Admins cannot self-register via the API.

    python scripts/create_admin.py --email you@example.com --name "Your Name"
The password is read interactively (or from ADMIN_PASSWORD) and never stored in plain text.
"""
import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.models.enums import UserRole  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--email", required=True)
ap.add_argument("--name", default="Administrator")
args = ap.parse_args()
password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Password (min 8 chars, letters+digits): ")
if len(password) < 8:
    sys.exit("Password too short")

with SessionLocal() as db:
    user = db.execute(select(User).where(User.email == args.email.lower())).scalar_one_or_none()
    if user is None:
        user = User(name=args.name, email=args.email.lower())
        db.add(user)
    user.role = UserRole.admin
    user.password_hash = hash_password(password)
    db.commit()
    print(f"Administrator ready: {user.email}")
