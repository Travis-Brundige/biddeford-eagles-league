# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

"""Print-friendly season roster context (teams, players, handicap column)."""

from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Prefetch

from league.models import Season, SeasonRosterEntry, SeasonTeam

from .season_schedule_print import team_numbers_by_season_team_pk


@dataclass(frozen=True)
class PlayerRosterLine:
    """One player row; handicap is filled in on paper (blank column in the template)."""

    display_name: str


@dataclass(frozen=True)
class TeamRosterPrintBlock:
    team_number: int
    team_name: str
    players: tuple[PlayerRosterLine, ...]


def build_season_rosters_print_context(season: Season) -> dict[str, object]:
    """
    One block per ``SeasonTeam`` in schedule order, with distinct roster players.

    Players are de-duplicated per team (multiple ``SeasonRosterEntry`` rows for the
    same person appear once). Order is by player display name.
    """
    team_nos = team_numbers_by_season_team_pk(season)

    roster_prefetch = Prefetch(
        "roster_entries",
        queryset=SeasonRosterEntry.objects.select_related("player").order_by(
            "player__display_name",
            "effective_from",
            "pk",
        ),
    )

    season_teams = (
        SeasonTeam.objects.filter(season=season)
        .select_related("team")
        .prefetch_related(roster_prefetch)
        .order_by("team__name", "pk")
    )

    blocks: list[TeamRosterPrintBlock] = []
    for st in season_teams:
        seen: set[int] = set()
        lines: list[PlayerRosterLine] = []
        for entry in st.roster_entries.all():
            pid = entry.player_id
            if pid in seen:
                continue
            seen.add(pid)
            lines.append(PlayerRosterLine(display_name=entry.player.display_name))
        blocks.append(
            TeamRosterPrintBlock(
                team_number=team_nos[st.pk],
                team_name=st.team.name,
                players=tuple(lines),
            )
        )

    return {
        "season": season,
        "teams": tuple(blocks),
    }
