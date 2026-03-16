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
      "home_goal_count": null,
      "visiting_goal_count": null
    }
  ]
}
```

`game_status` is one of `"scheduled"`, `"in_progress"`, `"completed"`, or `"unknown"`.
`game_datetime` is always timezone-aware and stored in the timezone passed to `get_schedule()`.
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

## Data source

Game data is fetched from the HockeyTech/LeagueStat API, the undocumented backend that powers [thepwhl.com](https://www.thepwhl.com). The API has been reverse-engineered and documented by the community — see the [PWHL Data Reference](https://github.com/IsabelleLefebvre97/PWHL-Data-Reference) repository for full details on available endpoints and parameters.

---

## License

MIT
