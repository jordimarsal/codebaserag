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
#
# Integrity: the installer, the uv bootstrapper and the package source all
# resolve mutable refs by default. Pin them in untrusted contexts (audit
# finding install-sh-curlsh-unpinned-git-main-bootstrap):
#
#   CODERAG_REF=<tag-or-commit>        package source ref (default: main)
#   CODERAG_UV_VERSION=<version>       uv bootstrapper version (default: 0.12.19)

set -eu

REF="${CODERAG_REF-main}"
REPO_URL="git+https://github.com/jordimarsal/codebaserag@${REF}"
EXTRAS="${CODERAG_EXTRAS-pgvector,embeddings,llm,qdrant}"
UV_VERSION="${CODERAG_UV_VERSION-0.12.19}"

if [ "$REF" = "main" ]; then
    echo "WARNING: installing from mutable 'main' with no digest or checksum binding." >&2
    echo "         Pin a reviewed ref instead: CODERAG_REF=<tag-or-commit> $0" >&2
fi

# 1. Ensure uv is available.
if ! command -v uv >/dev/null 2>&1; then
    echo "uv not found — installing uv ${UV_VERSION} from https://astral.sh/uv ..."
    curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | sh
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
