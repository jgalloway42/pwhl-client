"""Shared pytest fixtures for pwhl-client tests."""

import pytest


@pytest.fixture
def sample_scorebar_payload():
    return {
        "SiteKit": {
            "Scorebar": [
                {
                    "game_id": "101",
                    "GameStatus": "Pre-Game",
                    "GameDateISO8601": "2026-03-16T23:00:00+00:00",
                    "HomeTeam": {"ID": "1", "Name": "Boston Fleet"},
                    "VisitingTeam": {"ID": "2", "Name": "Minnesota Frost"},
                    "venue_name": "Tsongas Center",
                    "venue_city": "Lowell",
                    "HomeGoalCount": "",
                    "VisitingGoalCount": "",
                    "tickets_url": "https://example.com/101",
                },
                {
                    "game_id": "102",
                    "GameStatus": "In Progress",
                    "GameDateISO8601": "2026-03-16T20:00:00+00:00",
                    "HomeTeam": {"ID": "3", "Name": "Toronto Sceptres"},
                    "VisitingTeam": {"ID": "4", "Name": "Ottawa Charge"},
                    "venue_name": "Coca-Cola Coliseum",
                    "venue_city": "Toronto",
                    "HomeGoalCount": "2",
                    "VisitingGoalCount": "1",
                    "tickets_url": "https://example.com/102",
                },
                {
                    "game_id": "103",
                    "GameStatus": "Final",
                    "GameDateISO8601": "2026-03-15T18:00:00+00:00",
                    "HomeTeam": {"ID": "5", "Name": "Montreal Victoire"},
                    "VisitingTeam": {"ID": "6", "Name": "New York Sirens"},
                    "venue_name": "Place Bell",
                    "venue_city": "Laval",
                    "HomeGoalCount": "3",
                    "VisitingGoalCount": "2",
                    "tickets_url": "https://example.com/103",
                },
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
