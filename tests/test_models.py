"""Tests for models.py."""

from datetime import datetime, timezone

import pytest

from pwhl_client.models import Game, GameStatus, ScheduleResult


def _make_game(**kwargs) -> Game:
    defaults = dict(
        game_id="1",
        game_status=GameStatus.SCHEDULED,
        home_team="Boston Fleet",
        home_team_id="1",
        visiting_team="Minnesota Frost",
        visiting_team_id="2",
        venue="Tsongas Center",
        city="Lowell",
        game_datetime=datetime(2026, 3, 15, 19, 0, 0, tzinfo=timezone.utc),
        home_goal_count=None,
        visiting_goal_count=None,
    )
    defaults.update(kwargs)
    return Game(**defaults)


def test_game_status_str_values():
    assert GameStatus.SCHEDULED.value == "scheduled"
    assert GameStatus.IN_PROGRESS.value == "in_progress"
    assert GameStatus.COMPLETED.value == "completed"
    assert GameStatus.UNKNOWN.value == "unknown"


def test_game_status_serializes_as_string():
    assert str(GameStatus.IN_PROGRESS) == "in_progress"


def test_game_to_dict_datetime_is_string():
    game = _make_game()
    result = game.to_dict()
    assert isinstance(result["game_datetime"], str)
    assert result["game_datetime"] == "2026-03-15T19:00:00+00:00"


def test_game_to_dict_none_datetime():
    game = _make_game(game_datetime=None)
    assert game.to_dict()["game_datetime"] is None


def test_game_to_dict_game_status_is_string():
    game = _make_game(game_status=GameStatus.IN_PROGRESS)
    assert game.to_dict()["game_status"] == "in_progress"


def test_game_to_dict_none_goals():
    game = _make_game(home_goal_count=None, visiting_goal_count=None)
    result = game.to_dict()
    assert result["home_goal_count"] is None
    assert result["visiting_goal_count"] is None


def test_schedule_result_to_dict_shape():
    result = ScheduleResult(
        games=[], fetched_at=datetime(2026, 3, 15, 19, 0, 0, tzinfo=timezone.utc)
    )
    d = result.to_dict()
    assert set(d.keys()) == {"fetched_at", "game_count", "games"}


def test_schedule_result_to_dict_game_count():
    games = [_make_game(), _make_game(game_id="2")]
    result = ScheduleResult(
        games=games, fetched_at=datetime(2026, 3, 15, 19, 0, 0, tzinfo=timezone.utc)
    )
    assert result.to_dict()["game_count"] == 2


def test_schedule_result_to_dict_empty_games():
    result = ScheduleResult(
        games=[], fetched_at=datetime(2026, 3, 15, 19, 0, 0, tzinfo=timezone.utc)
    )
    d = result.to_dict()
    assert d["game_count"] == 0
    assert d["games"] == []
