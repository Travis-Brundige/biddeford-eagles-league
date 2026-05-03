# Astral uv on Docker Hardened Images (DHI) — no /bin/sh; exec-form RUN + Python ENTRYPOINT.
# Pin by digest in production: https://github.com/orgs/astral-sh/packages/container/package/uv
FROM ghcr.io/astral-sh/uv:python3.14-dhi

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    PATH="/app/.venv/bin:$PATH"

# 1) Dependencies only — cache hits when application code changes but lockfile does not.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    ["uv", "sync", "--frozen", "--no-dev", "--no-install-project"]

# 2) Application + install project into the venv (cheap when step 1 was cached).
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    ["uv", "sync", "--frozen", "--no-dev"]

EXPOSE 8000
ENTRYPOINT ["/app/.venv/bin/python", "/app/docker/entrypoint.py"]
CMD []
