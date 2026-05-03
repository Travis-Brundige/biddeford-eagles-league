# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

import datetime

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from league.constants import LEAGUE_TABLE_COUNT
from league.models import (
    ByeAssignment,
    Player,
    ScheduledMatch,
    SeasonRosterEntry,
    SeasonTeam,
    Team,
    Week,
)
from league.testing.sandbox import create_minimal_season_graph, create_sandbox_season


@pytest.mark.django_db
def test_minimal_season_week_match_and_bye(minimal_season_graph):
    g = minimal_season_graph
    assert g.season.slug == "pytest-minimal-graph"
    match = ScheduledMatch.objects.create(
        week=g.week1,
        home_season_team=g.home_season_team,
        away_season_team=g.away_season_team,
        table_number=2,
    )
    bye = ByeAssignment.objects.create(
        week=g.week1,
        season_team=g.home_season_team,
        team_points_awarded=5,
    )

    match.full_clean()
    bye.full_clean()

    assert match.week.season_id == g.season.id
    assert bye.team_points_awarded == 5


@pytest.mark.django_db
def test_scheduled_match_rejects_mismatched_season_teams():
    s1 = create_sandbox_season("cross-season-a")
    s2 = create_sandbox_season(
        "cross-season-b",
        start_date=datetime.date(2026, 4, 1),
        end_date=datetime.date(2026, 8, 31),
        format="summer_scotch_doubles",
    )
    team = Team.objects.create(name="Aces", slug="aces")
    st_s1 = SeasonTeam.objects.create(season=s1, team=team)
    bulls = Team.objects.create(name="Bulls", slug="bulls")
    st_s2 = SeasonTeam.objects.create(season=s2, team=bulls)
    week = Week.objects.create(season=s1, number=1)
    match = ScheduledMatch(
        week=week,
        home_season_team=st_s1,
        away_season_team=st_s2,
    )
    with pytest.raises(ValidationError):
        match.full_clean()


@pytest.mark.django_db
def test_scheduled_match_table_number_respects_league_table_count():
    season = create_sandbox_season("table-sandbox")
    ta = Team.objects.create(name="A", slug="table-sandbox-a")
    tb = Team.objects.create(name="B", slug="table-sandbox-b")
    st_a = SeasonTeam.objects.create(season=season, team=ta)
    st_b = SeasonTeam.objects.create(season=season, team=tb)
    week = Week.objects.create(season=season, number=1)
    match = ScheduledMatch(
        week=week,
        home_season_team=st_a,
        away_season_team=st_b,
        table_number=LEAGUE_TABLE_COUNT + 4,
    )
    with pytest.raises(ValidationError):
        match.full_clean()


@pytest.mark.django_db
def test_bye_assignment_rejects_wrong_season_team():
    s1 = create_sandbox_season("bye-sandbox-a")
    s2 = create_sandbox_season(
        "bye-sandbox-b",
        start_date=datetime.date(2026, 4, 1),
        end_date=datetime.date(2026, 8, 31),
        format="summer_scotch_doubles",
    )
    st = SeasonTeam.objects.create(
        season=s2,
        team=Team.objects.create(name="Solo", slug="solo-bye"),
    )
    week = Week.objects.create(season=s1, number=1)
    bye = ByeAssignment(week=week, season_team=st)
    with pytest.raises(ValidationError):
        bye.full_clean()


@pytest.mark.django_db
def test_unique_season_slug():
    create_sandbox_season("same-slug-unique-test", name="One")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            create_sandbox_season("same-slug-unique-test", name="Two")


@pytest.mark.django_db
def test_unique_week_number_per_season():
    season = create_sandbox_season("week-dup-sandbox")
    Week.objects.create(season=season, number=1)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Week.objects.create(season=season, number=1)


@pytest.mark.django_db
def test_unique_season_team_per_season():
    season = create_sandbox_season("st-dup-sandbox")
    team = Team.objects.create(name="A", slug="st-dup-a")
    SeasonTeam.objects.create(season=season, team=team)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SeasonTeam.objects.create(season=season, team=team)


@pytest.mark.django_db
def test_unique_bye_per_team_per_week():
    season = create_sandbox_season("bye-dup-sandbox")
    st = SeasonTeam.objects.create(
        season=season,
        team=Team.objects.create(name="Bye Team", slug="bye-dup-team"),
    )
    week = Week.objects.create(season=season, number=1)
    ByeAssignment.objects.create(week=week, season_team=st)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ByeAssignment.objects.create(week=week, season_team=st)


@pytest.mark.django_db
def test_roster_entry_date_constraint_integrity():
    season = create_sandbox_season("roster-sandbox")
    st = SeasonTeam.objects.create(
        season=season,
        team=Team.objects.create(name="Roster", slug="roster-sandbox-team"),
    )
    player = Player.objects.create(display_name="Pat")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SeasonRosterEntry.objects.create(
                season_team=st,
                player=player,
                effective_from=datetime.date(2026, 9, 10),
                effective_to=datetime.date(2026, 9, 1),
            )


@pytest.mark.django_db
def test_create_minimal_season_graph_accepts_week1_calendar_date():
    g = create_minimal_season_graph(
        "week-anchor-test",
        week1_calendar_date=datetime.date(2026, 9, 10),
    )
    assert g.week1.calendar_date == datetime.date(2026, 9, 10)
