"""
NOTES:
1. This is the management command tool for CrewSignal — like a control panel you run
   from the terminal to set up the app without touching the database by hand.
2. The "provision" command creates a new roofing company (Tenant) in the database and
   generates a secure random API key for them automatically. You copy that key and give
   it to the CRM so it can send webhooks.
3. The "update-tenant" command lets you change a tenant's review URL or message template
   later without having to delete and recreate them from scratch. Look them up by API
   key or business name.
4. The "list-tenants" command shows every company already in the database so you can
   check what's been set up without opening a DB browser.
5. Run this script from the project root using the venv Python so all the app imports
   resolve correctly: .venv\\Scripts\\python.exe manage.py <command>
"""

import argparse
import secrets
import sys
from datetime import timezone

from sqlmodel import Session, select

from app.core.db import create_db_and_tables, engine
from app.models.db_models import DEFAULT_MESSAGE_TEMPLATE, Tenant


# ── helpers ──────────────────────────────────────────────────────────────────

def _divider() -> None:
    print("=" * 62)


def _find_tenant(session: Session, api_key: str | None, business_name: str | None) -> Tenant | None:
    """Look up a tenant by api_key or business_name."""
    if api_key:
        return session.exec(select(Tenant).where(Tenant.api_key == api_key)).first()
    return session.exec(select(Tenant).where(Tenant.business_name == business_name)).first()


def _print_tenant(tenant: Tenant) -> None:
    _divider()
    print(f" Business  : {tenant.business_name}")
    print(f" ID        : {tenant.id}")
    print(f" API Key   : {tenant.api_key}")
    print(f" Review    : {tenant.review_url}")
    print(f" Template  : {tenant.message_template}")
    print(f" Active    : {tenant.is_active}")
    _divider()


# ── core logic (session-injectable so tests can use them directly) ────────────

def do_update_tenant(
    session: Session,
    tenant: Tenant,
    review_url: str | None = None,
    message_template: str | None = None,
) -> Tenant:
    """Apply field updates to a Tenant and commit. Returns the refreshed tenant."""
    if review_url is not None:
        tenant.review_url = review_url
    if message_template is not None:
        tenant.message_template = message_template
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


# ── subcommands ───────────────────────────────────────────────────────────────

def _resolve_review_url(review_url: str | None, place_id: str | None) -> str:
    """Return a review URL. Place ID takes precedence and generates the direct writereview link."""
    if place_id:
        return f"https://search.google.com/local/writereview?placeid={place_id}"
    if review_url:
        return review_url
    raise ValueError("Provide either --review-url or --place-id.")


def cmd_provision(args: argparse.Namespace) -> None:
    """Create a new Tenant and print its generated API key."""
    create_db_and_tables()

    api_key = secrets.token_urlsafe(32)
    review_url = _resolve_review_url(
        getattr(args, "review_url", None),
        getattr(args, "place_id", None),
    )

    tenant = Tenant(
        business_name=args.business_name,
        api_key=api_key,
        review_url=review_url,
        message_template=args.message_template or DEFAULT_MESSAGE_TEMPLATE,
    )

    with Session(engine) as session:
        session.add(tenant)
        session.commit()
        session.refresh(tenant)

        print()
        print(" TENANT PROVISIONED")
        _print_tenant(tenant)
        print(" Copy the API Key above — it will not be shown again.")
        print(" Pass it as X-Api-Key in every webhook and opt-out request.")
        _divider()
        print()


def cmd_update_tenant(args: argparse.Namespace) -> None:
    """Update review_url and/or message_template for an existing Tenant."""
    place_id = getattr(args, "place_id", None)
    review_url = _resolve_review_url(getattr(args, "review_url", None), place_id) if (args.review_url or place_id) else None

    if not review_url and not args.message_template:
        print("ERROR: Provide at least one of --review-url, --place-id, or --message-template.")
        sys.exit(1)

    with Session(engine) as session:
        tenant = _find_tenant(session, args.api_key, args.business_name)

        if not tenant:
            lookup = f"api_key={args.api_key}" if args.api_key else f"business_name={args.business_name}"
            print(f"ERROR: No tenant found with {lookup}")
            sys.exit(1)

        tenant = do_update_tenant(
            session,
            tenant,
            review_url=review_url,
            message_template=args.message_template,
        )

        print()
        print(" TENANT UPDATED")
        _print_tenant(tenant)
        print()


def cmd_list_tenants(_args: argparse.Namespace) -> None:
    """Print all tenants currently in the database."""
    with Session(engine) as session:
        tenants = session.exec(select(Tenant)).all()

    _divider()
    print(f" TENANTS IN DATABASE  ({len(tenants)} total)")
    _divider()

    if not tenants:
        print(" No tenants yet. Run: manage.py provision --business-name ... --review-url ...")
    else:
        for t in tenants:
            created = t.created_at.replace(tzinfo=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            status  = "active" if t.is_active else "INACTIVE"
            print(f" [{status}] {t.business_name}")
            print(f"   ID       : {t.id}")
            print(f"   API Key  : {t.api_key}")
            print(f"   Review   : {t.review_url}")
            print(f"   Template : {t.message_template}")
            print(f"   Created  : {created}")
            print()

    _divider()
    print()


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="manage.py",
        description="CrewSignal management CLI",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # provision
    provision_parser = subparsers.add_parser(
        "provision",
        help="Create a new Tenant and generate their API key",
    )
    provision_parser.add_argument(
        "--business-name",
        required=True,
        metavar="NAME",
        help='e.g. "Rutherford Roofing"',
    )
    review_group = provision_parser.add_mutually_exclusive_group(required=True)
    review_group.add_argument(
        "--review-url",
        metavar="URL",
        help='Full Google review URL, e.g. "https://search.google.com/local/writereview?placeid=..."',
    )
    review_group.add_argument(
        "--place-id",
        metavar="PLACE_ID",
        help='Google Place ID (e.g. ChIJxxxxxxx). Generates the direct writereview URL automatically.',
    )
    provision_parser.add_argument(
        "--message-template",
        default=None,
        metavar="TEMPLATE",
        help=(
            'Optional custom SMS template. Use {customer_name}, {business_name}, '
            'and {review_url} as placeholders. Defaults to the standard CrewSignal template.'
        ),
    )

    # update-tenant
    update_parser = subparsers.add_parser(
        "update-tenant",
        help="Update review_url or message_template for an existing Tenant",
    )
    lookup_group = update_parser.add_mutually_exclusive_group(required=True)
    lookup_group.add_argument(
        "--api-key",
        metavar="KEY",
        help="Find the tenant by their API key",
    )
    lookup_group.add_argument(
        "--business-name",
        metavar="NAME",
        help="Find the tenant by their business name",
    )
    update_parser.add_argument(
        "--review-url",
        default=None,
        metavar="URL",
        help="New full Google review URL",
    )
    update_parser.add_argument(
        "--place-id",
        default=None,
        metavar="PLACE_ID",
        help="New Google Place ID — generates the direct writereview URL automatically",
    )
    update_parser.add_argument(
        "--message-template",
        default=None,
        metavar="TEMPLATE",
        help="New SMS message template (use {customer_name}, {business_name}, {review_url})",
    )

    # list-tenants
    subparsers.add_parser(
        "list-tenants",
        help="Show all tenants currently in the database",
    )

    args = parser.parse_args()

    if args.command == "provision":
        cmd_provision(args)
    elif args.command == "update-tenant":
        cmd_update_tenant(args)
    elif args.command == "list-tenants":
        cmd_list_tenants(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
