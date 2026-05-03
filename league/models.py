# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

"""
Domain models for the in-house billiards league.

``Season.rules`` is a JSON object for format-specific knobs that change over time
without schema churn. Documented keys (all optional; code should default safely):

- ``bye_team_points_default`` (int): team points awarded per bye week when not
  overridden on ``ByeAssignment``.
- ``ghost_racks_per_team_season`` (int): typical cap on extra "ghost" racks per
  team per season (fall league).
- ``lineup_size`` (int): players submitted per match night (e.g. 4).
- ``team_roster_min`` / ``team_roster_max`` (int): allowed roster size for the
  format (e.g. 4–6 for fall).
"""

from __future__ import annotations

import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from .constants import LEAGUE_TABLE_COUNT


class Season(models.Model):
    """One league season (e.g. fall Sept–Mar, summer Apr–Aug)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    format = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Discipline code, e.g. fall_8ball, summer_scotch_doubles.",
    )
    rules = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    class Meta:
        ordering = ["-start_date", "slug"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="season_end_after_start",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Team(models.Model):
    """Stable team identity across seasons."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class SeasonTeam(models.Model):
    """A team enrolled in a specific season (supports mid-season join/leave)."""

    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        related_name="season_teams",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="season_teams",
    )
    first_week_number = models.PositiveIntegerField(
        default=1,
        help_text="First week this team participates (1-based within the season).",
    )
    last_week_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Last participating week; blank means through final week.",
    )

    class Meta:
        ordering = ["season", "team__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["season", "team"],
                name="season_team_unique_per_season",
            ),
            models.CheckConstraint(
                condition=Q(last_week_number__isnull=True)
                | Q(last_week_number__gte=F("first_week_number")),
                name="season_team_last_week_gte_first",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.team} ({self.season.slug})"


class Player(models.Model):
    """A person who may appear on season rosters."""

    display_name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True, null=True, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["display_name"]

    def __str__(self) -> str:
        return self.display_name


