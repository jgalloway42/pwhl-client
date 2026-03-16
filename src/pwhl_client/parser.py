"""Parse raw HockeyTech API responses into Game objects."""

import logging
from datetime import datetime, timezone
from typing import Any

from .exceptions import PWHLParseError
from .models import Game, GameStatus

logger = logging.getLogger(__name__)


def parse_scorebar(raw: dict, tz: timezone) -> list[Game]:
    """Parse a raw scorebar API response into a sorted list of Game objects."""
    if not isinstance(raw, dict):
        raise PWHLParseError("Expected a dict response, got: {type(raw).__name__}")

    try:
        scorebar = raw["SiteKit"]["Scorebar"]
    except KeyError as exc:
        raise PWHLParseError(
            f"Response missing expected key: {exc}. "
            'Expected shape: {{"SiteKit": {{"Scorebar": [...]}}}}'
        ) from exc

    games: list[Game] = []
    for item in scorebar:
        try:
            games.append(_item_to_game(item, tz))
        except Exception:  # pylint: disable=broad-exception-caught
            logger.warning("Skipping malformed scorebar item: %r", item)

    games.sort(key=lambda g: (g.game_datetime is None, g.game_datetime))
    return games


def _item_to_game(item: dict, tz: timezone) -> Game:
    """Convert a single scorebar item dict to a Game. Raises on bad input."""
    return Game(
        game_id=str(item["game_id"]),
        game_status=_parse_status(item["GameStatus"]),
        home_team=str(item["HomeTeam"]["Name"]),
        home_team_id=str(item["HomeTeam"]["ID"]),
        visiting_team=str(item["VisitingTeam"]["Name"]),
        visiting_team_id=str(item["VisitingTeam"]["ID"]),
        venue=str(item["venue_name"]),
        city=str(item["venue_city"]),
        game_datetime=_parse_datetime(item["GameDateISO8601"], tz),
        home_goal_count=_safe_int(item["HomeGoalCount"]),
        visiting_goal_count=_safe_int(item["VisitingGoalCount"]),
        tickets_url=str(item["tickets_url"]),
    )


def _parse_datetime(value: str, tz: timezone) -> datetime | None:
    """Parse an ISO-8601 datetime string and convert to the requested timezone."""
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.astimezone(tz)
    except Exception:  # pylint: disable=broad-exception-caught
        logger.debug("Could not parse datetime: %r", value)
        return None


def _safe_int(value: Any) -> int | None:
    """Convert a value to int, returning None for empty/missing/non-numeric values."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_status(value: str) -> GameStatus:
    """Map a HockeyTech GameStatus string to a GameStatus enum member."""
    return GameStatus.from_raw(value)
