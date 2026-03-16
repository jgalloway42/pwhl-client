"""Shared pytest fixtures for pwhl-client tests."""

import pytest


def _make_scorebar_item(
    game_id: str,
    status_code: str,
    date_iso: str,
    home_id: str,
    home_name: str,
    visitor_id: str,
    visitor_name: str,
    venue: str,
    location: str,
    home_goals: str,
    visitor_goals: str,
    ticket_url: str,
) -> dict:
    return {
        "ID": game_id,
        "GameStatus": status_code,
        "GameDateISO8601": date_iso,
        "HomeID": home_id,
        "HomeLongName": home_name,
        "VisitorID": visitor_id,
        "VisitorLongName": visitor_name,
        "venue_name": venue,
        "venue_location": location,
        "HomeGoals": home_goals,
        "VisitorGoals": visitor_goals,
        "TicketUrl": ticket_url,
    }


@pytest.fixture
def sample_scorebar_payload():
    return {
        "SiteKit": {
            "Scorebar": [
                _make_scorebar_item(
                    "101",
                    "1",
                    "2026-03-16T23:00:00+00:00",
                    "1",
                    "Boston Fleet",
                    "2",
                    "Minnesota Frost",
                    "Tsongas Center",
                    "Lowell, MA",
                    "",
                    "",
                    "https://example.com/101",
                ),
                _make_scorebar_item(
                    "102",
                    "2",
                    "2026-03-16T20:00:00+00:00",
                    "3",
                    "Toronto Sceptres",
                    "4",
                    "Ottawa Charge",
                    "Coca-Cola Coliseum",
                    "Toronto, ON",
                    "2",
                    "1",
                    "https://example.com/102",
                ),
                _make_scorebar_item(
                    "103",
                    "4",
                    "2026-03-15T18:00:00+00:00",
                    "5",
                    "Montreal Victoire",
                    "6",
                    "New York Sirens",
                    "Place Bell",
                    "Laval, QC",
                    "3",
                    "2",
                    "https://example.com/103",
                ),
            ]
        }
    }


@pytest.fixture
def empty_scorebar_payload():
    return {"SiteKit": {"Scorebar": []}}


@pytest.fixture
def malformed_payload():
    return {"not_sitekit": True}


@pytest.fixture
def missing_sitekit_payload():
    return {"SiteKit": {"not_scorebar": []}}
