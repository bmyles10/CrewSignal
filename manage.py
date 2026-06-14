"""
NOTES:
1. This is the management command tool for CrewSignal — like a control panel you run
   from the terminal to set up the app without touching the database by hand.
2. The "provision" command creates a new roofing company (Tenant) in the database and
   generates a secure random API key for them automatically. You copy that key and give
   it to the CRM so it can send webhooks.
3. The "list-tenants" command shows every company already in the database so you can
   check what's been set up without opening a DB browser.
4. Run this script from the project root using the venv Python so all the app imports
   resolve correctly: .venv\\Scripts\\python.exe manage.py <command>
"""

import argparse
import secrets
import sys
from datetime import timezone

from sqlmodel import Session, select

from app.core.db import create_db_and_tables, engine
from app.models.db_models import Tenant


# ── helpers ──────────────────────────────────────────────────────────────────

def _divider():
    print("=" * 62)


# ── subcommands ───────────────────────────────────────────────────────────────

def cmd_provision(args: argparse.Namespace) -> None:
    """Create a new Tenant and print its generated API key."""
    create_db_and_tables()

    api_key = secrets.token_urlsafe(32)

    tenant = Tenant(
        business_name=args.business_name,
        api_key=api_key,
        review_url=args.review_url,
    )

    with Session(engine) as session:
        session.add(tenant)
        session.commit()
        session.refresh(tenant)

        _divider()
        print(" TENANT PROVISIONED")
        _divider()
        print(f" Business : {tenant.business_name}")
        print(f" ID       : {tenant.id}")
        print(f" API Key  : {tenant.api_key}")
        print(f" Review   : {tenant.review_url}")
        print(f" Active   : {tenant.is_active}")
        _divider()
        print(" Copy the API Key above — it will not be shown again.")
        print(" Pass it as X-Api-Key in every webhook and opt-out request.")
        _divider()
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
            print(f"   ID      : {t.id}")
            print(f"   API Key : {t.api_key}")
            print(f"   Review  : {t.review_url}")
            print(f"   Created : {created}")
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
    provision_parser.add_argument(
        "--review-url",
        required=True,
        metavar="URL",
        help='Google review link, e.g. "https://g.page/rutherford-roofing/review"',
    )

    # list-tenants
    subparsers.add_parser(
        "list-tenants",
        help="Show all tenants currently in the database",
    )

    args = parser.parse_args()

    if args.command == "provision":
        cmd_provision(args)
    elif args.command == "list-tenants":
        cmd_list_tenants(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
