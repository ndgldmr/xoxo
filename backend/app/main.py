"""Main entry point with CLI and API server support."""
import sys
import argparse
from app.config import get_settings
from app.integrations.llm_client import LLMClient
from app.integrations.wasender_client import WaSenderClient
from app.logging.audit_log import AuditLog
from app.services.word_of_day_service import WordOfDayService


def get_service() -> WordOfDayService:
    """Create and return a WordOfDayService instance with dependencies."""
    settings = get_settings()

    llm_client = LLMClient(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout,
    )

    whatsapp_client = WaSenderClient(
        api_key=settings.wasender_api_key,
        dry_run=settings.dry_run,
    )

    audit_log = AuditLog(log_path=settings.audit_log_path)

    # Determine if using database mode
    db_session = None
    if settings.database_url:
        from app.db.session import _get_session_factory
        # Create a session directly for CLI usage
        SessionLocal = _get_session_factory()
        db_session = SessionLocal()

    return WordOfDayService(
        llm_client=llm_client,
        whatsapp_client=whatsapp_client,
        audit_log=audit_log,
        db_session=db_session,
        send_delay=settings.send_delay_seconds,
    )


def cmd_send(args):
    """Send command handler."""
    service = get_service()

    try:
        result = service.run_daily_job(
            theme=args.theme,
            level=args.level,
            force=args.force,
        )
    finally:
        # Close database session if it exists
        if service.db_session:
            service.db_session.commit()
            service.db_session.close()

    print("\n" + "=" * 60)
    print("SEND RESULT")
    print("=" * 60)
    print(f"Status: {result['status']}")

    # Handle both old and new response formats
    if 'sent_count' in result:
        # Multi-recipient mode
        print(f"Sent: {result['sent_count']}/{result['total_recipients']}")
        print(f"Failed: {result['failed_count']}")
    else:
        # Single-recipient mode (backward compatibility)
        print(f"Sent: {result.get('sent', False)}")

    print(f"Date: {result['date']}")
    print(f"Used Fallback: {result['used_fallback']}")

    if result.get('provider_message_id'):
        print(f"Provider Message ID: {result['provider_message_id']}")

    if result['validation_errors']:
        print(f"\nValidation Errors:")
        for error in result['validation_errors']:
            print(f"  - {error}")

    if result.get('preview'):
        print(f"\nPreview:")
        print(result['preview'])

    # Show individual send results if multi-recipient mode
    if 'sends' in result and isinstance(result['sends'], list):
        print(f"\nIndividual Sends:")
        for send in result['sends']:
            status = "✓" if send['sent'] else "✗"
            name = send.get('first_name', 'Unknown')
            phone = send['phone_number']
            print(f"  {status} {name} ({phone})")
            if send.get('error_message'):
                print(f"    Error: {send['error_message']}")

    print("=" * 60 + "\n")

    # Success if any messages sent
    sent_count = result.get('sent_count', 0 if not result.get('sent') else 1)
    return 0 if sent_count > 0 else 1


def cmd_health(args):
    """Health check command handler."""
    settings = get_settings()

    print("\n" + "=" * 60)
    print("HEALTH CHECK")
    print("=" * 60)

    # Check LLM configuration
    llm_ok = bool(settings.llm_api_key)
    print(f"LLM API Key: {'✓ Configured' if llm_ok else '✗ Missing'}")
    print(f"LLM Model: {settings.llm_model}")
    print(f"LLM Base URL: {settings.llm_base_url}")

    # Check WaSenderAPI configuration
    wasender_ok = bool(settings.wasender_api_key)
    print(f"\nWaSenderAPI: {'✓ Configured' if wasender_ok else '✗ Missing (WASENDER_API_KEY)'}")

    # Check recipient configuration
    print(f"\nRecipient Configuration:")
    if settings.database_url:
        print(f"  Mode: Multi-Recipient (Database)")
        print(f"  Database URL: {settings.database_url}")
        try:
            from app.db.session import get_session
            from app.repositories.student import StudentRepository
            with get_session() as session:
                repo = StudentRepository(session)
                students = repo.get_active_subscribers()
                print(f"  Active Subscribers: {len(students)}")
        except Exception as e:
            print(f"  Database Error: {e}")
    else:
        print(f"  Mode: ✗ Not Configured")
        print(f"  Set DATABASE_URL to enable sending")

    # Check general settings
    print(f"\nGeneral Settings:")
    print(f"  Dry Run: {settings.dry_run}")
    print(f"  Audit Log Path: {settings.audit_log_path}")
    print(f"  Send Delay: {settings.send_delay_seconds}s")

    recipient_ok = bool(settings.database_url)
    all_ok = llm_ok and wasender_ok and recipient_ok
    print(f"\nOverall Status: {'✓ READY' if all_ok else '✗ NOT READY'}")
    print("=" * 60 + "\n")

    if not all_ok:
        print("Please configure missing environment variables in .env file")
        print("See .env.example for required variables\n")
        return 1

    return 0


