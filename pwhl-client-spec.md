# `pwhl-client` — Implementation Specification

## Overview

A Python package that fetches PWHL game schedules from the public HockeyTech/LeagueStat API
that powers `thepwhl.com`. Returns structured, validated data as a clean dataclass. Installable
from PyPI. Ships a CLI entrypoint. Zero hardcoded secrets.

---

## Repository Layout

```
pwhl-client/
├── src/
│   └── pwhl_client/
│       ├── __init__.py
│       ├── client.py        # Public API: get_schedule()
│       ├── models.py        # Game, ScheduleResult, GameStatus
│       ├── parser.py        # Raw API dict → list[Game]
│       ├── exceptions.py    # Exception hierarchy
│       └── cli.py           # CLI entrypoint: pwhl-client
├── tests/
│   ├── conftest.py          # Shared fixtures
│   ├── test_client.py
│   ├── test_models.py
│   ├── test_parser.py
│   └── test_cli.py
├── .github/
│   └── workflows/
│       ├── ci.yml           # lint + test on every push/PR
│       └── publish.yml      # publish to PyPI on version tag
├── Makefile
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
└── LICENSE
```

---

## Environment Variables

| Variable       | Required | Default            | Purpose                                      |
|----------------|----------|--------------------|----------------------------------------------|
| `PWHL_API_KEY` | No       | `446521baf8c38984` | HockeyTech API key — override if key rotates |

`PWHL_CLIENT_CODE` is hardcoded as a constant in `client.py` (`"pwhl"`). It is a fixed league
identifier on the HockeyTech platform and is not user-configurable.

`PWHL_API_KEY` defaults to the current known public value embedded in the PWHL website's own
JavaScript. Users only need to set it if the key rotates. The `.env.example` documents this
with the default value pre-filled. The README explains the origin of the key and links to the
PWHL Data Reference repo.

---

## HockeyTech API

**Base URL:** `https://lscluster.hockeytech.com/feed/index.php`

**Endpoint used:** scorebar

**Key parameters:**

| Parameter            | Value                        |
|----------------------|------------------------------|
| `feed`               | `modulekit`                  |
| `view`               | `scorebar`                   |
| `numberofdaysback`   | Calculated from request date |
| `numberofdaysahead`  | Calculated from request date |
| `key`                | `$PWHL_API_KEY`              |
| `client_code`        | `$PWHL_CLIENT_CODE`          |
| `lang`               | `en`                         |
| `fmt`                | `json`                       |

**Response shape:**

```json
{
  "SiteKit": {
    "Scorebar": [
      {
        "game_id": "...",
        "GameStatus": "Pre-Game",
        "GameDateISO8601": "2026-03-15T19:00:00+00:00",
        "HomeTeam": { "ID": "1", "Name": "Boston Fleet" },
        "VisitingTeam": { "ID": "2", "Name": "Minnesota Frost" },
        "venue_name": "Tsongas Center",
        "venue_city": "Lowell",
        "HomeGoalCount": "",
        "VisitingGoalCount": "",
        "tickets_url": "https://..."
      }
    ]
  }
}
```

---

## Exception Hierarchy

```
PWHLBaseError(Exception)
├── PWHLConfigError       # Missing required environment variable
└── PWHLAPIError          # HTTP error, network failure, timeout
    └── PWHLParseError    # Bad JSON, unexpected response shape
```

### `PWHLConfigError`
Reserved for future use if additional required configuration is introduced. Not raised in
the current implementation since `PWHL_API_KEY` has a default value and `PWHL_CLIENT_CODE`
is hardcoded.

### `PWHLAPIError`
Raised on non-2xx HTTP response, network failure, or timeout. Wraps the original
`requests.RequestException` as `__cause__`.

### `PWHLParseError(PWHLAPIError)`
Raised when the response body is not valid JSON, or when the parsed JSON does not contain
the expected `SiteKit.Scorebar` key. Message describes exactly what was missing or malformed.

### `ValueError`
Raised (not a custom exception) when `start > end`. Message:
`"start date must be on or before end date"`.

---

## Models — `models.py`

### `GameStatus`

```python
class GameStatus(str, Enum):
    SCHEDULED   = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    UNKNOWN     = "unknown"
```

Inherits from `str` so values serialize to their string form in JSON without a custom encoder.

**HockeyTech string → `GameStatus` mapping:**

