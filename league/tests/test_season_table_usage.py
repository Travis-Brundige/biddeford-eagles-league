# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

import pytest

from league.models import ScheduledMatch, SeasonTeam, Team, Week
from league.services.season_table_usage import team_table_usage_rows
from league.testing.sandbox import create_sandbox_season


@pytest.mark.django_db
def test_team_table_usage_counts_home_and_away():
    season = create_sandbox_season("tu")
    t1 = Team.objects.create(name="A", slug="tu-a")
    t2 = Team.objects.create(name="B", slug="tu-b")
    st1 = SeasonTeam.objects.create(season=season, team=t1)
    st2 = SeasonTeam.objects.create(season=season, team=t2)
    wk = Week.objects.create(season=season, number=1)
    ScheduledMatch.objects.create(
        week=wk,
        home_season_team=st1,
        away_season_team=st2,
        table_number=2,
        status=ScheduledMatch.Status.SCHEDULED,
    )
    rows, col = team_table_usage_rows(season)
    assert len(rows) == 2
    by_team = {r["season_team"].pk: r["by_table"] for r in rows}
    assert by_team[st1.pk][2] == 1
    assert by_team[st2.pk][2] == 1
    for t in (1, 3, 4, 5):
        assert by_team[st1.pk][t] == 0
    assert col[2] == 2
    assert sum(col.values()) == 2


@pytest.mark.django_db
def test_team_table_usage_ignores_null_table():
    season = create_sandbox_season("tu2")
    t1 = Team.objects.create(name="A", slug="tu2-a")
    t2 = Team.objects.create(name="B", slug="tu2-b")
    st1 = SeasonTeam.objects.create(season=season, team=t1)
    st2 = SeasonTeam.objects.create(season=season, team=t2)
    wk = Week.objects.create(season=season, number=1)
    ScheduledMatch.objects.create(
        week=wk,
        home_season_team=st1,
        away_season_team=st2,
        table_number=None,
        status=ScheduledMatch.Status.SCHEDULED,
    )
    rows, col = team_table_usage_rows(season)
    assert all(r["row_total"] == 0 for r in rows)
    assert sum(col.values()) == 0


@pytest.mark.django_db
def test_team_table_usage_other_season_excluded():
    season = create_sandbox_season("tu3")
    other = create_sandbox_season("tu3-other")
    t1 = Team.objects.create(name="A", slug="tu3-a")
    t2 = Team.objects.create(name="B", slug="tu3-b")
    st1 = SeasonTeam.objects.create(season=season, team=t1)
    st2 = SeasonTeam.objects.create(season=season, team=t2)
    wk = Week.objects.create(season=season, number=1)
    ScheduledMatch.objects.create(
        week=wk,
        home_season_team=st1,
        away_season_team=st2,
        table_number=1,
        status=ScheduledMatch.Status.SCHEDULED,
    )
    w_other = Week.objects.create(season=other, number=1)
    st_o1 = SeasonTeam.objects.create(season=other, team=t1)
    st_o2 = SeasonTeam.objects.create(season=other, team=t2)
    ScheduledMatch.objects.create(
        week=w_other,
        home_season_team=st_o1,
        away_season_team=st_o2,
        table_number=1,
        status=ScheduledMatch.Status.SCHEDULED,
    )
    rows, _col = team_table_usage_rows(season)
    by_team = {r["season_team"].pk: r["by_table"] for r in rows}
    assert by_team[st1.pk][1] == 1
    assert by_team[st2.pk][1] == 1
