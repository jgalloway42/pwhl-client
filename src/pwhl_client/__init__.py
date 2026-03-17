"""pwhl-client — Fetch PWHL game schedules from the HockeyTech API."""

from .client import get_schedule
from .exceptions import PWHLAPIError, PWHLBaseError, PWHLConfigError, PWHLParseError
from .models import Game, GameStatus, ScheduleResult

__version__ = "0.1.1"
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
