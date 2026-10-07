"""
Seed the initial Admin account for SmartCare.

This script:
  1. Ensures all tables exist (calls db.create_all() - safe/no-op if the
     schema was already created via scripts/schema.sql).
  2. Creates the seed admin user using credentials from .env
     (ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_EMAIL), or sensible defaults.
  3. Is idempotent - running it again will NOT create a duplicate admin.

Usage:
    python scripts/seed_admin.py
"""

import os
import sys

# Allow running this script directly from the scripts/ folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from app.models import User


def main():
    app = create_app(os.environ.get("FLASK_ENV", "development"))

    with app.app_context():
        # Create any tables that don't exist yet (harmless if schema.sql was
        # already applied - SQLAlchemy only creates missing tables).
        db.create_all()
        print("[OK] Database tables verified/created.")

        username = app.config["ADMIN_USERNAME"]
        password = app.config["ADMIN_PASSWORD"]
        email = app.config["ADMIN_EMAIL"]

        existing = User.query.filter_by(username=username).first()
        if existing:
            print(f"[SKIP] Admin user '{username}' already exists (id={existing.id}). "
                  f"Nothing to do.")
            return

        admin = User(
            username='admin',
            full_name="System Administrator",
            email=email,
            role="admin",
            is_active=True,
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()

        print("=" * 60)
        print("[OK] Seed admin account created successfully!")
        print(f"     Username: {username}")
        print(f"     Password: {password}")
        print("     (Change this password after first login in production.)")
        print("=" * 60)


if __name__ == "__main__":
    main()
