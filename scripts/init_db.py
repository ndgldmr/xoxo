#!/usr/bin/env python3
"""Initialize the database by creating all tables."""
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import init_db


def main():
    """Initialize database tables."""
    print("Initializing database...")
    try:
        init_db()
        print("✓ Database initialized successfully!")
        print("  Tables created: students")
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
