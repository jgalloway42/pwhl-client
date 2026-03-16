"""Data models for pwhl-client."""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

logger = logging.getLogger(__name__)

_STATUS_MAP = {
    # Numeric codes returned by the live HockeyTech API
    "1": "scheduled",
    "2": "in_progress",
    "3": "in_progress",
    "4": "completed",
    # Legacy / spec string values kept for backwards compatibility
    "Pre-Game": "scheduled",
    "Scheduled": "scheduled",
    "In Progress": "in_progress",
    "Live": "in_progress",
    "Final": "completed",
    "Official": "completed",
}


class GameStatus(StrEnum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    UNKNOWN = "unknown"

    @classmethod
    def from_raw(cls, raw_value: str) -> "GameStatus":
        mapped = _STATUS_MAP.get(raw_value)
        if mapped is not None:
            return cls(mapped)
        logger.warning("Unrecognized GameStatus: %r", raw_value)
        return cls.UNKNOWN


@dataclass(frozen=True)
class Game:
    game_id: str
    game_status: GameStatus
    home_team: str
    home_team_id: str
    visiting_team: str
    visiting_team_id: str
    venue: str
    city: str
    game_datetime: datetime | None
    home_goal_count: int | None
    visiting_goal_count: int | None
    tickets_url: str

    def to_dict(self) -> dict:
        return {
            "game_id": self.game_id,
            "game_status": self.game_status.value,
            "home_team": self.home_team,
            "home_team_id": self.home_team_id,
            "visiting_team": self.visiting_team,
            "visiting_team_id": self.visiting_team_id,
            "venue": self.venue,
            "city": self.city,
            "game_datetime": (
                self.game_datetime.isoformat()
                if self.game_datetime is not None
                else None
            ),
            "home_goal_count": self.home_goal_count,
            "visiting_goal_count": self.visiting_goal_count,
            "tickets_url": self.tickets_url,
        }


@dataclass
class ScheduleResult:
    games: list[Game]
    fetched_at: datetime

    def to_dict(self) -> dict:
        return {
            "fetched_at": self.fetched_at.isoformat(),
            "game_count": len(self.games),
            "games": [g.to_dict() for g in self.games],
        }
