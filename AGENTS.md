<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Copyright (C) 2026 Biddeford Eagles League contributors -->

# Agent instructions — Biddeford Eagles League

This file is the **canonical guide** for AI coding agents (Cursor, Claude, ChatGPT, CI bots) working on this repository. Prefer it over guessing stack or conventions.

## Project purpose

**Billiards league** site for the Eagles in-house league: record stats, results, and standings (print-friendly). Stretch goals: public player-facing pages, admin for scores and league maintenance, possible future mobile client. **No commercial use**; self-hosted (e.g. AWS, Cloudflare edge + origin). **Security matters** even without revenue pressure.

## Tech stack (non-negotiable defaults)

| Layer | Choice |
|--------|--------|
| Language | **Python** only for application code |
| UI | **htmx** + server-rendered HTML; **Pico CSS** (or similarly lightweight CSS) unless the human asks otherwise |
| JS | **Do not** introduce React/Vue/SPA build pipelines or heavy client frameworks. Vanilla JS only if strictly necessary and minimal |
| Web framework | **Django** (ORM is a first-class learning goal — use it for models, migrations, relationships, and most queries) |
| Packaging / runs | **uv** (`pyproject.toml`, `uv.lock` committed). Use `uv run …` for CLI tools and tests |
| Runtime / deploy | **Docker** as the primary way to run the app consistently; avoid assuming a hand-maintained Python stack on the host |
| Database | **PostgreSQL** in production-oriented setups; SQLite acceptable for early local/dev if documented |

## How to run things

Read **`README.md`** for exact commands (`migrate`, `runserver`, `docker compose`, tests). Target patterns:

- Install deps: `uv sync` (locked: `uv sync --frozen` in CI/Docker).
- Tests: `uv run pytest` (pytest-django configured in `pyproject.toml`).
- Docker Compose runs **web** (Gunicorn) + **Postgres**; local `runserver` uses SQLite unless `POSTGRES_HOST` is set.

## Engineering practices

- **TDD**: Encourage tests for domain rules (standings, scoring, permissions) and critical views/forms. Full coverage is not required; **correctness where mistakes hurt** is.
- **Small changes**: Prefer focused PR-sized diffs. **Branch by abstraction** for risky refactors (e.g. swap standings implementation behind a narrow interface).
- **Feature flags**: Start simple (`settings` / env vars). Upgrade to a flag library only when needed.
- **SQL**: The human is SQL-strong. Use the **Django ORM** by default; use **raw SQL / views / annotations** when the ORM obscures intent or performance.

## Django & ORM expectations

- Models in `models.py` (or split model modules) with clear `ForeignKey` / `ManyToMany` / constraints.
- Migrations committed; never hand-edit applied migration history without explicit human direction.
- Use `select_related` / `prefetch_related` when traversing relations in views.
- **Django Admin** is a feature, not technical debt — use it for internal operations unless the human specifies custom screens.

## Security baseline (always)

- **Never** commit secrets, API keys, or production `SECRET_KEY`. Use environment variables or a secret manager.
- Production-minded settings: `DEBUG=False`, restricted `ALLOWED_HOSTS`, secure cookies behind HTTPS, CSRF enabled for session-backed flows.
- Dependencies pinned via lockfile; flag outdated packages with known CVEs when you touch deps.
- Auth-protect admin and privileged routes; prefer framework defaults over custom crypto.

## Files and layout

Follow whatever structure exists after scaffolding. Typical Django expectations:

- Apps under project-specific packages (e.g. `league/`, `core/`).
- Templates for partials htmx swaps as well as full pages.
- Static: Pico + minimal custom CSS; no bundler unless explicitly added later.

## Licensing

- Canonical text: **`LICENSE`** (GNU Affero General Public License version 3).
- SPDX: **`AGPL-3.0-or-later`** — use the same per-file `SPDX-License-Identifier` and copyright notice pattern as existing `*.py`, `pyproject.toml`, `README.md`, `AGENTS.md`, `CLAUDE.md`, and `.cursor/rules/*.mdc` when adding new first-party source or substantive prose.

## Documentation

- **Do not** add large unsolicited markdown docs. Update `README.md` when run/deploy steps change meaningfully.

## When uncertain

Prefer **asking one focused question** over inventing stack choices that contradict this file.
