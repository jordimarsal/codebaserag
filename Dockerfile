# The image installs the dependency closure from requirements.lock, the
# hash-pinned export of uv.lock (audit finding
# dockerfile-pip-install-unbound-lowerbounds-unused-lockfile: pip used to
# resolve live from PyPI with >= lower bounds while the lockfile was consumed
# by no install path). Regenerate with:
#
#   uv export --format requirements-txt --all-extras --no-emit-project -o requirements.lock
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependency layer first: pinned, hash-verified, and independent of app code.
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

# Application layer (project itself, no deps: everything came from the lock).
COPY pyproject.toml README.md ./
COPY src ./src
COPY evals ./evals
RUN pip install --no-deps .

# Never serve as root: the workload only needs to read /repo and talk to the
# DB/embedder (audit hardening: image had no USER directive).
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# Index the mounted codebase, then serve the API.
CMD ["sh", "-c", "coderag ingest /repo && uvicorn coderag.api.app:app_factory --factory --host 0.0.0.0 --port 8000"]
