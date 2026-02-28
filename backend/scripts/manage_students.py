#!/usr/bin/env python3
"""CLI tool for managing students in the database."""
import sys
from pathlib import Path
from typing import Optional

import click

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import get_session
from app.repositories.student import StudentRepository


@click.group()
def cli():
    """Student management CLI for XOXO Word of the Day."""
    pass


@cli.command()
@click.option("--phone", required=True, help="Phone number in E.164 format (e.g., +5511999999999)")
@click.option("--first-name", help="Student's first name")
@click.option("--last-name", help="Student's last name")
@click.option(
    "--level",
    type=click.Choice(["beginner", "intermediate"]),
    default="beginner",
    help="English proficiency level",
)
@click.option(
    "--whatsapp/--no-whatsapp",
    default=True,
    help="Whether to send WhatsApp messages",
)
def add_student(
    phone: str,
    first_name: Optional[str],
    last_name: Optional[str],
    level: str,
    whatsapp: bool,
):
    """Add a new student to the database."""
    try:
        with get_session() as session:
            repo = StudentRepository(session)

            # Check if student already exists
            existing = repo.get_by_phone(phone)
            if existing:
                click.echo(f"✗ Student with phone {phone} already exists!")
                sys.exit(1)

            # Create student
            student = repo.create(
                phone_number=phone,
                first_name=first_name,
                last_name=last_name,
                english_level=level,
                whatsapp_messages=whatsapp,
            )

            name = f"{first_name or ''} {last_name or ''}".strip() or "N/A"
            click.echo(f"✓ Student added successfully!")
            click.echo(f"  Phone: {student.phone_number}")
            click.echo(f"  Name: {name}")
            click.echo(f"  Level: {student.english_level}")
            click.echo(f"  WhatsApp: {'Yes' if student.whatsapp_messages else 'No'}")

    except Exception as e:
        click.echo(f"✗ Error adding student: {e}")
        sys.exit(1)


@cli.command()
@click.option("--include-inactive", is_flag=True, help="Include inactive students")
@click.option(
    "--level",
    type=click.Choice(["beginner", "intermediate"]),
    help="Filter by English level",
)
def list_students(include_inactive: bool, level: Optional[str]):
    """List all students in the database."""
    try:
        with get_session() as session:
            repo = StudentRepository(session)
            students = repo.list_all(include_inactive=include_inactive)

            if level:
                students = [s for s in students if s.english_level == level]

            if not students:
                click.echo("No students found.")
                return

            click.echo(f"\nFound {len(students)} student(s):\n")
            click.echo(f"{'Phone':<20} {'Name':<30} {'Level':<15} {'WhatsApp':<10} {'Active':<10}")
            click.echo("-" * 90)

            for student in students:
                name = f"{student.first_name or ''} {student.last_name or ''}".strip() or "N/A"
                whatsapp_status = "Yes" if student.whatsapp_messages else "No"
                active_status = "Yes" if student.is_active else "No"

                click.echo(
                    f"{student.phone_number:<20} {name:<30} {student.english_level:<15} "
                    f"{whatsapp_status:<10} {active_status:<10}"
                )

    except Exception as e:
        click.echo(f"✗ Error listing students: {e}")
        sys.exit(1)


@cli.command()
@click.option("--phone", required=True, help="Phone number of the student to remove")
def remove_student(phone: str):
    """Remove (deactivate) a student from the database."""
    try:
        with get_session() as session:
            repo = StudentRepository(session)

            # Check if student exists
            student = repo.get_by_phone(phone)
            if not student:
                click.echo(f"✗ Student with phone {phone} not found!")
                sys.exit(1)

            # Confirm deletion
            name = f"{student.first_name or ''} {student.last_name or ''}".strip() or "Unknown"
            if click.confirm(f"Are you sure you want to deactivate {name} ({phone})?"):
                repo.deactivate(phone)
                click.echo(f"✓ Student {phone} deactivated successfully!")
            else:
                click.echo("Cancelled.")

    except Exception as e:
        click.echo(f"✗ Error removing student: {e}")
        sys.exit(1)


@cli.command()
@click.option("--phone", required=True, help="Phone number of the student")
def opt_out(phone: str):
    """Opt out a student from WhatsApp messages."""
    try:
        with get_session() as session:
            repo = StudentRepository(session)

            if repo.update_whatsapp_opt_out(phone):
                click.echo(f"✓ Student {phone} opted out of WhatsApp messages.")
            else:
                click.echo(f"✗ Student with phone {phone} not found!")
                sys.exit(1)

    except Exception as e:
        click.echo(f"✗ Error opting out student: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
