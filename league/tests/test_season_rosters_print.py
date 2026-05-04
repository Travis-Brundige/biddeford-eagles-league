# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

import datetime

import pytest
from django.urls import reverse

from league.models import Player, SeasonRosterEntry, SeasonTeam, Team
from league.services.season_rosters_print import build_season_rosters_print_context
from league.testing.sandbox import create_sandbox_season


@pytest.mark.django_db
def test_rosters_print_dedupes_player_across_entries():
    season = create_sandbox_season("rost-dedupe")
    t = Team.objects.create(name="Solo", slug="rost-solo")
    st = SeasonTeam.objects.create(season=season, team=t)
    p = Player.objects.create(display_name="Alex A", slug="rost-alex")
    SeasonRosterEntry.objects.create(
        season_team=st,
        player=p,
        effective_from=datetime.date(2026, 9, 1),
        effective_to=datetime.date(2026, 10, 1),
    )
    SeasonRosterEntry.objects.create(
        season_team=st,
        player=p,
        effective_from=datetime.date(2026, 10, 2),
        effective_to=None,
    )
    ctx = build_season_rosters_print_context(season)
    assert len(ctx["teams"]) == 1
    assert len(ctx["teams"][0].players) == 1
    assert ctx["teams"][0].players[0].display_name == "Alex A"


@pytest.mark.django_db
def test_rosters_print_team_numbers_match_schedule_order():
    season = create_sandbox_season("rost-nums")
    z = Team.objects.create(name="Zed", slug="rost-z")
    a = Team.objects.create(name="Ann", slug="rost-a")
    SeasonTeam.objects.create(season=season, team=z)
    SeasonTeam.objects.create(season=season, team=a)
    ctx = build_season_rosters_print_context(season)
    by_name = {b.team_name: b.team_number for b in ctx["teams"]}
    assert by_name["Ann"] == 1
    assert by_name["Zed"] == 2


@pytest.mark.django_db
def test_rosters_print_view_ok(client):
    season = create_sandbox_season("rost-view")
    url = reverse("season-rosters-print", kwargs={"season_slug": season.slug})
    response = client.get(url)
    assert response.status_code == 200
    assert season.name.encode() in response.content
    assert b"Team rosters" in response.content


@pytest.mark.django_db
def test_rosters_print_view_404(client):
    url = reverse("season-rosters-print", kwargs={"season_slug": "missing-season"})
    assert client.get(url).status_code == 404
