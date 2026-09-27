import logging
from pathlib import Path

import pathspec

from coderag.types import Language

logger = logging.getLogger("coderag.ingest")

EXT_TO_LANGUAGE: dict[str, Language] = {
    ".py": Language.PYTHON,
    ".md": Language.MARKDOWN,
    ".toml": Language.TOML,
    ".yaml": Language.YAML,
    ".yml": Language.YAML,
}

DEFAULT_EXTENSIONS: frozenset[str] = frozenset(EXT_TO_LANGUAGE)


# region language_for
def language_for(path: Path) -> Language:
    return EXT_TO_LANGUAGE.get(path.suffix.lower(), Language.UNKNOWN)


# region load_gitignore
def load_gitignore(repo_root: Path) -> "pathspec.GitIgnoreSpec | None":
    """Root-level ``.gitignore`` as a GitIgnoreSpec.

    GitIgnoreSpec (unlike plain PathSpec) also implements git's rule that a
    negation cannot re-include a file inside an already-excluded directory.
    """
    gitignore = Path(repo_root) / ".gitignore"
    if not gitignore.is_file():
        return None
    with gitignore.open(encoding="utf-8") as handle:
        return pathspec.GitIgnoreSpec.from_lines("gitwildmatch", handle)


# region combined ignore spec
def _read_lines(path: Path) -> list[str]:
    try:
        with path.open(encoding="utf-8") as handle:
            return handle.read().splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("skipping ignore file %s: %s", path, exc)
        return []


def _scoped_pattern(line: str, prefix: str) -> str:
    """Re-anchor a nested ``.gitignore`` pattern under its directory."""
    negate = line.startswith("!")
    body = line[1:] if negate else line
    scoped = prefix + body if body.startswith("/") else f"{prefix}/**/{body}"
    return f"!{scoped}" if negate else scoped


def combined_ignore_spec(repo_root: Path) -> "pathspec.GitIgnoreSpec | None":
    """Combine every git ignore layer that gates the ingest boundary.

    Git honours the root ``.gitignore``, nested ``.gitignore`` files and
    ``.git/info/exclude``; the tool previously read only the root file, so
    files a developer deliberately kept out of version control at any other
    layer were indexed and shipped to the embedder (audit finding
    readers.is_ignored-gitignore-root-only-approximation). Patterns from
    nested files are re-anchored under their directory.
    """
    root = Path(repo_root).resolve()
    lines: list[str] = []
    lines.extend(_read_lines(root / ".gitignore"))
    lines.extend(_read_lines(root / ".git" / "info" / "exclude"))
    for nested in sorted(root.rglob(".gitignore")):
        try:
            rel_dir = nested.parent.resolve().relative_to(root)
        except ValueError:
            continue  # ignore file resolves outside the repo root
        if rel_dir.as_posix() == "." or any(part == ".git" for part in rel_dir.parts):
            continue  # root file handled above; never read inside .git
        for line in _read_lines(nested):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            lines.append(_scoped_pattern(stripped, rel_dir.as_posix()))
    if not lines:
        return None
    return pathspec.GitIgnoreSpec.from_lines("gitwildmatch", lines)


# region is_ignored
def is_ignored(
    path: Path, repo_root: Path, spec: "pathspec.PathSpec | None"  # type: ignore[type-arg]
) -> bool:
    try:
        relative = Path(path).resolve().relative_to(Path(repo_root).resolve())
    except ValueError:
        # Resolves outside the repo root (e.g. a symlink escaping the tree):
        # treat it as ignored so nothing outside the root is ever read and one
        # bad link cannot abort the whole ingest (audit hardening, R11).
        return True
    if any(part == ".git" for part in relative.parts):
        return True
    if spec is None:
        return False
    if spec.match_file(relative.as_posix()):
        return True
    # Git does not descend into ignored directories, so a negation cannot
    # re-include a file whose ancestor directory is excluded; pathspec matches
    # the file path alone, so walk the ancestors here.
    parts = relative.parts
    for i in range(1, len(parts)):
        ancestor = "/".join(parts[:i])
        if spec.match_file(ancestor) or spec.match_file(f"{ancestor}/"):
            return True
    return False


# region discover_files
def discover_files(repo: Path, extensions: frozenset[str] = DEFAULT_EXTENSIONS) -> list[Path]:
    repo_root = Path(repo)
    spec = combined_ignore_spec(repo_root)
    found: list[Path] = []
    for path in sorted(repo_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in extensions:
            continue
        if is_ignored(path, repo_root, spec):
            continue
        found.append(path)
    logger.debug("discovered %d files in %s", len(found), repo_root)
    return found