| HockeyTech value(s)               | `GameStatus`  |
|-----------------------------------|---------------|
| `"Pre-Game"`, `"Scheduled"`       | `SCHEDULED`   |
| `"In Progress"`, `"Live"`         | `IN_PROGRESS` |
| `"Final"`, `"Official"`           | `COMPLETED`   |
| Anything else                     | `UNKNOWN`      |

Any unrecognized value maps to `UNKNOWN` and emits `logger.warning(f"Unrecognized GameStatus: {raw_value!r}")`.

---

### `Game` (frozen dataclass)

| Field                 | Type             | Notes                                      |
|-----------------------|------------------|--------------------------------------------|
| `game_id`             | `str`            |                                            |
| `game_status`         | `GameStatus`     | Enum, serializes as string value           |
| `home_team`           | `str`            |                                            |
| `home_team_id`        | `str`            |                                            |
| `visiting_team`       | `str`            |                                            |
| `visiting_team_id`    | `str`            |                                            |
| `venue`               | `str`            |                                            |
| `city`                | `str`            |                                            |
| `game_datetime`       | `datetime\|None` | Always timezone-aware; stored in requested `tz` |
| `home_goal_count`     | `int\|None`      | `None` for pre-game                        |
| `visiting_goal_count` | `int\|None`      | `None` for pre-game                        |
| `tickets_url`         | `str`            |                                            |

**Method:** `to_dict() -> dict` — JSON-safe. `game_datetime` serialized as ISO-8601 string.
`game_status` serializes as its string value (e.g. `"in_progress"`).

---

### `ScheduleResult` (dataclass)

| Field        | Type         | Notes                          |
|--------------|--------------|--------------------------------|
| `games`      | `list[Game]` | Sorted by `game_datetime` asc  |
| `fetched_at` | `datetime`   | UTC-aware timestamp of request |

**Method:** `to_dict() -> dict` — returns:

```json
{
  "fetched_at": "2026-03-15T19:00:00+00:00",
  "game_count": 2,
  "games": [...]
}
```

---

## Client — `client.py`

### Constants

```python
MAX_DAYS_RANGE = 365  # Maximum days from today in either direction
_BASE_URL = "https://lscluster.hockeytech.com/feed/index.php"
_CLIENT_CODE = "pwhl"  # Fixed HockeyTech league identifier — not user-configurable
_DEFAULT_API_KEY = "446521baf8c38984"  # Public key embedded in PWHL website JS
_DEFAULT_TIMEOUT = 10
```

### Public function

```python
def get_schedule(
    start: date = date.today(),
    end: date | None = None,
    tz: timezone = timezone.utc,
    timeout: int = _DEFAULT_TIMEOUT,
) -> ScheduleResult
```

**Behavior, step by step:**

1. **Resolve `end`** — if `end is None`, set `end = start`.

2. **Validate order** — if `start > end`, raise `ValueError("start date must be on or before end date")`.

3. **Read env vars** — read `PWHL_API_KEY` from environment, falling back to `_DEFAULT_API_KEY`
   if not set. Use `_CLIENT_CODE` constant directly — no env var lookup.

4. **Calculate the HockeyTech window** — determine "today" in the requested `tz`:
   ```python
   today = datetime.now(tz).date()
   days_back = max(0, (today - start).days)
   days_ahead = max(0, (end - today).days)
   ```
   Both values are non-negative. If `start` is in the future, `days_back = 0`.
   If `end` is in the past, `days_ahead = 0`.

5. **Range guard** — if `days_back > MAX_DAYS_RANGE` or `days_ahead > MAX_DAYS_RANGE`,
   raise `PWHLAPIError` with message:
   `"No games found. The requested date may be outside the supported range (365 days from today)."`.

6. **Make the HTTP request** — GET to `_BASE_URL` with scorebar params.
   On any `requests.RequestException`, raise `PWHLAPIError` wrapping the original as `__cause__`.
   On non-2xx status, raise `PWHLAPIError` with the status code in the message.

7. **Parse** — pass raw response dict to `parser.parse_scorebar(raw, tz)`.
   This returns `list[Game]` or raises `PWHLParseError`.

8. **Filter to requested window** — keep only games where `game_datetime.date()` falls within
   `[start, end]` inclusive, after converting `game_datetime` to `tz`.
   Games with `game_datetime = None` are excluded.

9. **Empty + out-of-range check** — if the filtered result is empty AND
   (`days_back > MAX_DAYS_RANGE * 0.9` or `days_ahead > MAX_DAYS_RANGE * 0.9`),
   raise `PWHLAPIError` with the descriptive out-of-range message.
   If the result is empty but the date is within range, return an empty `ScheduleResult` — this is valid
   (off-season, bye week, etc.).

