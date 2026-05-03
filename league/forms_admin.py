# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

from django import forms


class RoundRobinScheduleForm(forms.Form):
    """Options for generating weeks, matches, byes, and table numbers."""

    cycles = forms.IntegerField(
        min_value=1,
        max_value=30,
        initial=1,
        help_text=(
            "Number of full round-robin passes (everyone plays everyone that many "
            "times). Even cycles swap home/away relative to odd cycles."
        ),
    )
    clear_existing = forms.BooleanField(
        required=False,
        initial=False,
        help_text=(
            "Delete all existing weeks for this season (and their matches/byes) first."
        ),
    )
    max_weeks = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=53,
        help_text=(
            "Optional cap on Thursday round rows (1–53). Uses enough round-robin "
            "cycles to cover this many weeks, then stops mid-rotation if the cap is "
            "hit early. Leave blank to schedule exactly the number of weeks implied "
            "by Cycles alone."
        ),
    )
