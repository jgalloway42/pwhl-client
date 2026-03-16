"""Tests for client.py."""

import json
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
import requests

from pwhl_client.client import (
    MAX_DAYS_RANGE,
    _DEFAULT_API_KEY,
    get_schedule,
)
from pwhl_client.exceptions import PWHLAPIError, PWHLParseError
from pwhl_client.models import GameStatus, ScheduleResult

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_item(
    game_date_iso: str, game_id: str = "1", status: str = "Pre-Game"
) -> dict:
    return {
        "game_id": game_id,
        "GameStatus": status,
        "GameDateISO8601": game_date_iso,
        "HomeTeam": {"ID": "1", "Name": "Boston Fleet"},
        "VisitingTeam": {"ID": "2", "Name": "Minnesota Frost"},
        "venue_name": "Tsongas Center",
        "venue_city": "Lowell",
        "HomeGoalCount": "",
        "VisitingGoalCount": "",
        "tickets_url": "https://example.com",
    }


def _payload(*items) -> dict:
    return {"SiteKit": {"Scorebar": list(items)}}


def _mock_response(mocker, payload: dict, status_code: int = 200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = payload
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = requests.HTTPError(response=mock_resp)
    else:
        mock_resp.raise_for_status.return_value = None
    mocker.patch("requests.Session.get", return_value=mock_resp)
    return mock_resp


# ---------------------------------------------------------------------------
# API key handling
# ---------------------------------------------------------------------------


def test_fetch_uses_default_api_key(mocker, monkeypatch):
    monkeypatch.delenv("PWHL_API_KEY", raising=False)
    _mock_response(mocker, _payload())
    get_schedule(start=date.today())
    call_kwargs = requests.Session.get.call_args
    assert _DEFAULT_API_KEY in str(call_kwargs)


def test_fetch_env_var_overrides_default(mocker, monkeypatch):
    monkeypatch.setenv("PWHL_API_KEY", "custom_key_xyz")
    _mock_response(mocker, _payload())
    get_schedule(start=date.today())
    call_kwargs = requests.Session.get.call_args
    assert "custom_key_xyz" in str(call_kwargs)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_fetch_happy_path_returns_result(mocker):
    today = date.today()
    _mock_response(mocker, _payload(_make_item(f"{today.isoformat()}T19:00:00+00:00")))
    result = get_schedule(start=today)
    assert isinstance(result, ScheduleResult)


def test_fetch_happy_path_games_filtered_to_date(mocker):
    today = date.today()
    tomorrow = today + timedelta(days=1)
    _mock_response(
        mocker,
        _payload(
            _make_item(f"{today.isoformat()}T19:00:00+00:00", game_id="1"),
            _make_item(f"{tomorrow.isoformat()}T19:00:00+00:00", game_id="2"),
        ),
    )
    result = get_schedule(start=today)
    assert len(result.games) == 1
    assert result.games[0].game_id == "1"


def test_fetch_single_date_sets_end_equal_start(mocker):
    today = date.today()
    _mock_response(mocker, _payload(_make_item(f"{today.isoformat()}T19:00:00+00:00")))
    result = get_schedule(start=today, end=None)
    assert len(result.games) == 1


def test_fetch_range_inclusive_both_ends(mocker):
    today = date.today()
    tomorrow = today + timedelta(days=1)
    _mock_response(
        mocker,
        _payload(
            _make_item(f"{today.isoformat()}T19:00:00+00:00", game_id="1"),
            _make_item(f"{tomorrow.isoformat()}T19:00:00+00:00", game_id="2"),
        ),
    )
    result = get_schedule(start=today, end=tomorrow)
    assert len(result.games) == 2


def test_fetch_start_equals_end(mocker):
    today = date.today()
    _mock_response(mocker, _payload(_make_item(f"{today.isoformat()}T19:00:00+00:00")))
    result = get_schedule(start=today, end=today)
    assert len(result.games) == 1


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_fetch_start_greater_than_end_raises():
    today = date.today()
    yesterday = today - timedelta(days=1)
    with pytest.raises(ValueError, match="start date must be on or before end date"):
        get_schedule(start=today, end=yesterday)


# ---------------------------------------------------------------------------
# HTTP / network errors
# ---------------------------------------------------------------------------


def test_fetch_http_error_raises_api_error(mocker):
    _mock_response(mocker, {}, status_code=500)
    with pytest.raises(PWHLAPIError, match="500"):
        get_schedule(start=date.today())


def test_fetch_network_error_raises_api_error(mocker):
    mocker.patch(
        "requests.Session.get", side_effect=requests.ConnectionError("conn refused")
    )
    with pytest.raises(PWHLAPIError) as exc_info:
        get_schedule(start=date.today())
    assert exc_info.value.__cause__ is not None


def test_fetch_timeout_raises_api_error(mocker):
    mocker.patch("requests.Session.get", side_effect=requests.Timeout("timed out"))
    with pytest.raises(PWHLAPIError) as exc_info:
        get_schedule(start=date.today())
    assert exc_info.value.__cause__ is not None


# ---------------------------------------------------------------------------
# Parse errors
# ---------------------------------------------------------------------------


def test_fetch_non_json_raises_parse_error(mocker):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.side_effect = json.JSONDecodeError("bad json", "", 0)
    mocker.patch("requests.Session.get", return_value=mock_resp)
    with pytest.raises(Exception):
        get_schedule(start=date.today())


def test_fetch_malformed_shape_raises_parse_error(mocker, malformed_payload):
    _mock_response(mocker, malformed_payload)
    with pytest.raises(PWHLParseError):
        get_schedule(start=date.today())


# ---------------------------------------------------------------------------
# Empty results
# ---------------------------------------------------------------------------


def test_fetch_empty_result_within_range(mocker):
    _mock_response(mocker, _payload())
    result = get_schedule(start=date.today())
    assert isinstance(result, ScheduleResult)
    assert result.games == []


def test_fetch_games_with_none_datetime_excluded(mocker):
    today = date.today()
    item_no_dt = _make_item("", game_id="bad")
    item_good = _make_item(f"{today.isoformat()}T19:00:00+00:00", game_id="good")
    _mock_response(mocker, _payload(item_no_dt, item_good))
    result = get_schedule(start=today)
    assert len(result.games) == 1
    assert result.games[0].game_id == "good"


# ---------------------------------------------------------------------------
# days_back / days_ahead calculation
# ---------------------------------------------------------------------------


def test_fetch_days_back_calculation(mocker):
    today = date.today()
    past = today - timedelta(days=10)
    _mock_response(mocker, _payload(_make_item(f"{past.isoformat()}T19:00:00+00:00")))
    result = get_schedule(start=past, end=past)
    call_kwargs = requests.Session.get.call_args
    assert "numberofdaysback" in str(call_kwargs)
    assert "10" in str(call_kwargs)


def test_fetch_days_ahead_calculation(mocker):
    today = date.today()
    future = today + timedelta(days=7)
    _mock_response(mocker, _payload(_make_item(f"{future.isoformat()}T19:00:00+00:00")))
    result = get_schedule(start=future, end=future)
    call_kwargs = requests.Session.get.call_args
    assert "numberofdaysahead" in str(call_kwargs)
    assert "7" in str(call_kwargs)


def test_fetch_tz_affects_today_calculation(mocker):
    # Use a fixed offset timezone well ahead of UTC so "today" differs
    ahead_tz = timezone(timedelta(hours=12))
    today_in_tz = datetime.now(ahead_tz).date()
    _mock_response(
        mocker,
        _payload(_make_item(f"{today_in_tz.isoformat()}T00:00:00+12:00")),
    )
    result = get_schedule(start=today_in_tz, tz=ahead_tz)
    assert isinstance(result, ScheduleResult)


# ---------------------------------------------------------------------------
# fetched_at
# ---------------------------------------------------------------------------


def test_fetch_fetched_at_is_utc_aware(mocker):
    _mock_response(mocker, _payload())
    result = get_schedule(start=date.today())
    assert result.fetched_at.tzinfo is not None
    assert result.fetched_at.utcoffset() == timedelta(0)