10. **Return** `ScheduleResult(games=filtered_games, fetched_at=datetime.now(timezone.utc))`.

---

## Parser — `parser.py`

### `parse_scorebar(raw: dict, tz: timezone) -> list[Game]`

1. Validate shape — confirm `raw` is a `dict` with `raw["SiteKit"]["Scorebar"]` present.
   Raise `PWHLParseError` if not, with a descriptive message identifying exactly what was missing.

2. Iterate items — call `_item_to_game(item, tz)` for each entry in `Scorebar`.

3. Skip bad items — if `_item_to_game` raises any exception, log `WARNING` with the raw item
   and continue. Do not propagate.

4. Sort — by `game_datetime` ascending, `None` datetimes sorted last.

5. Return `list[Game]`.

---

### `_item_to_game(item: dict, tz: timezone) -> Game`

Pure function. Raises on bad input — caller handles via skip logic above.

Field extraction:

| `Game` field          | HockeyTech key                          | Transform                        |
|-----------------------|-----------------------------------------|----------------------------------|
| `game_id`             | `item["game_id"]`                       | `str()`                          |
| `game_status`         | `item["GameStatus"]`                    | `_parse_status()`                |
| `home_team`           | `item["HomeTeam"]["Name"]`              | `str()`                          |
| `home_team_id`        | `item["HomeTeam"]["ID"]`                | `str()`                          |
| `visiting_team`       | `item["VisitingTeam"]["Name"]`          | `str()`                          |
| `visiting_team_id`    | `item["VisitingTeam"]["ID"]`            | `str()`                          |
| `venue`               | `item["venue_name"]`                    | `str()`                          |
| `city`                | `item["venue_city"]`                    | `str()`                          |
| `game_datetime`       | `item["GameDateISO8601"]`               | `_parse_datetime(value, tz)`     |
| `home_goal_count`     | `item["HomeGoalCount"]`                 | `_safe_int()`                    |
| `visiting_goal_count` | `item["VisitingGoalCount"]`             | `_safe_int()`                    |
| `tickets_url`         | `item["tickets_url"]`                   | `str()`                          |

---

### Private helpers

**`_parse_datetime(value: str, tz: timezone) -> datetime | None`**
- Empty string or missing → `None`
- Parse ISO-8601, replacing trailing `Z` with `+00:00` for Python < 3.11 compatibility
- Convert to requested `tz`
- Return timezone-aware `datetime`
- On any parse failure → `None` (log `DEBUG`)

**`_safe_int(value: Any) -> int | None`**
- `None` or `""` → `None`
- Attempt `int(value)` → return result
- On `ValueError` / `TypeError` → `None`

**`_parse_status(value: str) -> GameStatus`**
- Map known HockeyTech strings to `GameStatus` members per the table in Models
- Unknown value → `GameStatus.UNKNOWN` + `logger.warning`

---

## CLI — `cli.py`

### Usage

```
pwhl-client [DATE] [--tz TZ]
```

| Argument | Type              | Default    | Notes                              |
|----------|-------------------|------------|------------------------------------|
| `DATE`   | Positional string | Today      | Format: `YYYY-MM-DD`               |
| `--tz`   | IANA string       | `UTC`      | e.g. `America/New_York`            |

### Behavior

1. Parse `DATE` with `date.fromisoformat()`. On `ValueError` → stderr message, exit 3.
2. Parse `--tz` with `zoneinfo.ZoneInfo(tz_string)`. On `ZoneInfoNotFoundError` →
   stderr message `"Unknown timezone: {tz_string}"`, exit 3.
3. Call `get_schedule(start=date, tz=tz)`.
4. Print `result.to_dict()` as pretty-printed JSON to stdout.

### Exit codes

| Code | Condition                                      |
|------|------------------------------------------------|
| `0`  | Success                                        |
| `1`  | `PWHLConfigError` — reserved, not currently raised |
| `2`  | `PWHLAPIError` / `PWHLParseError`              |
| `3`  | Bad CLI arguments (invalid date or timezone)   |

All error messages go to **stderr**. JSON output goes to **stdout**.

---

## `__init__.py` — Public Exports

