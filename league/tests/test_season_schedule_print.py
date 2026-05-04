# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

import datetime

import pytest
from django.urls import reverse

from league.models import ScheduledMatch, SeasonTeam, Team, Week
from league.services.season_schedule_print import (
    build_season_schedule_print_context,
    team_numbers_by_season_team_pk,
)
from league.testing.sandbox import create_sandbox_season


@pytest.mark.django_db
def test_team_numbers_follow_name_order_not_insert_order():
    season = create_sandbox_season("print-nums")
    # Insert Z first, then A — roster numbers still alphabetical by team name
    z = Team.objects.create(name="Zebra", slug="print-zebra")
    a = Team.objects.create(name="Apple", slug="print-apple")
    st_z = SeasonTeam.objects.create(season=season, team=z)
    st_a = SeasonTeam.objects.create(season=season, team=a)
    nos = team_numbers_by_season_team_pk(season)
    assert nos[st_a.pk] == 1
    assert nos[st_z.pk] == 2


@pytest.mark.django_db
def test_print_context_matches_sorted_by_table_then_byes():
    season = create_sandbox_season("print-ctx")
    t1 = Team.objects.create(name="M", slug="print-m")
    t2 = Team.objects.create(name="N", slug="print-n")
    st1 = SeasonTeam.objects.create(season=season, team=t1)
    st2 = SeasonTeam.objects.create(season=season, team=t2)
    wk = Week.objects.create(
        season=season,
        number=1,
        calendar_date=datetime.date(2026, 9, 10),
    )
    ScheduledMatch.objects.create(
        week=wk,
        home_season_team=st1,
        away_season_team=st2,
        table_number=3,
    )
    ctx = build_season_schedule_print_context(season)
    assert len(ctx["roster"]) == 2
    week = ctx["weeks"][0]
    assert week.number == 1
    assert week.calendar_date == datetime.date(2026, 9, 10)
    assert len(week.matches) == 1
    assert week.matches[0].table_number == 3


@pytest.mark.django_db
def test_schedule_print_view_ok(client):
    season = create_sandbox_season("print-view")
    url = reverse("season-schedule-print", kwargs={"season_slug": season.slug})
    response = client.get(url)
    assert response.status_code == 200
    assert season.name.encode() in response.content


@pytest.mark.django_db
def test_schedule_print_view_404(client):
    url = reverse("season-schedule-print", kwargs={"season_slug": "no-such-season"})
    assert client.get(url).status_code == 404
