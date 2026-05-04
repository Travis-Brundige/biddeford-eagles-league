# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from league.models import Season
from league.services.season_rosters_print import build_season_rosters_print_context
from league.services.season_schedule_print import build_season_schedule_print_context


def home(request: HttpRequest) -> HttpResponse:
    seasons = Season.objects.order_by("-start_date", "slug")[:24]
    return render(request, "league/home.html", {"seasons": seasons})


def hello_fragment(request: HttpRequest) -> HttpResponse:
    return render(request, "league/_hello_fragment.html")


def season_schedule_print(request: HttpRequest, season_slug: str) -> HttpResponse:
    season = get_object_or_404(Season, slug=season_slug)
    ctx = build_season_schedule_print_context(season)
    return render(request, "league/season_schedule_print.html", ctx)


def season_rosters_print(request: HttpRequest, season_slug: str) -> HttpResponse:
    season = get_object_or_404(Season, slug=season_slug)
    ctx = build_season_rosters_print_context(season)
    return render(request, "league/season_rosters_print.html", ctx)
