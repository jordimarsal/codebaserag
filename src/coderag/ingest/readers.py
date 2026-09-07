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
def load_gitignore(repo_root: Path) -> "pathspec.PathSpec | None":  # type: ignore[type-arg]
    gitignore = Path(repo_root) / ".gitignore"
    if not gitignore.is_file():
        return None
    with gitignore.open(encoding="utf-8") as handle:
        return pathspec.PathSpec.from_lines("gitwildmatch", handle.readlines())


# region is_ignored
def is_ignored(
    path: Path, repo_root: Path, spec: "pathspec.PathSpec | None"  # type: ignore[type-arg]
) -> bool:
    relative = Path(path).resolve().relative_to(Path(repo_root).resolve())
    if any(part == ".git" for part in relative.parts):
        return True
    return spec is not None and spec.match_file(relative.as_posix())


# region discover_files
def discover_files(repo: Path, extensions: frozenset[str] = DEFAULT_EXTENSIONS) -> list[Path]:
    repo_root = Path(repo)
    spec = load_gitignore(repo_root)
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
