"""Public API for pwhl-client: get_schedule()."""

import os
from datetime import date, datetime, timezone

import requests

from .exceptions import PWHLAPIError
from .models import ScheduleResult
from .parser import parse_scorebar

MAX_DAYS_RANGE = 365
_BASE_URL = "https://lscluster.hockeytech.com/feed/index.php"
_CLIENT_CODE = "pwhl"
_DEFAULT_API_KEY = "446521baf8c38984"
_DEFAULT_TIMEOUT = 10

_OUT_OF_RANGE_MSG = (
    "No games found. The requested date may be outside the supported range "
    "(365 days from today)."
)


def get_schedule(
    start: date = date.today(),
    end: date | None = None,
    tz: timezone = timezone.utc,
    timeout: int = _DEFAULT_TIMEOUT,
) -> ScheduleResult:
    """Fetch PWHL game schedule for the given date range.

    Args:
        start: First date to include (default: today).
        end: Last date to include (default: same as start).
        tz: Timezone for game datetimes and date boundary calculations.
        timeout: HTTP request timeout in seconds.

    Returns:
        ScheduleResult containing matching games sorted by game_datetime.

    Raises:
        ValueError: If start > end.
        PWHLAPIError: On HTTP error, network failure, timeout, or out-of-range date.
        PWHLParseError: If the API response cannot be parsed.
    """
    if end is None:
        end = start

    if start > end:
        raise ValueError("start date must be on or before end date")

    api_key = os.environ.get("PWHL_API_KEY", _DEFAULT_API_KEY)

    today = datetime.now(tz).date()
    days_back = max(0, (today - start).days)
    days_ahead = max(0, (end - today).days)

    if days_back > MAX_DAYS_RANGE or days_ahead > MAX_DAYS_RANGE:
        raise PWHLAPIError(_OUT_OF_RANGE_MSG)

    params = {
        "feed": "modulekit",
        "view": "scorebar",
        "numberofdaysback": days_back,
        "numberofdaysahead": days_ahead,
        "key": api_key,
        "client_code": _CLIENT_CODE,
        "lang": "en",
        "fmt": "json",
    }

    session = requests.Session()
    try:
        response = session.get(_BASE_URL, params=params, timeout=timeout)
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise PWHLAPIError(
            f"HTTP error fetching schedule: {exc.response.status_code}"
        ) from exc
    except requests.RequestException as exc:
        raise PWHLAPIError(f"Network error fetching schedule: {exc}") from exc

    raw = response.json()
    games = parse_scorebar(raw, tz)

    filtered = [
        g
        for g in games
        if g.game_datetime is not None and start <= g.game_datetime.date() <= end
    ]

    if not filtered and (
        days_back > MAX_DAYS_RANGE * 0.9 or days_ahead > MAX_DAYS_RANGE * 0.9
    ):
        raise PWHLAPIError(_OUT_OF_RANGE_MSG)

    return ScheduleResult(games=filtered, fetched_at=datetime.now(timezone.utc))
