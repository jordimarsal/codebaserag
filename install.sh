#!/bin/sh
# One-line installer for the `coderag` CLI (Linux / macOS).
#
#   curl -LsSf https://raw.githubusercontent.com/jordimarsal/codebaserag/main/install.sh | sh
#
# Installs `uv` if missing (uv fetches Python 3.13 itself), then installs the
# tool in an isolated environment. Extras can be overridden:
#
#   CODERAG_EXTRAS=pgvector,embeddings,llm,qdrant  (default)
#   CODERAG_EXTRAS=""                              (base: memory store + fake LLM only)

set -eu

REPO_URL="git+https://github.com/jordimarsal/codebaserag"
EXTRAS="${CODERAG_EXTRAS-pgvector,embeddings,llm,qdrant}"

# 1. Ensure uv is available.
if ! command -v uv >/dev/null 2>&1; then
    echo "uv not found — installing from https://astral.sh/uv ..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # shellcheck disable=SC1091
    . "$HOME/.local/bin/env" 2>/dev/null || PATH="$HOME/.local/bin:$PATH"
    export PATH
fi

# 2. Install (or update) the tool with the requested extras.
if [ -n "$EXTRAS" ]; then
    PACKAGE="codebaserag[$EXTRAS]"
else
    PACKAGE="codebaserag"
fi

uv tool install --reinstall --from "$PACKAGE @ $REPO_URL" codebaserag

# 3. Report.
if command -v coderag >/dev/null 2>&1; then
    echo "coderag $(coderag version) installed. Try: coderag --help"
else
    echo "Installed. Make sure ~/.local/bin is on your PATH to use 'coderag'."
fi