class SeasonRosterEntry(models.Model):
    """Time-bounded roster slot: which player was on which season team when."""

    season_team = models.ForeignKey(
        SeasonTeam,
        on_delete=models.CASCADE,
        related_name="roster_entries",
    )
    player = models.ForeignKey(
        Player,
        on_delete=models.PROTECT,
        related_name="roster_entries",
    )
    effective_from = models.DateField()
    effective_to = models.DateField(
        null=True,
        blank=True,
        help_text="Inclusive end date; blank means still active.",
    )

    class Meta:
        ordering = ["season_team", "effective_from", "player"]
        indexes = [
            models.Index(fields=["season_team", "effective_from"]),
            models.Index(fields=["player", "effective_from"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(effective_to__isnull=True)
                | Q(effective_to__gte=F("effective_from")),
                name="roster_effective_to_gte_from",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.player} on {self.season_team}"


class Week(models.Model):
    """
    League **round** anchor: primary session night (typically Thursday) and sequence.

    ``number`` is the rotation / schedule index. ``calendar_date`` is the canonical
    league night for that round (usually Thursday). Make-up matches that count
    toward a different standings round but share this round's calendar week are
    stored on ``ScheduledMatch`` (``counts_as_round``, ``played_on``, ``session_kind``).
    """

    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        related_name="weeks",
    )
    number = models.PositiveIntegerField(
        help_text="Round index (1-based) within the season.",
    )
    calendar_date = models.DateField(
        null=True,
        blank=True,
        help_text="Primary league session date (typically Thursday).",
    )

    class Meta:
        ordering = ["season", "number"]
        verbose_name = "Round"
        verbose_name_plural = "Rounds"
        constraints = [
            models.UniqueConstraint(
                fields=["season", "number"],
                name="week_unique_number_per_season",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.season.slug} round {self.number}"


class ScheduledMatch(models.Model):
    """Head-to-head match between two season teams, tied to a round anchor week."""

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        POSTPONED = "postponed", "Postponed"

    class SessionKind(models.TextChoices):
        PRIMARY_THURSDAY = "primary_thursday", "Primary league night (Thursday)"
        MAKEUP_SAME_WEEK = (
            "makeup_same_week",
            "Make-up: same calendar week, non-Thursday (by agreement)",
        )

    week = models.ForeignKey(
        Week,
        on_delete=models.CASCADE,
        related_name="matches",
        help_text=(
            "Round row whose calendar week anchors this match (primary Thursday night)."
        ),
    )
    home_season_team = models.ForeignKey(
        SeasonTeam,
        on_delete=models.PROTECT,
        related_name="home_matches",
    )
    away_season_team = models.ForeignKey(
        SeasonTeam,
        on_delete=models.PROTECT,
        related_name="away_matches",
    )
    table_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text=f"Table 1–{LEAGUE_TABLE_COUNT} when assigned.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
        db_index=True,
    )
    counts_as_round = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Standings / rotation round this result counts toward when it differs "
            "from week.number (e.g. a pairing scored as round 14 but anchored to "
            "round 13's calendar week)."
        ),
    )
    played_on = models.DateField(
        null=True,
        blank=True,
        help_text="Actual calendar date of play; blank means primary session night.",
    )
    session_kind = models.CharField(
        max_length=24,
        choices=SessionKind.choices,
        default=SessionKind.PRIMARY_THURSDAY,
        db_index=True,
    )

    class Meta:
        ordering = ["week", "home_season_team_id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(table_number__isnull=True)
                | (
                    Q(table_number__gte=1)
                    & Q(table_number__lte=LEAGUE_TABLE_COUNT)
                ),
                name="scheduled_match_table_number_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.home_season_team} vs {self.away_season_team} ({self.week})"

    @property
    def effective_round_number(self) -> int:
        """Standings round index (explicit or same as the anchor round)."""
        if self.counts_as_round is not None:
            return self.counts_as_round
        return self.week.number

    def clean(self) -> None:
        if self.week_id is None or self.home_season_team_id is None:
            return
        if self.away_season_team_id is None:
            return
        season = self.week.season_id
        if self.home_season_team_id == self.away_season_team_id:
            raise ValidationError("Home and away must be different season teams.")
        if self.home_season_team.season_id != season:
            raise ValidationError("Home team must belong to the match week's season.")
        if self.away_season_team.season_id != season:
            raise ValidationError("Away team must belong to the match week's season.")
        if self.table_number is not None and not (
            1 <= self.table_number <= LEAGUE_TABLE_COUNT
        ):
            raise ValidationError(
                {
                    "table_number": (
                        f"Must be between 1 and {LEAGUE_TABLE_COUNT} for league play."
                    ),
                }
            )
        anchor = self.week.calendar_date
        def _iso_year_week(d: datetime.date) -> tuple[int, int]:
            ic = d.isocalendar()
            return (ic.year, ic.week)

        if (
            self.session_kind == self.SessionKind.MAKEUP_SAME_WEEK
            and self.played_on is not None
            and anchor is not None
        ):
            if _iso_year_week(self.played_on) != _iso_year_week(anchor):
                raise ValidationError(
                    {
                        "played_on": (
                            "Make-up same-week matches must fall in the same ISO "
                            "calendar week as the anchor round's primary session date."
                        ),
                    }
                )


class ByeAssignment(models.Model):
    """Bye for a season team on a week (points may differ from season default)."""

    week = models.ForeignKey(
        Week,
        on_delete=models.CASCADE,
        related_name="bye_assignments",
    )
    season_team = models.ForeignKey(
        SeasonTeam,
        on_delete=models.CASCADE,
        related_name="bye_assignments",
    )
    team_points_awarded = models.PositiveSmallIntegerField(
        default=3,
        help_text="League team points for this bye; override when rules differ.",
    )

    class Meta:
        ordering = ["week", "season_team_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["week", "season_team"],
                name="bye_unique_team_per_week",
            ),
        ]

    def __str__(self) -> str:
        return f"Bye {self.season_team} ({self.week})"

    def clean(self) -> None:
        if self.week_id is None or self.season_team_id is None:
            return
        if self.season_team.season_id != self.week.season_id:
            raise ValidationError("Season team must belong to the bye week's season.")