```python
from .client import get_schedule
from .models import Game, GameStatus, ScheduleResult
from .exceptions import PWHLBaseError, PWHLConfigError, PWHLAPIError, PWHLParseError

__version__ = "0.1.0"
__all__ = [
    "get_schedule",
    "Game",
    "GameStatus",
    "ScheduleResult",
    "PWHLBaseError",
    "PWHLConfigError",
    "PWHLAPIError",
    "PWHLParseError",
]
```

---

## `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pwhl-client"
version = "0.1.0"
description = "Fetch PWHL game schedules from the HockeyTech API"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [
  { name = "Josh Galloway" }
]
keywords = ["pwhl", "hockey", "sports", "schedule", "hockeytech"]
classifiers = [
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.11",
  "License :: OSI Approved :: MIT License",
  "Operating System :: OS Independent",
  "Intended Audience :: Developers",
  "Topic :: Software Development :: Libraries :: Python Modules",
  "Topic :: Internet :: WWW/HTTP",
]
dependencies = ["requests>=2.28"]

[project.optional-dependencies]
dev = ["pytest", "black", "pytest-mock", "pylint"]

[project.urls]
Homepage = "https://github.com/jgalloway42/pwhl-client"
Repository = "https://github.com/jgalloway42/pwhl-client"
Issues = "https://github.com/jgalloway42/pwhl-client/issues"

