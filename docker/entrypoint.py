# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors
"""Container entrypoint: migrate, then exec gunicorn (no shell — DHI-safe)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)

    subprocess.run(
        [sys.executable, str(root / "manage.py"), "migrate", "--noinput"],
        check=True,
    )

    gunicorn = shutil.which("gunicorn")
    if gunicorn is None:
        gunicorn = str(root / ".venv" / "bin" / "gunicorn")
    os.execv(
        gunicorn,
        [
            gunicorn,
            "config.wsgi:application",
            "--bind",
            "0.0.0.0:8000",
            "--workers",
            "2",
        ],
    )


if __name__ == "__main__":
    main()
