# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

"""
Round-robin schedule construction and fair table assignment.

**Mental model:** a standard circle / Berger rotation suggests *who should meet
whom and in what order*; it is sequencing guidance, not a rigid “this must all
happen in one calendar sitting.” The hall has ``LEAGUE_TABLE_COUNT`` tables, so
each Thursday anchor runs at most that many head-to-head games. Pairings that
do not fit that week simply **continue on the next available Thursday** until
every real pairing in the rotation has a ``ScheduledMatch``—whether the tail
lands in week 13, 14, or later is an outcome, not a separate “carryover”
concept.

**Bye / idle:** teams not on a table that anchor get ``ByeAssignment`` rows
(plus ``get_or_create`` when the same anchor already had byes). Think of idle
as smoothing the week: like a fictitious opponent that never occupies a table
and whose “record” we do not track—only real teams and matches matter.

**Tail of the rotation:** extra ``WeekPlan`` steps after the classical circle
rows place the remaining pairings (still at most ``max_m`` disjoint matches per
step). Those are ``primary_thursday`` except when the **last** tail step is a
single pairing: that row is ``makeup_same_week`` on the same ``Week`` as the
prior tail step (same calendar week as that Thursday block).

**Cycles:** each cycle runs one full single round-robin (all ``C(n,2)`` pairings).
Even-numbered cycles keep circle home sides; odd cycles swap home/away on every
pairing.

**Tables:** greedy permutation per plan step to spread table usage (not optimal).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from itertools import permutations
from typing import TYPE_CHECKING, Any

from django.db import transaction

from league.constants import LEAGUE_TABLE_COUNT

if TYPE_CHECKING:
    from league.models import Season, SeasonTeam


@dataclass(frozen=True)
class WeekPlan:
    """One Thursday anchor: table matches plus indices of real teams idle (bye)."""

    matches: tuple[tuple[int, int], ...]  # (home_idx, away_idx)
    bye_team_indices: tuple[int, ...]


def _classical_rounds(team_count: int) -> list[list[tuple[int, int]]]:
    """Circle rounds: each inner list is that round's pairings (real teams only)."""
    if team_count < 2:
        msg = "Need at least two season teams for a schedule."
        raise ValueError(msg)

    indices = list(range(team_count))
    if team_count % 2 == 1:
        teams: list[int | None] = indices + [None]
    else:
        teams = list(indices)
    n = len(teams)
    n_rounds = n - 1
    half = n // 2
    rounds: list[list[tuple[int, int]]] = []
    for _ in range(n_rounds):
        pairs: list[tuple[int, int]] = []
        for i in range(half):
            a, b = teams[i], teams[n - 1 - i]
            if a is None or b is None:
                continue
            pairs.append((a, b))
        rounds.append(pairs)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
    return rounds


def _spill_pending_pairings_into_plans(
    pending: list[tuple[int, int]],
    team_count: int,
    max_m: int,
) -> list[WeekPlan]:
    """Drain ``pending`` into ``WeekPlan`` rows (cap ``max_m`` matches per row)."""
    plans: list[WeekPlan] = []
    while pending:
        week_matches: list[tuple[int, int]] = []
        used: set[int] = set()
        i = 0
        while i < len(pending) and len(week_matches) < max_m:
            a, b = pending[i]
            if a not in used and b not in used:
                week_matches.append((a, b))
                used.add(a)
                used.add(b)
                pending.pop(i)
            else:
                i += 1
        if not week_matches:
            a, b = pending.pop(0)
            week_matches.append((a, b))
            used.update((a, b))
        byes = tuple(t for t in range(team_count) if t not in used)
        plans.append(WeekPlan(matches=tuple(week_matches), bye_team_indices=byes))
    return plans