[project.scripts]
pwhl-client = "pwhl_client.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/pwhl_client"]
```

---

## Tests

**Framework:** `pytest tests/`
**Format:** `black --check src/ tests/`
**Lint:** `pylint --disable=R,C src/`
**Coverage:** 100% by test plan convention — no `--cov` flag in CI

---

### `conftest.py` — Fixtures

| Fixture                    | Description                                              |
|----------------------------|----------------------------------------------------------|
| `sample_scorebar_payload`  | 3 games: one `SCHEDULED`, one `IN_PROGRESS`, one `COMPLETED` |
| `empty_scorebar_payload`   | Valid shape, `Scorebar` is an empty list                 |
| `malformed_payload`        | Dict missing `SiteKit` key entirely                      |
| `missing_sitekit_payload`  | Has `SiteKit` but no `Scorebar` key                      |

All fixtures are hardcoded dicts mirroring the real HockeyTech response shape.

---

### `test_parser.py`

| Test | Covers |
|---|---|
| `test_parse_scorebar_returns_games` | Happy path, 3 games returned |
| `test_parse_scorebar_empty_list` | Empty scorebar → empty list, no error |
| `test_parse_scorebar_missing_sitekit` | Raises `PWHLParseError` |
| `test_parse_scorebar_missing_scorebar_key` | Raises `PWHLParseError` |
| `test_parse_scorebar_skips_bad_items` | One malformed item → others still parsed |
| `test_parse_scorebar_sorted_by_datetime` | Games returned in ascending datetime order |
| `test_parse_scorebar_none_datetimes_last` | `None` datetimes sorted after valid ones |
| `test_item_to_game_all_fields` | Every field on `Game` populated correctly |
| `test_item_to_game_pre_game_goals_none` | Empty string goal counts → `None` |
| `test_parse_datetime_valid_iso_with_z` | `Z` suffix → aware datetime in requested tz |
| `test_parse_datetime_valid_iso_with_offset` | Offset string → converted to requested tz |
| `test_parse_datetime_empty_string` | Returns `None` |
| `test_parse_datetime_invalid` | Returns `None`, no exception |
| `test_safe_int_numeric_string` | `"3"` → `3` |
| `test_safe_int_integer` | `3` → `3` |
| `test_safe_int_none` | `None` → `None` |
| `test_safe_int_empty_string` | `""` → `None` |
| `test_safe_int_non_numeric` | `"abc"` → `None` |
| `test_parse_status_scheduled` | `"Pre-Game"` → `GameStatus.SCHEDULED` |
| `test_parse_status_in_progress` | `"In Progress"` → `GameStatus.IN_PROGRESS` |
| `test_parse_status_completed_final` | `"Final"` → `GameStatus.COMPLETED` |
| `test_parse_status_completed_official` | `"Official"` → `GameStatus.COMPLETED` |
| `test_parse_status_unknown` | Unrecognized string → `GameStatus.UNKNOWN` |
| `test_parse_status_unknown_emits_warning` | Unrecognized string → `logger.warning` called |

---

### `test_models.py`

| Test | Covers |
|---|---|
| `test_game_status_str_values` | Enum values are lowercase snake_case strings |
| `test_game_status_serializes_as_string` | `str(GameStatus.IN_PROGRESS)` == `"in_progress"` |
| `test_game_to_dict_datetime_is_string` | `game_datetime` serialized as ISO string |
| `test_game_to_dict_none_datetime` | `None` datetime → `None` in dict |
| `test_game_to_dict_game_status_is_string` | `game_status` → string value in dict |
| `test_game_to_dict_none_goals` | `None` goal counts → `None` in dict |
| `test_schedule_result_to_dict_shape` | Keys: `fetched_at`, `game_count`, `games` |
| `test_schedule_result_to_dict_game_count` | `game_count` matches `len(games)` |
| `test_schedule_result_to_dict_empty_games` | Empty list → `game_count: 0` |

---

### `test_client.py`

All HTTP calls mocked via `pytest-mock` patching `requests.Session.get`.

| Test | Covers |
|---|---|
| `test_fetch_uses_default_api_key` | No env var set → `_DEFAULT_API_KEY` used in request |
| `test_fetch_env_var_overrides_default` | `PWHL_API_KEY` env var overrides default |
| `test_fetch_happy_path_returns_result` | Returns `ScheduleResult` |
| `test_fetch_happy_path_games_filtered_to_date` | Only games on requested date returned |
| `test_fetch_single_date_sets_end_equal_start` | `end=None` → `end=start` internally |
| `test_fetch_range_inclusive_both_ends` | Games on `start` and `end` dates both included |
| `test_fetch_start_greater_than_end_raises` | `ValueError` with correct message |
| `test_fetch_http_error_raises_api_error` | Non-2xx → `PWHLAPIError` |
| `test_fetch_network_error_raises_api_error` | `ConnectionError` → `PWHLAPIError` with `__cause__` |
| `test_fetch_timeout_raises_api_error` | `Timeout` → `PWHLAPIError` with `__cause__` |
| `test_fetch_non_json_raises_parse_error` | Bad body → `PWHLParseError` |
| `test_fetch_malformed_shape_raises_parse_error` | Missing `SiteKit` → `PWHLParseError` |
| `test_fetch_empty_result_within_range` | Empty games, date within range → empty `ScheduleResult` |
| `test_fetch_days_back_calculation` | `days_back` correct for past date |
| `test_fetch_days_ahead_calculation` | `days_ahead` correct for future date |
| `test_fetch_tz_affects_today_calculation` | Date boundary shifts with non-UTC tz |
| `test_fetch_fetched_at_is_utc_aware` | `fetched_at` is UTC timezone-aware |
| `test_fetch_games_with_none_datetime_excluded` | Games with `None` datetime filtered out |
| `test_fetch_start_equals_end` | Single day range works correctly |

---

### `test_cli.py`

Uses `subprocess` with env var injection and `capsys` / stdout capture.

| Test | Covers |
|---|---|
| `test_cli_no_args_uses_today` | No date → uses today's date |
| `test_cli_date_arg_accepted` | `pwhl-client 2026-03-15` → exit 0 |
| `test_cli_output_is_valid_json` | stdout parses as JSON |
| `test_cli_output_shape` | JSON has `fetched_at`, `game_count`, `games` keys |
| `test_cli_api_error_exits_two` | `PWHLAPIError` → exit 2, stderr message |
| `test_cli_invalid_date_exits_three` | `"not-a-date"` → exit 3, stderr message |
| `test_cli_invalid_tz_exits_three` | `--tz Foo/Bar` → exit 3, stderr message |
| `test_cli_valid_tz_accepted` | `--tz America/New_York` → exit 0 |
| `test_cli_json_to_stdout_errors_to_stderr` | JSON on stdout, errors on stderr |

---

## Makefile

```makefile
.PHONY: install format lint test build clean check

install:
	pip install -e ".[dev]"

format:
	black src/ tests/

lint:
	black --check src/ tests/
	pylint --disable=R,C src/

test:
	pytest tests/

check: format lint test

build:
	python -m build

