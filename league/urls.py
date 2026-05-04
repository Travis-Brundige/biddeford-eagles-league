# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("fragment/hello/", views.hello_fragment, name="hello-fragment"),
    path(
        "season/<slug:season_slug>/schedule/print/",
        views.season_schedule_print,
        name="season-schedule-print",
    ),
    path(
        "season/<slug:season_slug>/rosters/print/",
        views.season_rosters_print,
        name="season-rosters-print",
    ),
]
