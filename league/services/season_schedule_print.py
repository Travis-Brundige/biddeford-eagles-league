# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

"""Build context for a print-friendly season schedule (team numbers, tables, dates)."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from django.db.models import F, Prefetch

from league.models import ByeAssignment, ScheduledMatch, Season

from .round_robin_schedule import ordered_season_teams


@dataclass(frozen=True)
class TeamRosterLine:
    """One team row in the schedule key (stable # within season)."""

    number: int
    name: str


@dataclass(frozen=True)
class MatchPrintRow:
    table_number: int | None
    home_team_no: int
    home_team_name: str
    away_team_no: int
    away_team_name: str


@dataclass(frozen=True)
class ByePrintRow:
    team_no: int
    team_name: str
    points: int


@dataclass(frozen=True)
class WeekPrintBlock:
    number: int
    calendar_date: datetime.date | None
    matches: tuple[MatchPrintRow, ...]
    byes: tuple[ByePrintRow, ...]


def team_numbers_by_season_team_pk(season: Season) -> dict[int, int]:
    """Map ``SeasonTeam.pk`` to display number (1-based, name order like scheduling)."""
    return {st.pk: i + 1 for i, st in enumerate(ordered_season_teams(season))}


def build_season_schedule_print_context(season: Season) -> dict[str, object]:
    """
    Prefetch weeks, matches, and byes for one HTML/print page.

    Team numbers follow ``ordered_season_teams`` (team name, then pk).
    """
    team_nos = team_numbers_by_season_team_pk(season)
    roster = tuple(
        TeamRosterLine(number=team_nos[st.pk], name=st.team.name)
        for st in ordered_season_teams(season)
    )

    match_qs = ScheduledMatch.objects.select_related(
        "home_season_team__team",
        "away_season_team__team",
    ).order_by(F("table_number").asc(nulls_last=True), "pk")

    bye_qs = ByeAssignment.objects.select_related("season_team__team").order_by(
        "season_team__team__name",
        "season_team_id",
    )

    weeks_qs = season.weeks.prefetch_related(
        Prefetch("matches", queryset=match_qs),
        Prefetch("bye_assignments", queryset=bye_qs),
    ).order_by("number")

    blocks: list[WeekPrintBlock] = []
    for w in weeks_qs:
        matches = tuple(
            MatchPrintRow(
                table_number=m.table_number,
                home_team_no=team_nos[m.home_season_team_id],
                home_team_name=m.home_season_team.team.name,
                away_team_no=team_nos[m.away_season_team_id],
                away_team_name=m.away_season_team.team.name,
            )
            for m in w.matches.all()
        )
        byes = tuple(
            ByePrintRow(
                team_no=team_nos[b.season_team_id],
                team_name=b.season_team.team.name,
                points=b.team_points_awarded,
            )
            for b in w.bye_assignments.all()
        )
        blocks.append(
            WeekPrintBlock(
                number=w.number,
                calendar_date=w.calendar_date,
                matches=matches,
                byes=byes,
            )
        )

    return {
        "season": season,
        "roster": roster,
        "weeks": tuple(blocks),
    }