clean:
	rm -rf dist/ *.egg-info src/*.egg-info __pycache__
```

`check` is the pre-push habit: formats files, verifies lint, runs the full test suite.
`lint` is what CI runs — `black --check` fails on any diff rather than fixing in place.

---

## CI/CD — GitHub Actions

### `ci.yml` — triggers on push and PR to `main`

```yaml
steps:
  - Checkout
  - Set up Python 3.11
  - pip install -e ".[dev]"
  - black --check src/ tests/
  - pylint --disable=R,C src/
  - pytest tests/
```

### `publish.yml` — triggers on push of tag matching `v*.*.*`

Uses PyPI's **Trusted Publishers** mechanism (OIDC) — no API token or secret required.
GitHub acts as an identity provider; PyPI issues a short-lived token (15 min) at publish time.

The workflow is intentionally split into two jobs. The `id-token: write` permission is
sensitive and must be scoped only to the publish job, not the build step.

```yaml
name: Publish to PyPI

on:
  push:
    tags:
      - "v*.*.*"

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install build backend
        run: pip install hatchling build
      - name: Build distributions
        run: python -m build
      - uses: actions/upload-artifact@v4
        with:
          name: python-package-distributions
          path: dist/

  publish:
    needs: build
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: python-package-distributions
          path: dist/
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

**One-time manual setup on PyPI (done before first publish):**
1. Create a PyPI account with 2FA enabled.
2. Go to `pypi.org/manage/account/publishing/` and add a pending publisher with:
   - Package name: `pwhl-client`
   - GitHub owner: your GitHub username
   - Repository name: `pwhl-client`
   - Workflow filename: `publish.yml`
   - Environment: `pypi`
3. Create a `pypi` environment in the GitHub repo under Settings → Environments.

The version in `pyproject.toml` must match the tag. No dynamic versioning. No secrets to manage.

---

## Implementation Order for Claude Code

Implement in this order — each step has no forward dependencies:

1. `exceptions.py` — no dependencies
2. `models.py` — no dependencies
3. `test_models.py` — depends on `models.py`
4. `parser.py` — depends on `models.py`, `exceptions.py`
5. `test_parser.py` + `conftest.py` — depends on `parser.py`
6. `client.py` — depends on `parser.py`, `models.py`, `exceptions.py`
7. `test_client.py` — depends on `client.py`
8. `cli.py` — depends on `client.py`, `exceptions.py`
9. `test_cli.py` — depends on `cli.py`
10. `__init__.py` — depends on all modules
11. `pyproject.toml` — use the full version from this spec including authors, URLs, keywords, classifiers
12. `Makefile` — use the version from this spec exactly
13. `ci.yml` + `publish.yml`
14. `README.md` — must include all nine sections defined in the README spec below
15. `.env.example`
16. `.gitignore` — already in the repo. Verify it includes `.env` and `dist/`. Append only if missing, do not overwrite.
17. `LICENSE` — already in the repo. Do not modify.

---

## README Spec

The README must include the following nine sections in order. Be explicit and complete —
do not write a thin or placeholder README.

### 1. Title + description
`pwhl-client` — Fetch PWHL game schedules from the HockeyTech API. One sentence explaining
what the package does and who it is for.

### 2. Install
```bash
pip install pwhl-client
```

### 3. Quick start — library
Three working code snippets:

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

### 4. Quick start — CLI
```bash
# Today's games
pwhl-client

# Specific date
pwhl-client 2026-03-15

# Specific date with timezone
pwhl-client 2026-03-15 --tz America/New_York
```

### 5. Configuration
Explain that `PWHL_API_KEY` defaults to the current known public value and users only need
to set it if the key rotates. Show both methods:

```bash
# .env file (recommended)
PWHL_API_KEY=your_new_key_here

# or shell export
export PWHL_API_KEY=your_new_key_here
```

Note that `PWHL_CLIENT_CODE` is hardcoded and not user-configurable.

### 6. Output shape
Show the full JSON structure returned by `ScheduleResult.to_dict()`:

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
      "visiting_goal_count": null,
      "tickets_url": "https://..."
    }
  ]
}
```

### 7. Exceptions
One paragraph explaining what callers should catch and when:
- `PWHLAPIError` — network failure, timeout, or non-2xx HTTP response from the HockeyTech API
- `PWHLParseError` (subclass of `PWHLAPIError`) — API returned a response that could not be parsed
- `ValueError` — `start` date is after `end` date

Show a basic try/except example:
```python
from pwhl_client import get_schedule, PWHLAPIError

try:
    result = get_schedule()
except PWHLAPIError as e:
    print(f"Could not fetch schedule: {e}")
```

### 8. Data source
Credit the HockeyTech/LeagueStat API as the underlying data provider powering `thepwhl.com`.
Note that the API is undocumented but has been reverse-engineered and documented by the
community. Link to `https://github.com/IsabelleLefebvre97/PWHL-Data-Reference`.

### 9. License
MIT
