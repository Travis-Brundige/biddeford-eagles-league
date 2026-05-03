# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

import pytest

from league.constants import LEAGUE_TABLE_COUNT
from league.models import ByeAssignment, ScheduledMatch, SeasonTeam, Team, Week
from league.services.round_robin_schedule import (
    assign_tables_greedy,
    build_week_plans,
    ordered_season_teams,
    replace_season_schedule_from_round_robin,
    schedule_weeks_per_single_cycle,
)
from league.testing.sandbox import create_sandbox_season


def test_build_week_plans_three_teams_one_cycle():
    plans = build_week_plans(3, cycles=1)
    assert len(plans) == 3
    for p in plans:
        assert len(p.matches) == 1
        assert len(p.bye_team_indices) == 1


def test_build_week_plans_three_teams_two_cycles_swaps_home():
    plans = build_week_plans(3, cycles=2)
    assert len(plans) == 6
    assert plans[0].matches[0] != plans[3].matches[0]
    assert plans[0].matches[0] == (plans[3].matches[0][1], plans[3].matches[0][0])


def test_assign_tables_greedy_covers_tables():
    plans = build_week_plans(4, cycles=1)
    tabled = assign_tables_greedy(plans, 4)
    assert len(tabled) == len(plans)
    for week_rows in tabled:
        for _hi, _ai, tbl in week_rows:
            assert 1 <= tbl <= LEAGUE_TABLE_COUNT


def test_schedule_weeks_per_cycle_examples():
    assert schedule_weeks_per_single_cycle(10) == 9
    assert schedule_weeks_per_single_cycle(11) == 11
    assert schedule_weeks_per_single_cycle(12) == 13
    assert schedule_weeks_per_single_cycle(14) == 20


def test_build_week_plans_twelve_teams_one_cycle_shape():
    plans = build_week_plans(12, cycles=1)
    assert len(plans) == 14
    assert all(len(p.matches) <= LEAGUE_TABLE_COUNT for p in plans)
    assert sum(len(p.matches) for p in plans) == 66
    assert all(len(p.matches) == 5 for p in plans[:11])


@pytest.mark.django_db
def test_replace_season_schedule_creates_weeks_matches_byes():
    season = create_sandbox_season("rr-test", name="RR Test")
    for name, slug in (("A", "rr-a"), ("B", "rr-b"), ("C", "rr-c")):
        t = Team.objects.create(name=name, slug=slug)
        SeasonTeam.objects.create(season=season, team=t)

    teams = ordered_season_teams(season)
    summary = replace_season_schedule_from_round_robin(
        season,
        teams,
        cycles=1,
        clear_existing=False,
    )
    assert summary["weeks"] == 3
    assert summary["teams"] == 3
    assert summary["weeks_per_cycle"] == 3
    assert Week.objects.filter(season=season).count() == 3
    assert ScheduledMatch.objects.filter(week__season=season).count() == 3
    assert ByeAssignment.objects.filter(week__season=season).count() == 3
    for m in ScheduledMatch.objects.filter(week__season=season):
        assert m.table_number is not None


@pytest.mark.django_db
def test_replace_max_weeks_truncates_after_twenty_anchors():
    """Cap Thursday rows; build enough cycles to cover the cap; stop mid-rotation."""
    season = create_sandbox_season("rr-12-cap")
    for i in range(12):
        t = Team.objects.create(name=f"C{i}", slug=f"rr-cap-{i}")
        SeasonTeam.objects.create(season=season, team=t)
    teams = ordered_season_teams(season)
    summary = replace_season_schedule_from_round_robin(
        season,
        teams,
        cycles=1,
        clear_existing=False,
        max_weeks=20,
    )
    assert summary["weeks"] == 20
    assert summary["weeks_per_cycle"] == 13
    assert summary["cycles"] == 1
    assert summary["cycles_used"] == 2
    assert summary["max_weeks"] == 20
    assert Week.objects.filter(season=season).count() == 20
    n_matches = ScheduledMatch.objects.filter(week__season=season).count()
    assert 66 < n_matches < 132


@pytest.mark.django_db
def test_replace_max_weeks_out_of_range_raises():
    season = create_sandbox_season("rr-bad-cap")
    t1 = Team.objects.create(name="A", slug="rr-bad-a")
    t2 = Team.objects.create(name="B", slug="rr-bad-b")
    SeasonTeam.objects.create(season=season, team=t1)
    SeasonTeam.objects.create(season=season, team=t2)
    teams = ordered_season_teams(season)
    with pytest.raises(ValueError, match="max_weeks"):
        replace_season_schedule_from_round_robin(
            season,
            teams,
            cycles=1,
            clear_existing=False,
            max_weeks=0,
        )
    with pytest.raises(ValueError, match="max_weeks"):
        replace_season_schedule_from_round_robin(
            season,
            teams,
            cycles=1,
            clear_existing=False,
            max_weeks=54,
        )


