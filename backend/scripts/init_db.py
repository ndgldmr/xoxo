"""
Database initialization script.
Creates initial database schema and optionally seeds data.
"""

import asyncio

from app.db.base import Base
from app.db.session import async_engine


async def init_db() -> None:
    """Initialize database by creating all tables."""
    print("Creating database tables...")

    async with async_engine.begin() as conn:
        # Drop all tables (use with caution!)
        # await conn.run_sync(Base.metadata.drop_all)

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    print("Database tables created successfully!")


async def seed_data() -> None:
    """Seed initial data (optional)."""
    from app.schemas.user import UserCreate
    from app.services.user import UserService
    from app.db.session import async_session_maker

    print("Seeding initial data...")

    async with async_session_maker() as session:
        service = UserService(session)

        # Create sample users
        sample_users = [
            UserCreate(
                email="admin@xoxo.com",
                first_name="Admin",
                last_name="User",
                phone="+1234567890",
                is_active=True,
            ),
            UserCreate(
                email="volunteer@xoxo.com",
                first_name="Volunteer",
                last_name="Coordinator",
                phone="+1234567891",
                is_active=True,
            ),
        ]

        for user_data in sample_users:
            try:
                user = await service.create_user(user_data)
                print(f"Created user: {user.email}")
            except Exception as e:
                print(f"User {user_data.email} already exists or error: {e}")

    print("Data seeding completed!")


async def main() -> None:
    """Main function."""
    await init_db()
    # Uncomment to seed data:
    # await seed_data()


if __name__ == "__main__":
    asyncio.run(main())
