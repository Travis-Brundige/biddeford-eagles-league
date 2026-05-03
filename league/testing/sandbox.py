# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

"""
Ephemeral seasons and small object graphs for **automated tests only**.

Production data (e.g. Fall 2026 entered week by week in admin or future UI) is
not represented here — use arbitrary slugs and dates so tests stay isolated.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

from league.models import Season, SeasonTeam, Team, Week


def create_sandbox_season(slug: str, **kwargs: Any) -> Season:
    """Create a season row (typical fall-shaped date window unless overridden)."""
    data: dict[str, Any] = {
        "name": slug.replace("-", " ").title(),
        "slug": slug,
        "start_date": datetime.date(2026, 9, 1),
        "end_date": datetime.date(2027, 3, 31),
        "format": "fall_8ball",
    }
    data.update(kwargs)
    return Season.objects.create(**data)


def ensure_season(slug: str, **kwargs: Any) -> tuple[Season, bool]:
    """``get_or_create`` on ``slug``; defaults match ``create_sandbox_season``."""
    defaults: dict[str, Any] = {
        "name": slug.replace("-", " ").title(),
        "start_date": datetime.date(2026, 9, 1),
        "end_date": datetime.date(2027, 3, 31),
        "format": "fall_8ball",
    }
    defaults.update(kwargs)
    return Season.objects.get_or_create(slug=slug, defaults=defaults)


def ensure_weeks(
    season: Season,
    count: int,
    *,
    anchor: datetime.date | None = None,
) -> None:
    """Create weeks 1..count if missing; ``calendar_date`` steps weekly from anchor."""
    start = anchor if anchor is not None else season.start_date
    for n in range(1, count + 1):
        when = start + datetime.timedelta(weeks=n - 1)
        Week.objects.get_or_create(
            season=season,
            number=n,
            defaults={"calendar_date": when},
        )


@dataclass(frozen=True)
class MinimalSeasonGraph:
    """Two teams and week 1 — enough for model validation tests."""

    season: Season
    week1: Week
    home_team: Team
    away_team: Team
    home_season_team: SeasonTeam
    away_season_team: SeasonTeam


def create_minimal_season_graph(
    slug: str,
    *,
    week1_calendar_date: datetime.date | None = None,
    **season_kwargs: Any,
) -> MinimalSeasonGraph:
    """Season + placeholder teams + week 1; team slugs are prefixed with ``slug``."""
    season = create_sandbox_season(slug, **season_kwargs)
    if week1_calendar_date is not None:
        anchor = week1_calendar_date
    else:
        anchor = season.start_date
    home = Team.objects.create(
        name="(test placeholder home)",
        slug=f"{slug}-test-ph-home",
    )
    away = Team.objects.create(
        name="(test placeholder away)",
        slug=f"{slug}-test-ph-away",
    )
    st_home = SeasonTeam.objects.create(season=season, team=home)
    st_away = SeasonTeam.objects.create(season=season, team=away)
    week1 = Week.objects.create(
        season=season,
        number=1,
        calendar_date=anchor,
    )
    return MinimalSeasonGraph(
        season=season,
        week1=week1,
        home_team=home,
        away_team=away,
        home_season_team=st_home,
        away_season_team=st_away,
    )
