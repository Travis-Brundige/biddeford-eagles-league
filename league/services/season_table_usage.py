# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

"""Per-season-team counts of scheduled matches by table number."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from league.constants import LEAGUE_TABLE_COUNT

if TYPE_CHECKING:
    from league.models import Season


def team_table_usage_rows(
    season: Season,
) -> tuple[list[dict[str, Any]], dict[int, int]]:
    """
    Count ``ScheduledMatch`` rows with a table assignment where each season team
    is home or away.

    Returns ``(rows, column_totals)`` where each row is
    ``{"season_team", "by_table", "row_total"}`` with ``by_table`` keys ``1 .. k``.
    """
    from league.models import ScheduledMatch

    pair_counts: defaultdict[tuple[int, int], int] = defaultdict(int)
    qs = ScheduledMatch.objects.filter(
        week__season_id=season.pk,
        table_number__isnull=False,
    ).values_list("home_season_team_id", "away_season_team_id", "table_number")
    for hid, aid, tbl in qs:
        t = int(tbl)
        pair_counts[(hid, t)] += 1
        pair_counts[(aid, t)] += 1

    st_list = list(
        season.season_teams.select_related("team").order_by("team__name", "pk")
    )
    rows: list[dict[str, Any]] = []
    for st in st_list:
        by_t = {
            t: pair_counts.get((st.pk, t), 0)
            for t in range(1, LEAGUE_TABLE_COUNT + 1)
        }
        rows.append(
            {
                "season_team": st,
                "by_table": by_t,
                "row_total": sum(by_t.values()),
            }
        )

    column_totals = {
        t: sum(r["by_table"][t] for r in rows)
        for t in range(1, LEAGUE_TABLE_COUNT + 1)
    }
    return rows, column_totals
