#!/usr/bin/env python3
"""
Script to create the first admin user for XOXO Education backend.

Usage:
    python scripts/create_admin.py

Or with Docker:
    docker compose exec app python scripts/create_admin.py
"""

import asyncio
import sys
from getpass import getpass

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Add parent directory to path to import app modules
sys.path.insert(0, '/app')  # For Docker
sys.path.insert(0, '.')     # For local

from app.core.config import settings
from app.core.security import hash_password, validate_password_strength
from app.models.user import User
from app.repositories.user import UserRepository


async def create_admin():
    """Create the first admin user interactively."""
    print("=" * 60)
    print("XOXO Education - Create Admin User")
    print("=" * 60)
    print()

    # Get user input
    email = input("Admin email: ").strip()
    if not email:
        print("Error: Email is required")
        return

    first_name = input("First name: ").strip()
    if not first_name:
        print("Error: First name is required")
        return

    last_name = input("Last name: ").strip()
    if not last_name:
        print("Error: Last name is required")
        return

    phone = input("Phone (optional): ").strip() or None

    print()
    print("Password requirements:")
    print("  - Minimum 12 characters")
    print("  - At least one uppercase letter")
    print("  - At least one lowercase letter")
    print("  - At least one digit")
    print("  - At least one special character (@$!%*?&)")
    print()

    while True:
        password = getpass("Password: ")
        password_confirm = getpass("Confirm password: ")

        if password != password_confirm:
            print("Error: Passwords do not match. Please try again.")
            continue

        is_valid, error = validate_password_strength(password)
        if not is_valid:
            print(f"Error: {error}")
            print("Please try again.")
            continue

        break

    # Create database connection
    engine = create_async_engine(
        str(settings.DATABASE_URL),
        echo=False
    )

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        # Check if email already exists
        user_repo = UserRepository(session)
        existing_user = await user_repo.get_by_email(email)

        if existing_user:
            print(f"\nError: User with email '{email}' already exists!")
            await engine.dispose()
            return

        # Create admin user
        admin = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            hashed_password=hash_password(password),
            is_active=True,
            is_admin=True
        )

        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        print()
        print("=" * 60)
        print("✓ Admin user created successfully!")
        print("=" * 60)
        print(f"ID:         {admin.id}")
        print(f"Email:      {admin.email}")
        print(f"Name:       {admin.full_name}")
        print(f"Phone:      {admin.phone or 'N/A'}")
        print(f"Is Active:  {admin.is_active}")
        print(f"Is Admin:   {admin.is_admin}")
        print(f"Created:    {admin.created_at}")
        print("=" * 60)
        print()
        print("You can now login at: POST /api/v1/auth/login")
        print()

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(create_admin())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