@pytest.mark.django_db
def test_replace_twelve_teams_one_cycle_match_and_bye_counts():
    season = create_sandbox_season("rr-12")
    for i in range(12):
        t = Team.objects.create(name=f"T{i}", slug=f"rr-12-{i}")
        SeasonTeam.objects.create(season=season, team=t)
    teams = ordered_season_teams(season)
    summary = replace_season_schedule_from_round_robin(
        season,
        teams,
        cycles=1,
        clear_existing=False,
    )
    assert summary["weeks"] == 13
    assert summary["weeks_per_cycle"] == 13
    assert Week.objects.filter(season=season).count() == 13
    assert ScheduledMatch.objects.filter(week__season=season).count() == 66
    # 12×5 primary + 5 primary on round 13 + 1 make-up (66th pairing) on round 13.
    assert sum(w.matches.count() for w in Week.objects.filter(season=season)) == 66
    for wk in Week.objects.filter(season=season, number__lte=12).order_by("number"):
        assert (
            wk.matches.filter(
                session_kind=ScheduledMatch.SessionKind.MAKEUP_SAME_WEEK
            ).count()
            == 0
        )
        assert (
            wk.matches.filter(
                session_kind=ScheduledMatch.SessionKind.PRIMARY_THURSDAY
            ).count()
            == 5
        )
    final_wk = Week.objects.get(season=season, number=13)
    assert final_wk.matches.count() == 6
    assert (
        final_wk.matches.filter(
            session_kind=ScheduledMatch.SessionKind.PRIMARY_THURSDAY
        ).count()
        == 5
    )
    assert (
        final_wk.matches.filter(
            session_kind=ScheduledMatch.SessionKind.MAKEUP_SAME_WEEK
        ).count()
        == 1
    )
    makeup = final_wk.matches.get(
        session_kind=ScheduledMatch.SessionKind.MAKEUP_SAME_WEEK
    )
    assert makeup.counts_as_round is not None


@pytest.mark.django_db
def test_replace_season_schedule_requires_clear_if_weeks_exist():
    season = create_sandbox_season("rr-clash")
    t1 = Team.objects.create(name="X", slug="rr-clash-x")
    t2 = Team.objects.create(name="Y", slug="rr-clash-y")
    SeasonTeam.objects.create(season=season, team=t1)
    SeasonTeam.objects.create(season=season, team=t2)
    teams = ordered_season_teams(season)
    replace_season_schedule_from_round_robin(
        season,
        teams,
        cycles=1,
        clear_existing=False,
    )
    with pytest.raises(ValueError, match="already has weeks"):
        replace_season_schedule_from_round_robin(
            season,
            teams,
            cycles=1,
            clear_existing=False,
        )


@pytest.mark.django_db
def test_replace_season_schedule_clear_then_regenerate():
    season = create_sandbox_season("rr-clear")
    t1 = Team.objects.create(name="X", slug="rr-clear-x")
    t2 = Team.objects.create(name="Y", slug="rr-clear-y")
    SeasonTeam.objects.create(season=season, team=t1)
    SeasonTeam.objects.create(season=season, team=t2)
    teams = ordered_season_teams(season)
    replace_season_schedule_from_round_robin(
        season,
        teams,
        cycles=1,
        clear_existing=False,
    )
    replace_season_schedule_from_round_robin(
        season,
        teams,
        cycles=2,
        clear_existing=True,
    )
    assert Week.objects.filter(season=season).count() == 2


@pytest.mark.django_db
def test_scheduled_match_unique_per_week_teams():
    """Generator must not double-book the same home/away on one week."""
    season = create_sandbox_season("rr-unique")
    teams = []
    for i in range(4):
        t = Team.objects.create(name=f"T{i}", slug=f"rr-u-{i}")
        teams.append(SeasonTeam.objects.create(season=season, team=t))
    replace_season_schedule_from_round_robin(
        season,
        teams,
        cycles=1,
        clear_existing=False,
    )
    for wk in Week.objects.filter(season=season):
        keys = set()
        for m in wk.matches.all():
            k = (m.home_season_team_id, m.away_season_team_id)
            assert k not in keys
            keys.add(k)
