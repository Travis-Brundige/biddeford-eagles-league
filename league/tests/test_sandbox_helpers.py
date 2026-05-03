# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

import datetime

import pytest

from league.testing.sandbox import (
    create_sandbox_season,
    ensure_season,
    ensure_weeks,
)


@pytest.mark.django_db
def test_ensure_season_is_idempotent():
    a, created_a = ensure_season("ensure-season-slug")
    b, created_b = ensure_season("ensure-season-slug")
    assert created_a is True
    assert created_b is False
    assert a.pk == b.pk


@pytest.mark.django_db
def test_ensure_weeks_idempotent_spacing():
    season = create_sandbox_season("week-spacing-sandbox")
    anchor = datetime.date(2026, 9, 3)
    ensure_weeks(season, 3, anchor=anchor)
    ensure_weeks(season, 3, anchor=anchor)
    weeks = list(season.weeks.order_by("number"))
    assert len(weeks) == 3
    assert weeks[0].calendar_date == anchor
    assert weeks[1].calendar_date == anchor + datetime.timedelta(weeks=1)
    assert weeks[2].calendar_date == anchor + datetime.timedelta(weeks=2)


@pytest.mark.django_db
def test_ensure_weeks_defaults_anchor_to_season_start():
    season = create_sandbox_season(
        "week-default-anchor",
        start_date=datetime.date(2026, 10, 1),
    )
    ensure_weeks(season, 2)
    weeks = list(season.weeks.order_by("number"))
    assert weeks[0].calendar_date == datetime.date(2026, 10, 1)
    assert weeks[1].calendar_date == datetime.date(2026, 10, 8)