def _one_cycle_week_plans(team_count: int, max_m: int) -> list[WeekPlan]:
    """One full single RR: circle anchors, then pending pairings on later anchors."""
    if max_m < 1:
        msg = "max_matches_per_week must be at least 1"
        raise ValueError(msg)

    rounds = _classical_rounds(team_count)
    pending: list[tuple[int, int]] = []
    plans: list[WeekPlan] = []
    for rp in rounds:
        if not rp:
            continue
        matches = tuple(rp[:max_m])
        pending.extend(rp[max_m:])
        playing: set[int] = set()
        for h, a in matches:
            playing.add(h)
            playing.add(a)
        byes = tuple(i for i in range(team_count) if i not in playing)
        plans.append(WeekPlan(matches=matches, bye_team_indices=byes))
    plans.extend(_spill_pending_pairings_into_plans(pending, team_count, max_m))
    return plans


def _swap_home_away_weeks(weeks: list[WeekPlan]) -> list[WeekPlan]:
    return [
        WeekPlan(
            matches=tuple((a, h) for (h, a) in w.matches),
            bye_team_indices=w.bye_team_indices,
        )
        for w in weeks
    ]


def build_week_plans(
    team_count: int,
    *,
    cycles: int,
    max_matches_per_week: int | None = None,
) -> list[WeekPlan]:
    """
    Build ``WeekPlan`` rows for ``cycles`` full single round-robins (see module
    docstring). ``max_matches_per_week`` defaults to ``LEAGUE_TABLE_COUNT``.
    """
    if cycles < 1:
        msg = "cycles must be at least 1"
        raise ValueError(msg)
    if max_matches_per_week is not None:
        max_m = max_matches_per_week
    else:
        max_m = LEAGUE_TABLE_COUNT
    one = _one_cycle_week_plans(team_count, max_m)
    out: list[WeekPlan] = []
    for c in range(cycles):
        block = one if c % 2 == 0 else _swap_home_away_weeks(one)
        out.extend(block)
    return out


def _persisted_weeks_from_prototype(one: list[WeekPlan], classical: int) -> int:
    """``Week`` rows per cycle; singleton last tail step shares the prior anchor."""
    f = len(one) - classical
    if f == 0:
        return classical
    if len(one[-1].matches) == 1 and f >= 2:
        return classical + f - 1
    return classical + f


def _persisted_weeks_per_cycle(team_count: int, max_m: int) -> int:
    """``Week`` rows per cycle (see module docstring)."""
    classical = len(_classical_rounds(team_count))
    one = _one_cycle_week_plans(team_count, max_m)
    return _persisted_weeks_from_prototype(one, classical)


def _tail_plan_week_in_cycle(
    tail_idx: int,
    *,
    classical: int,
    tail_plan_count: int,
    last_plan_is_singleton: bool,
) -> int:
    """1-based week number within a cycle for rotation-tail plan ``tail_idx``."""
    if last_plan_is_singleton and tail_plan_count >= 2:
        if tail_idx < tail_plan_count - 1:
            return classical + 1 + tail_idx
        return classical + tail_plan_count - 1
    return classical + 1 + tail_idx


def schedule_weeks_per_single_cycle(
    team_count: int,
    *,
    max_matches_per_week: int | None = None,
) -> int:
    """Persisted ``Week`` rows for one full single round-robin."""
    if max_matches_per_week is not None:
        max_m = max_matches_per_week
    else:
        max_m = LEAGUE_TABLE_COUNT
    return _persisted_weeks_per_cycle(team_count, max_m)


def _table_imbalance_cost(
    counts: list[dict[int, int]],
    n_tables: int,
) -> float:
    """Lower is better: sum over teams of sum_table (count - ideal)^2."""
    cost = 0.0
    for row in counts:
        games = sum(row.values())
        if games == 0:
            continue
        ideal = games / n_tables
        for t in range(1, n_tables + 1):
            v = row.get(t, 0)
            d = v - ideal
            cost += d * d
    return cost


