[![CI](https://github.com/jgalloway42/pwhl-client/actions/workflows/ci.yml/badge.svg)](https://github.com/jgalloway42/pwhl-client/actions/workflows/ci.yml)
# pwhl-client

Fetch PWHL game schedules from the HockeyTech API. A Python library and CLI tool for developers who want structured, validated schedule data from the Professional Women's Hockey League without dealing with raw API responses.

---

## Install

```bash
pip install pwhl-client
```

---

## Quick start — library

**Single date (defaults to today):**

```python
from pwhl_client import get_schedule

games = get_schedule()
print(games.to_dict())
```

**Specific date:**

```python
from datetime import date
from pwhl_client import get_schedule

games = get_schedule(start=date(2026, 3, 15))
print(games.to_dict())
```

**Date range with timezone:**

```python
from datetime import date
from zoneinfo import ZoneInfo
from pwhl_client import get_schedule

games = get_schedule(
    start=date(2026, 3, 15),
    end=date(2026, 3, 22),
    tz=ZoneInfo("America/New_York"),
)
for game in games.games:
    print(game.home_team, "vs", game.visiting_team, "@", game.game_datetime)
```

---

## Quick start — CLI

```bash
# Today's games
pwhl-client

# Specific date
pwhl-client 2026-03-15

# Specific date with timezone
pwhl-client 2026-03-15 --tz America/New_York
```

---

## Configuration

`PWHL_API_KEY` defaults to the current known public value embedded in the PWHL website's JavaScript. You only need to set it if the key rotates.

```bash
# .env file (recommended)
PWHL_API_KEY=your_new_key_here

# or shell export
export PWHL_API_KEY=your_new_key_here
```

`PWHL_CLIENT_CODE` is hardcoded as `"pwhl"` — it is a fixed league identifier on the HockeyTech platform and is not user-configurable.

---

## Output shape

`ScheduleResult.to_dict()` returns:

```json
{
  "fetched_at": "2026-03-15T19:00:00+00:00",
  "game_count": 1,
  "games": [
    {
      "game_id": "12345",
      "game_status": "scheduled",
      "home_team": "Boston Fleet",
      "home_team_id": "1",
      "visiting_team": "Minnesota Frost",
      "visiting_team_id": "2",
      "venue": "Tsongas Center",
      "city": "Lowell",
      "game_datetime": "2026-03-15T19:00:00-04:00",
      "game_date": "2026-03-15",
      "home_goal_count": null,
      "visiting_goal_count": null
    }
  ]
}
```

`game_status` is one of `"scheduled"`, `"in_progress"`, `"completed"`, or `"unknown"`.
`game_datetime` is always timezone-aware and stored in the timezone passed to `get_schedule()`.
`game_date` is the calendar date the game is played, taken directly from the API's local game date — independent of timezone conversion.
`home_goal_count` and `visiting_goal_count` are `null` for pre-game entries.

---

## Exceptions

`pwhl-client` raises the following exceptions:

- `PWHLAPIError` — raised on network failure, timeout, or a non-2xx HTTP response from the HockeyTech API.
- `PWHLParseError` (subclass of `PWHLAPIError`) — raised when the API returns a response that cannot be parsed or does not match the expected shape.
- `ValueError` — raised when `start` is after `end`.

Catch `PWHLAPIError` to handle both API and parse failures in one place:

```python
from pwhl_client import get_schedule, PWHLAPIError

try:
    result = get_schedule()
except PWHLAPIError as e:
    print(f"Could not fetch schedule: {e}")
```

---

## Known bugs and fixes

### `python -m pwhl_client.cli` silently returned no output (v0.1.0)

**Symptom:** Running `python -m pwhl_client.cli <date>` exited with code 0 but printed nothing, even when games existed.

**Root cause:** `cli.py` defined `main()` but had no `if __name__ == "__main__": main()` guard, so the module ran as a script with no entry point. Additionally, `__main__.py` was absent, so `python -m pwhl_client` was also broken.

**Fix:** Added `if __name__ == "__main__": main()` to `cli.py` and created `__main__.py` to delegate to `cli.main()`.

---

### Today's games missing when `end == today` (v0.1.0)

**Symptom:** Calling `get_schedule()` or `get_schedule(start=date.today())` returned no games even when games were scheduled or in progress for that day.

**Root cause:** The HockeyTech `scorebar` endpoint uses `numberofdaysahead` to control how far forward it looks. When `end == today`, `numberofdaysahead` was computed as `0`, which caused the API to exclude games scheduled later the same day.

**Fix:** When `end >= today`, `numberofdaysahead` is incremented by 1 to ensure the full current day is included. Results are still filtered to the requested date range after fetching.

### Playoff games silently dropped for late-evening starts (v0.1.1)

**Symptom:** Calling `get_schedule(start=date(2026, 4, 30))` returned 0 games despite a completed playoff game on that date (Ottawa @ Boston, Tsongas Center).

**Root cause:** The date filter compared `game_datetime.date()` — the game's start time converted to UTC — against the requested date. A game starting at 8 PM EDT is midnight UTC, so its UTC date is the *next* calendar day. The filter for April 30 therefore silently excluded it. The same issue affects any game starting at or after 8 PM Eastern time when queried in the default UTC timezone.

**Fix (v0.1.2):** Added a `game_date` field to `Game` that stores the calendar date extracted from the API's `GameDateISO8601` string before any timezone conversion (i.e., the date the game is actually played at the arena). The filter in `get_schedule()` now uses `game_date` instead of `game_datetime.date()`. The `game_date` field is also included in `to_dict()` output.

---

## Data source

Game data is fetched from the HockeyTech/LeagueStat API, the undocumented backend that powers [thepwhl.com](https://www.thepwhl.com). The API has been reverse-engineered and documented by the community — see the [PWHL Data Reference](https://github.com/IsabelleLefebvre97/PWHL-Data-Reference) repository for full details on available endpoints and parameters.

---

## License

MIT
