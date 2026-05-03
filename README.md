<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Copyright (C) 2026 Biddeford Eagles League contributors -->

# Biddeford Eagles League

Web app for the **Biddeford Eagles in-house billiards league**: record stats, publish results, and print standings. Stretch goals include a fuller public site, richer admin for scores and league maintenance, and possibly a mobile client for live entry.

## Stack

- **Django** (including the **ORM** for models and migrations)
- **htmx** + **Pico CSS** — server-rendered HTML, no SPA framework
- **uv** for Python dependencies and commands
- **Docker** (and Compose) for consistent local and deployed runs — no hand-maintained Python on the server

## Prerequisites

- [uv](https://docs.astral.sh/uv/)
- [Docker](https://docs.docker.com/get-docker/) (and Docker Compose)

## Getting started

### Local (SQLite, development server)

```bash
uv sync
source .venv/bin/activate   # optional; or use `uv run` below
uv run python manage.py migrate
uv run python manage.py runserver
```

Open http://127.0.0.1:8000/ — home page with a small **htmx** fragment demo.

### Local tooling

```bash
uv run ruff check .
uv run pytest
```

**Git hooks (fail before `git push`):** after `uv sync`, run `uv run pre-commit install` once. Each `git commit` then runs the same checks as CI (Ruff, Bandit, pip-audit, Django checks, pytest). Run everything manually with `uv run pre-commit run --all-files`.

### Docker (PostgreSQL + Gunicorn)

The app image uses **`ghcr.io/astral-sh/uv:python3.14-dhi`** (Astral’s uv on **Docker Hardened Images** Python). DHI often has **no shell**, so the image uses **exec-form `RUN`**, **`ENTRYPOINT`** → **`docker/entrypoint.py`** (runs `migrate`, then **`os.execv`** into **gunicorn**), and **`CMD []`**. Pin a digest for reproducible deploys (see `Dockerfile` comments).

```bash
cp .env.example .env   # optional; compose defaults work for a quick try
docker compose up --build
```

The **web** service runs migrations then **Gunicorn** on port **8000**. Postgres uses the `db` service; credentials default to `biddeford` / `biddeford` (override via `.env`).

The **`Dockerfile`** installs dependencies in a separate layer (`uv sync … --no-install-project` on `pyproject.toml` + `uv.lock` only), then copies the rest of the tree and runs a final `uv sync` so **lockfile-only changes** do not invalidate the heavy dependency install when you edit templates or Python.

With **no** `POSTGRES_HOST` set, Django uses **SQLite** (`db.sqlite3`). With `POSTGRES_HOST` set (e.g. to `db` in Compose), Django uses **PostgreSQL** via **psycopg**.

## Development approach

- **Tests** where correctness matters (standings, scoring, permissions).
- **Small, reviewable changes**; optional **feature flags** (env/settings first).
- **Security**: no secrets in git; set a real `SECRET_KEY` and `DEBUG=False` for production; use `ALLOWED_HOSTS` explicitly when not in debug.

Details for tools and agents: **[`AGENTS.md`](./AGENTS.md)**. Cursor-specific rules: **`.cursor/rules/`**.

## Other agent entrypoints

| File | Use |
|------|-----|
| [`AGENTS.md`](./AGENTS.md) | Full instructions for any coding agent |
| [`CLAUDE.md`](./CLAUDE.md) | Short pointer for Claude-oriented tools; defers to `AGENTS.md` |

## License

This project is licensed under the **GNU Affero General Public License v3.0 or later** — see [`LICENSE`](./LICENSE). SPDX: `AGPL-3.0-or-later`.