def assign_tables_greedy(
    weeks: list[WeekPlan],
    team_count: int,
    *,
    n_tables: int = LEAGUE_TABLE_COUNT,
) -> list[list[tuple[int, int, int]]]:
    """
    Return per-week list of ``(home_idx, away_idx, table_number)``.

    Greedy week order: for each week try every permutation of tables ``1..k``
    (``k`` = match count) and keep the assignment minimizing running imbalance cost.
    """
    counts: list[dict[int, int]] = [{} for _ in range(team_count)]
    result: list[list[tuple[int, int, int]]] = []
    for week in weeks:
        k = len(week.matches)
        if k == 0:
            result.append([])
            continue
        if k > n_tables:
            msg = f"Internal error: {k} matches in one week exceed {n_tables} tables."
            raise ValueError(msg)
        best_perm: tuple[int, ...] | None = None
        best_cost: float | None = None
        for perm in permutations(range(1, k + 1), k):
            trial = [dict(r) for r in counts]
            for (hi, ai), tbl in zip(week.matches, perm, strict=True):
                for idx in (hi, ai):
                    row = trial[idx]
                    row[tbl] = row.get(tbl, 0) + 1
            trial_cost = _table_imbalance_cost(trial, n_tables)
            if best_cost is None or trial_cost < best_cost:
                best_cost = trial_cost
                best_perm = perm
        if best_perm is None:
            msg = "Internal error: no table assignment permutation found."
            raise ValueError(msg)
        week_rows: list[tuple[int, int, int]] = []
        for (hi, ai), tbl in zip(week.matches, best_perm, strict=True):
            week_rows.append((hi, ai, tbl))
            for idx in (hi, ai):
                row = counts[idx]
                row[tbl] = row.get(tbl, 0) + 1
        result.append(week_rows)
    return result


