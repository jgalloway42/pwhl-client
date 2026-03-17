"""CLI entrypoint for pwhl-client: pwhl-client [DATE] [--tz TZ]."""

import json
import sys
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .client import get_schedule
from .exceptions import PWHLAPIError, PWHLConfigError


def main() -> None:
    """Entry point for the pwhl-client CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="pwhl-client",
        description="Fetch PWHL game schedules.",
    )
    parser.add_argument(
        "date",
        nargs="?",
        default=None,
        metavar="DATE",
        help="Date to fetch (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--tz",
        default="UTC",
        metavar="TZ",
        help="IANA timezone name (e.g. America/New_York). Defaults to UTC.",
    )

    args = parser.parse_args()

    if args.date is not None:
        try:
            requested_date = date.fromisoformat(args.date)
        except ValueError:
            print(
                f"Invalid date: {args.date!r}. Expected format: YYYY-MM-DD.",
                file=sys.stderr,
            )
            sys.exit(3)
    else:
        requested_date = date.today()

    try:
        tz = ZoneInfo(args.tz)
    except ZoneInfoNotFoundError:
        print(f"Unknown timezone: {args.tz}", file=sys.stderr)
        sys.exit(3)

    try:
        result = get_schedule(start=requested_date, tz=tz)
    except PWHLConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)
    except PWHLAPIError as exc:
        print(f"Error fetching schedule: {exc}", file=sys.stderr)
        sys.exit(2)

    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