def cmd_preview(args):
    """Preview command handler."""
    service = get_service()

    try:
        result = service.preview_message(
            theme=args.theme,
            level=args.level,
        )
    finally:
        # Close database session if it exists
        if service.db_session:
            service.db_session.close()

    print("\n" + "=" * 60)
    print("PREVIEW (Generate + Validate, No Send)")
    print("=" * 60)
    print(f"Mode: {result.get('mode', 'plain_text')}")
    print(f"Valid: {result['valid']}")

    if result['validation_errors']:
        print(f"\nValidation Errors:")
        for error in result['validation_errors']:
            print(f"  - {error}")

    content = result.get('content')
    if content:
        if result.get('mode') == 'template':
            # Template mode - show parameters
            print(f"\nGenerated Template Parameters:")
            print("-" * 60)
            import json
            print(json.dumps(content, indent=2, ensure_ascii=False))
            print("-" * 60)
        else:
            # Plain text mode - show message
            print(f"\nGenerated Message:")
            print("-" * 60)
            print(content)
            print("-" * 60)
            print(f"Length: {len(content)} characters")

    print("=" * 60 + "\n")

    return 0 if result['valid'] else 1


def cmd_create_admin(args):
    """Create a new admin account."""
    import getpass
    from app.db.session import get_session, init_db
    from app.repositories.admin import AdminRepository
    from app.security import hash_password

    init_db()

    password = getpass.getpass("Password: ")
    if not password:
        print("Error: password cannot be empty.", file=sys.stderr)
        return 1

    with get_session() as session:
        repo = AdminRepository(session)
        if repo.get_by_email(args.email):
            print(f"Error: admin '{args.email}' already exists.", file=sys.stderr)
            return 1
        repo.create(email=args.email, hashed_password=hash_password(password))

    print(f"Admin '{args.email}' created successfully.")
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="XOXO Education - Word of the Day CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Send command
    send_parser = subparsers.add_parser("send", help="Generate and send Word of the Day")
    send_parser.add_argument(
        "--theme",
        default="daily life",
        help="Topic theme (default: daily life)",
    )
    send_parser.add_argument(
        "--level",
        default="beginner",
        choices=["beginner", "intermediate"],
        help="Difficulty level (default: beginner)",
    )
    send_parser.add_argument(
        "--force",
        action="store_true",
        help="Send even if already sent today",
    )
    send_parser.set_defaults(func=cmd_send)

    # Health command
    health_parser = subparsers.add_parser("health", help="Check configuration and readiness")
    health_parser.set_defaults(func=cmd_health)

    # Preview command
    preview_parser = subparsers.add_parser("preview", help="Generate and validate message without sending")
    preview_parser.add_argument(
        "--theme",
        default="daily life",
        help="Topic theme (default: daily life)",
    )
    preview_parser.add_argument(
        "--level",
        default="beginner",
        choices=["beginner", "intermediate"],
        help="Difficulty level (default: beginner)",
    )
    preview_parser.set_defaults(func=cmd_preview)

    # create-admin command
    create_admin_parser = subparsers.add_parser("create-admin", help="Create a new admin user")
    create_admin_parser.add_argument("--email", required=True, help="Admin email address")
    create_admin_parser.set_defaults(func=cmd_create_admin)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except Exception as e:
        print(f"\nError: {e}\n", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
