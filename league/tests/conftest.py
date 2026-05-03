# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

import pytest

from league.testing.sandbox import create_minimal_season_graph


@pytest.fixture
def minimal_season_graph(db):
    """Disposable season + two teams + week 1 for model tests."""
    return create_minimal_season_graph("pytest-minimal-graph")
