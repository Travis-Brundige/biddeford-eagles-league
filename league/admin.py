# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from league.admin_carryover import CarryoverFieldsOnAddAnotherMixin
from league.constants import LEAGUE_TABLE_COUNT
from league.forms_admin import RoundRobinScheduleForm
from league.models import (
    ByeAssignment,
    Player,
    ScheduledMatch,
    Season,
    SeasonRosterEntry,
    SeasonTeam,
    Team,
    Week,
)
from league.services.round_robin_schedule import (
    ordered_season_teams,
    replace_season_schedule_from_round_robin,
    schedule_weeks_per_single_cycle,
)
from league.services.season_table_usage import team_table_usage_rows


class SeasonTeamInline(admin.TabularInline):
    model = SeasonTeam
    extra = 0
    autocomplete_fields = ("team",)
    show_change_link = True


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    change_form_template = "admin/league/season_change_form.html"
    list_display = (
        "name",
        "slug",
        "format",
        "status",
        "start_date",
        "end_date",
    )
    list_filter = ("status", "format")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SeasonTeamInline]

    def get_urls(self):
        info = self.model._meta.model_name
        return [
            path(
                "<path:object_id>/generate-schedule/",
                self.admin_site.admin_view(self.generate_schedule_view),
                name=f"{self.opts.app_label}_{info}_generate_schedule",
            ),
            path(
                "<path:object_id>/table-usage/",
                self.admin_site.admin_view(self.table_usage_view),
                name=f"{self.opts.app_label}_{info}_table_usage",
            ),
        ] + super().get_urls()

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        if object_id and str(object_id) != "add":
            extra_context["generate_schedule_url"] = reverse(
                f"admin:{self.opts.app_label}_{self.model._meta.model_name}_generate_schedule",
                args=[object_id],
            )
            extra_context["table_usage_url"] = reverse(
                f"admin:{self.opts.app_label}_{self.model._meta.model_name}_table_usage",
                args=[object_id],
            )
        return super().change_view(request, object_id, form_url, extra_context)

    def generate_schedule_view(self, request, object_id):
        if not self.has_change_permission(request):
            raise PermissionDenied
        season = get_object_or_404(Season, pk=object_id)
        if not self.has_change_permission(request, season):
            raise PermissionDenied

        teams = ordered_season_teams(season)
        team_count = len(teams)
        weeks_one_cycle = (
            schedule_weeks_per_single_cycle(team_count) if team_count >= 2 else None
        )

        opts = self.model._meta
        if request.method == "POST":
            form = RoundRobinScheduleForm(request.POST)
            if form.is_valid() and team_count >= 2:
                try:
                    summary = replace_season_schedule_from_round_robin(
                        season,
                        teams,
                        cycles=form.cleaned_data["cycles"],
                        clear_existing=form.cleaned_data["clear_existing"],
                        max_weeks=form.cleaned_data.get("max_weeks"),
                    )
                except ValueError as exc:
                    messages.error(request, str(exc))
                else:
                    msg = (
                        "Schedule created: %(weeks)s round anchors (Thursday weeks), "
                        "%(teams)s teams, %(cycles)s cycle(s) requested "
                        "(%(used)s built), %(wpc)s anchors per full round-robin."
                    ) % {
                        "weeks": summary["weeks"],
                        "teams": summary["teams"],
                        "cycles": summary["cycles"],
                        "used": summary["cycles_used"],
                        "wpc": summary["weeks_per_cycle"],
                    }
                    messages.success(request, msg)
                    return redirect("admin:league_season_change", season.pk)
        else:
            form = RoundRobinScheduleForm()

        context = {
            **self.admin_site.each_context(request),
            "title": _("Generate round-robin schedule"),
            "opts": opts,
            "season": season,
            "form": form,
            "team_count": team_count,
            "weeks_one_cycle": weeks_one_cycle,
            "max_tables": LEAGUE_TABLE_COUNT,
            "media": self.media,
        }
        return render(
            request,
            "admin/league/season_generate_schedule.html",
            context,
        )

    def table_usage_view(self, request, object_id):
        if not self.has_change_permission(request):
            raise PermissionDenied
        season = get_object_or_404(Season, pk=object_id)
        if not self.has_change_permission(request, season):
            raise PermissionDenied

        opts = self.model._meta
        usage_rows, column_totals = team_table_usage_rows(season)
        for r in usage_rows:
            r["cells"] = [r["by_table"][t] for t in range(1, LEAGUE_TABLE_COUNT + 1)]
        column_cells = [column_totals[t] for t in range(1, LEAGUE_TABLE_COUNT + 1)]
        grand_total = sum(column_totals.values())
        context = {
            **self.admin_site.each_context(request),
            "title": _("Table usage by team"),
            "opts": opts,
            "season": season,
            "usage_rows": usage_rows,
            "table_numbers": list(range(1, LEAGUE_TABLE_COUNT + 1)),
            "column_cells": column_cells,
            "grand_total": grand_total,
            "media": self.media,
        }
        return render(
            request,
            "admin/league/season_table_usage.html",
            context,
        )


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


