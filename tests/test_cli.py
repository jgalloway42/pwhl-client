"""Tests for cli.py."""

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from pwhl_client.cli import main
from pwhl_client.exceptions import PWHLAPIError
from pwhl_client.models import GameStatus, ScheduleResult
from pwhl_client.models import Game
from datetime import datetime, timezone


def _empty_result() -> ScheduleResult:
    return ScheduleResult(games=[], fetched_at=datetime.now(timezone.utc))


def _run_main(args: list[str], mocker=None):
    """Patch sys.argv and run main(), returning (exit_code, stdout, stderr)."""
    import sys
    from io import StringIO

    stdout_capture = StringIO()
    stderr_capture = StringIO()

    with patch("sys.argv", ["pwhl-client"] + args), patch(
        "sys.stdout", stdout_capture
    ), patch("sys.stderr", stderr_capture):
        try:
            main()
            exit_code = 0
        except SystemExit as exc:
            exit_code = exc.code

    return exit_code, stdout_capture.getvalue(), stderr_capture.getvalue()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_cli_no_args_uses_today(mocker):
    mocker.patch("pwhl_client.cli.get_schedule", return_value=_empty_result())
    exit_code, stdout, stderr = _run_main([])
    assert exit_code == 0
    pwhl_client_cli = __import__("pwhl_client.cli", fromlist=["get_schedule"])
    call_args = pwhl_client_cli.get_schedule.call_args
    assert call_args.kwargs["start"] == date.today()


def test_cli_date_arg_accepted(mocker):
    mocker.patch("pwhl_client.cli.get_schedule", return_value=_empty_result())
    exit_code, stdout, stderr = _run_main(["2026-03-15"])
    assert exit_code == 0


def test_cli_output_is_valid_json(mocker):
    mocker.patch("pwhl_client.cli.get_schedule", return_value=_empty_result())
    exit_code, stdout, stderr = _run_main([])
    assert exit_code == 0
    parsed = json.loads(stdout)
    assert isinstance(parsed, dict)


def test_cli_output_shape(mocker):
    mocker.patch("pwhl_client.cli.get_schedule", return_value=_empty_result())
    exit_code, stdout, stderr = _run_main([])
    parsed = json.loads(stdout)
    assert "fetched_at" in parsed
    assert "game_count" in parsed
    assert "games" in parsed


def test_cli_valid_tz_accepted(mocker):
    mocker.patch("pwhl_client.cli.get_schedule", return_value=_empty_result())
    exit_code, stdout, stderr = _run_main(["--tz", "America/New_York"])
    assert exit_code == 0


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_cli_api_error_exits_two(mocker):
    mocker.patch("pwhl_client.cli.get_schedule", side_effect=PWHLAPIError("api down"))
    exit_code, stdout, stderr = _run_main([])
    assert exit_code == 2
    assert "api down" in stderr


def test_cli_invalid_date_exits_three():
    exit_code, stdout, stderr = _run_main(["not-a-date"])
    assert exit_code == 3
    assert stderr != ""


def test_cli_invalid_tz_exits_three():
    exit_code, stdout, stderr = _run_main(["--tz", "Foo/Bar"])
    assert exit_code == 3
    assert "Foo/Bar" in stderr


# ---------------------------------------------------------------------------
# Output routing
# ---------------------------------------------------------------------------


def test_cli_json_to_stdout_errors_to_stderr(mocker):
    mocker.patch(
        "pwhl_client.cli.get_schedule", side_effect=PWHLAPIError("something broke")
    )
    exit_code, stdout, stderr = _run_main([])
    assert stdout == ""
    assert "something broke" in stderr
