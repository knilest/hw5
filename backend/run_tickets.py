"""Run the agent team on tickets from the command line.

    python run_tickets.py --ticket 102          # one ticket
    python run_tickets.py --all --reset         # reset the DB, then every open ticket

Tickets run one at a time (so two tickets never race for the same cash).
Every agent step is appended to output/audit_trail.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json

from reset_db import reset_db
from team import open_ticket_ids, run_ticket


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Campus Customs agent team")
    parser.add_argument("--ticket", type=int, action="append", help="ticket id (repeatable)")
    parser.add_argument("--all", action="store_true", help="run every open ticket")
    parser.add_argument("--reset", action="store_true", help="reset the working DB first")
    args = parser.parse_args()
    if args.reset:
        print(f"Reset {reset_db()}")
    ids = args.ticket or []
    if args.all:
        ids = await open_ticket_ids()
    if not ids:
        parser.error("give --ticket N or --all")
    for ticket_id in ids:
        print(f"\n=== Ticket {ticket_id} ===")
        decision = await run_ticket(ticket_id)
        print(json.dumps(decision.model_dump(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