@transaction.atomic
def replace_season_schedule_from_round_robin(
    season: Season,
    season_teams: list[SeasonTeam],
    *,
    cycles: int,
    clear_existing: bool,
    week_start_anchor: datetime.date | None = None,
    max_matches_per_week: int | None = None,
    max_weeks: int | None = None,
) -> dict[str, Any]:
    """
    Delete existing weeks (and cascaded matches/byes) if ``clear_existing``,
    then create ``Week``, ``ScheduledMatch``, and ``ByeAssignment`` rows.
    Rotation-tail plans are ``primary_thursday`` except a **single** pairing in
    the last tail step, stored as ``makeup_same_week`` on that step's Thursday
    ``Week`` (see module docstring).

    ``max_weeks`` caps how many Thursday ``Week`` rows are created. Enough
    round-robin cycles are built to cover that many anchors; assignment stops
    when the next plan would land past ``max_weeks`` (season may end
    mid-rotation). Leave ``max_weeks`` unset to use ``cycles`` only.

    ``season_teams`` order is preserved (stable sort by team name recommended).
    """
    from league.models import ByeAssignment, ScheduledMatch, Week

    n = len(season_teams)
    if n < 2:
        msg = "Add at least two season teams before generating a schedule."
        raise ValueError(msg)

    if clear_existing:
        season.weeks.all().delete()

    if season.weeks.exists():
        msg = (
            "This season already has weeks. Check 'clear existing weeks' to replace, "
            "or delete weeks manually."
        )
        raise ValueError(msg)

    if max_weeks is not None and (max_weeks < 1 or max_weeks >= 54):
        msg = "max_weeks must be between 1 and 53 inclusive when set."
        raise ValueError(msg)

    if max_matches_per_week is not None:
        max_m = max_matches_per_week
    else:
        max_m = LEAGUE_TABLE_COUNT

    classical_count = len(_classical_rounds(n))
    one_prototype = _one_cycle_week_plans(n, max_m)
    one_cycle_len = len(one_prototype)
    tail_plan_count = one_cycle_len - classical_count
    last_tail_singleton = tail_plan_count > 0 and len(one_prototype[-1].matches) == 1
    weeks_per_cycle = _persisted_weeks_from_prototype(
        one_prototype,
        classical_count,
    )

    if max_weeks is None:
        cycles_used = cycles
        total_weeks = cycles * weeks_per_cycle
    else:
        min_cycles = (max_weeks + weeks_per_cycle - 1) // weeks_per_cycle
        cycles_used = max(cycles, min_cycles)
        total_weeks = max_weeks

    plans = build_week_plans(
        n,
        cycles=cycles_used,
        max_matches_per_week=max_matches_per_week,
    )
    tabled = assign_tables_greedy(plans, n)
    bye_points = 3
    if isinstance(season.rules, dict):
        bye_points = int(season.rules.get("bye_team_points_default", 3))

    anchor = week_start_anchor or season.start_date
    st_by_idx = list(season_teams)
    week_by_number: dict[int, Week] = {}
    for wn in range(1, total_weeks + 1):
        wk = Week.objects.create(
            season=season,
            number=wn,
            calendar_date=anchor + datetime.timedelta(weeks=wn - 1),
        )
        week_by_number[wn] = wk

    sk = ScheduledMatch.SessionKind
    for pi, (plan, match_rows) in enumerate(zip(plans, tabled, strict=True)):
        cycle = pi // one_cycle_len
        within = pi % one_cycle_len
        week_offset = cycle * weeks_per_cycle
        if within < classical_count:
            week_num = week_offset + within + 1
        else:
            tail_idx = within - classical_count
            week_in_cycle = _tail_plan_week_in_cycle(
                tail_idx,
                classical=classical_count,
                tail_plan_count=tail_plan_count,
                last_plan_is_singleton=last_tail_singleton,
            )
            week_num = week_offset + week_in_cycle
        if max_weeks is not None and week_num > max_weeks:
            break
        if within < classical_count:
            wk = week_by_number[week_num]
            for hi, ai, tbl in match_rows:
                ScheduledMatch.objects.create(
                    week=wk,
                    home_season_team=st_by_idx[hi],
                    away_season_team=st_by_idx[ai],
                    table_number=tbl,
                    session_kind=sk.PRIMARY_THURSDAY,
                )
            for bi in plan.bye_team_indices:
                ByeAssignment.objects.get_or_create(
                    week=wk,
                    season_team=st_by_idx[bi],
                    defaults={"team_points_awarded": bye_points},
                )
        else:
            wk = week_by_number[week_num]
            logical_round = pi + 1
            is_singleton_tail = (
                tail_idx == tail_plan_count - 1
                and len(plan.matches) == 1
                and tail_plan_count >= 1
            )
            if is_singleton_tail:
                for hi, ai, tbl in match_rows:
                    ScheduledMatch.objects.create(
                        week=wk,
                        home_season_team=st_by_idx[hi],
                        away_season_team=st_by_idx[ai],
                        table_number=tbl,
                        counts_as_round=logical_round,
                        session_kind=sk.MAKEUP_SAME_WEEK,
                    )
            else:
                for hi, ai, tbl in match_rows:
                    ScheduledMatch.objects.create(
                        week=wk,
                        home_season_team=st_by_idx[hi],
                        away_season_team=st_by_idx[ai],
                        table_number=tbl,
                        session_kind=sk.PRIMARY_THURSDAY,
                    )
            for bi in plan.bye_team_indices:
                ByeAssignment.objects.get_or_create(
                    week=wk,
                    season_team=st_by_idx[bi],
                    defaults={"team_points_awarded": bye_points},
                )

    return {
        "weeks": total_weeks,
        "cycles": cycles,
        "cycles_used": cycles_used,
        "teams": n,
        "bye_points_default": bye_points,
        "weeks_per_cycle": weeks_per_cycle,
        "max_weeks": max_weeks,
    }


def ordered_season_teams(season: Season) -> list[SeasonTeam]:
    """Stable order for reproducible schedules (team name, then pk)."""
    return list(
        season.season_teams.select_related("team").order_by(
            "team__name",
            "pk",
        ),
    )
