<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Copyright (C) 2026 Biddeford Eagles League contributors -->

# Biddeford Eagles League

Web app for a charity **billiards league**: record stats, publish results, and print standings. Stretch goals include a fuller public site, richer admin for scores and league maintenance, and possibly a mobile client for live entry.

## Stack

- **Django** (including the **ORM** for models and migrations)
- **htmx** + **Pico CSS** — server-rendered HTML, no SPA framework
- **uv** for Python dependencies and commands
- **Docker** (and Compose) for consistent local and deployed runs — no hand-maintained Python on the server

## Prerequisites

- [uv](https://docs.astral.sh/uv/)
- [Docker](https://docs.docker.com/get-docker/) (and Docker Compose)

## Getting started

The Django app, `compose.yaml`, and exact `uv run` / `docker compose` commands will land as the project is scaffolded. Until then:

- Clone the repo.
- Read **[`AGENTS.md`](./AGENTS.md)** if you are an AI agent or setting up automation — it is the canonical project contract.

Once scaffolding exists, this section will describe `uv sync`, running tests with `uv run pytest`, and starting the stack with Docker Compose.

## Development approach

- **Tests** where correctness matters (standings, scoring, permissions).
- **Small, reviewable changes**; optional **feature flags** (env/settings first).
- **Security**: no secrets in git; production-style Django settings when deployed.

Details for tools and agents: **[`AGENTS.md`](./AGENTS.md)**. Cursor-specific rules: **`.cursor/rules/`**.

## Other agent entrypoints

| File | Use |
|------|-----|
| [`AGENTS.md`](./AGENTS.md) | Full instructions for any coding agent |
| [`CLAUDE.md`](./CLAUDE.md) | Short pointer for Claude-oriented tools; defers to `AGENTS.md` |

## License

This project is licensed under the **GNU Affero General Public License v3.0 or later** — see [`LICENSE`](./LICENSE). SPDX: `AGPL-3.0-or-later`.
