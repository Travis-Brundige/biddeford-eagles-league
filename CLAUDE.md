<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Copyright (C) 2026 Biddeford Eagles League contributors -->

# Claude (project)

**Full agent context lives in [`AGENTS.md`](./AGENTS.md).** Read that first for stack, security, Django/htmx/uv/Docker rules, and workflow expectations.

## Quick reminders for this repo

- **Python + Django + ORM**; **htmx + Pico**; **uv** + **Docker** — not a JavaScript SPA stack.
- Treat **AGENTS.md** as authoritative if anything conflicts with a generic Claude default.
- For multi-step refactors, prefer **small commits** and **tests** around league rules and auth.

If `AGENTS.md` is missing, ask the maintainer before assuming stack changes.