class SeasonRosterEntryInline(admin.TabularInline):
    model = SeasonRosterEntry
    extra = 0
    autocomplete_fields = ("player",)


@admin.register(SeasonTeam)
class SeasonTeamAdmin(CarryoverFieldsOnAddAnotherMixin, admin.ModelAdmin):
    carryover_fields = ("season", "first_week_number", "last_week_number")
    list_display = ("team", "season", "first_week_number", "last_week_number")
    list_filter = ("season",)
    search_fields = ("team__name", "team__slug", "season__name", "season__slug")
    autocomplete_fields = ("season", "team")
    inlines = [SeasonRosterEntryInline]
    fieldsets = (
        (
            None,
            {
                "fields": ("season", "team", "first_week_number", "last_week_number"),
                "description": _(
                    "Add roster entries below (player + effective dates). "
                    "Use the season start date for players who begin at week 1."
                ),
            },
        ),
    )


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("display_name", "slug", "email")
    search_fields = ("display_name", "slug", "email")
    prepopulated_fields = {"slug": ("display_name",)}


@admin.register(SeasonRosterEntry)
class SeasonRosterEntryAdmin(CarryoverFieldsOnAddAnotherMixin, admin.ModelAdmin):
    carryover_fields = ("season_team", "effective_from", "effective_to")
    list_display = ("player", "season_team", "effective_from", "effective_to")
    list_filter = ("season_team__season",)
    search_fields = (
        "player__display_name",
        "season_team__team__name",
        "season_team__season__slug",
    )
    autocomplete_fields = ("season_team", "player")
    date_hierarchy = "effective_from"


@admin.register(Week)
class WeekAdmin(CarryoverFieldsOnAddAnotherMixin, admin.ModelAdmin):
    carryover_fields = ("season",)
    list_display = ("season", "number", "calendar_date")
    list_filter = ("season",)
    search_fields = ("season__name", "season__slug")
    ordering = ("season", "number")
    autocomplete_fields = ("season",)


@admin.register(ScheduledMatch)
class ScheduledMatchAdmin(CarryoverFieldsOnAddAnotherMixin, admin.ModelAdmin):
    carryover_fields = ("week", "session_kind", "status")
    list_display = (
        "week",
        "counts_as_round",
        "played_on",
        "session_kind",
        "home_season_team",
        "away_season_team",
        "table_number",
        "status",
    )
    list_filter = ("status", "session_kind", "week__season")
    search_fields = (
        "week__season__slug",
        "home_season_team__team__name",
        "away_season_team__team__name",
    )
    autocomplete_fields = ("week", "home_season_team", "away_season_team")


@admin.register(ByeAssignment)
class ByeAssignmentAdmin(CarryoverFieldsOnAddAnotherMixin, admin.ModelAdmin):
    carryover_fields = ("week", "season_team", "team_points_awarded")
    list_display = ("week", "season_team", "team_points_awarded")
    list_filter = ("week__season",)
    search_fields = (
        "week__season__slug",
        "season_team__team__name",
    )
    autocomplete_fields = ("week", "season_team")
