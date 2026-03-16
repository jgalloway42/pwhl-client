"""Tests for parser.py."""

import logging
from datetime import datetime, timezone

import pytest

from pwhl_client.exceptions import PWHLParseError
from pwhl_client.models import GameStatus
from pwhl_client.parser import (
    _parse_datetime,
    _parse_status,
    _safe_int,
    parse_scorebar,
)

UTC = timezone.utc
ET = timezone(offset=__import__("datetime").timedelta(hours=-5))


# ---------------------------------------------------------------------------
# parse_scorebar — happy path
# ---------------------------------------------------------------------------


def test_parse_scorebar_returns_games(sample_scorebar_payload):
    games = parse_scorebar(sample_scorebar_payload, UTC)
    assert len(games) == 3


def test_parse_scorebar_empty_list(empty_scorebar_payload):
    games = parse_scorebar(empty_scorebar_payload, UTC)
    assert games == []


def test_parse_scorebar_missing_sitekit(malformed_payload):
    with pytest.raises(PWHLParseError):
        parse_scorebar(malformed_payload, UTC)


def test_parse_scorebar_missing_scorebar_key(missing_sitekit_payload):
    with pytest.raises(PWHLParseError):
        parse_scorebar(missing_sitekit_payload, UTC)


def test_parse_scorebar_skips_bad_items(sample_scorebar_payload):
    # Corrupt the second item so _item_to_game raises
    sample_scorebar_payload["SiteKit"]["Scorebar"][1].pop("HomeLongName")
    games = parse_scorebar(sample_scorebar_payload, UTC)
    assert len(games) == 2


def test_parse_scorebar_sorted_by_datetime(sample_scorebar_payload):
    games = parse_scorebar(sample_scorebar_payload, UTC)
    datetimes = [g.game_datetime for g in games if g.game_datetime is not None]
    assert datetimes == sorted(datetimes)


def test_parse_scorebar_none_datetimes_last(sample_scorebar_payload):
    # Make the first item have no datetime
    sample_scorebar_payload["SiteKit"]["Scorebar"][0]["GameDateISO8601"] = ""
    games = parse_scorebar(sample_scorebar_payload, UTC)
    # All non-None datetimes should come before None
    none_seen = False
    for g in games:
        if g.game_datetime is None:
            none_seen = True
        else:
            assert not none_seen, "Non-None datetime appeared after a None datetime"


# ---------------------------------------------------------------------------
# _item_to_game — field mapping
# ---------------------------------------------------------------------------


def _scheduled_item():
    return {
        "ID": "999",
        "GameStatus": "1",
        "GameDateISO8601": "2026-03-16T23:00:00+00:00",
        "HomeID": "1",
        "HomeLongName": "Boston Fleet",
        "VisitorID": "2",
        "VisitorLongName": "Minnesota Frost",
        "venue_name": "Tsongas Center",
        "venue_location": "Lowell, MA",
        "HomeGoals": "",
        "VisitorGoals": "",
    }


def test_item_to_game_all_fields():
    from pwhl_client.parser import _item_to_game

    item = _scheduled_item()
    item["HomeGoals"] = "2"
    item["VisitorGoals"] = "1"
    item["GameStatus"] = "4"
    game = _item_to_game(item, UTC)

    assert game.game_id == "999"
    assert game.game_status == GameStatus.COMPLETED
    assert game.home_team == "Boston Fleet"
    assert game.home_team_id == "1"
    assert game.visiting_team == "Minnesota Frost"
    assert game.visiting_team_id == "2"
    assert game.venue == "Tsongas Center"
    assert game.city == "Lowell, MA"
    assert game.game_datetime is not None
    assert game.home_goal_count == 2
    assert game.visiting_goal_count == 1


def test_item_to_game_pre_game_goals_none():
    from pwhl_client.parser import _item_to_game

    game = _item_to_game(_scheduled_item(), UTC)
    assert game.home_goal_count is None
    assert game.visiting_goal_count is None


# ---------------------------------------------------------------------------
# _parse_datetime
# ---------------------------------------------------------------------------


def test_parse_datetime_valid_iso_with_z():
    dt = _parse_datetime("2026-03-16T23:00:00Z", UTC)
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.year == 2026 and dt.month == 3 and dt.day == 16


def test_parse_datetime_valid_iso_with_offset():
    dt = _parse_datetime("2026-03-16T18:00:00-05:00", UTC)
    assert dt is not None
    assert dt.tzinfo == UTC
    assert dt.hour == 23  # -05:00 converted to UTC


def test_parse_datetime_empty_string():
    assert _parse_datetime("", UTC) is None


def test_parse_datetime_invalid():
    assert _parse_datetime("not-a-date", UTC) is None


# ---------------------------------------------------------------------------
# _safe_int
# ---------------------------------------------------------------------------


def test_safe_int_numeric_string():
    assert _safe_int("3") == 3


def test_safe_int_integer():
    assert _safe_int(3) == 3


def test_safe_int_none():
    assert _safe_int(None) is None


def test_safe_int_empty_string():
    assert _safe_int("") is None


def test_safe_int_non_numeric():
    assert _safe_int("abc") is None


# ---------------------------------------------------------------------------
# _parse_status
# ---------------------------------------------------------------------------


def test_parse_status_scheduled():
    assert _parse_status("1") == GameStatus.SCHEDULED


def test_parse_status_in_progress():
    assert _parse_status("2") == GameStatus.IN_PROGRESS


def test_parse_status_completed_final():
    assert _parse_status("4") == GameStatus.COMPLETED


def test_parse_status_completed_official():
    assert _parse_status("Official") == GameStatus.COMPLETED


def test_parse_status_unknown():
    assert _parse_status("99") == GameStatus.UNKNOWN


def test_parse_status_unknown_emits_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="pwhl_client.models"):
        result = _parse_status("99")
    assert result == GameStatus.UNKNOWN
    assert any("99" in r.message for r in caplog.records)
