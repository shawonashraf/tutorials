"""Turn the repo's notebook folders into Sphinx sources for the tutorial site."""

import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path

SKIP_DIRS = {"website"}


class SiteError(Exception):
    pass


@dataclass
class Topic:
    dir: Path
    posts: list[Path] = field(default_factory=list)
    subtopics: list["Topic"] = field(default_factory=list)


def pretty_name(name: str) -> str:
    words = [w for w in re.split(r"[-_\s]+", name) if w]
    return " ".join(w[0].upper() + w[1:] for w in words)


def _skipped(d: Path) -> bool:
    return d.name.startswith((".", "_")) or d.name in SKIP_DIRS


def _subdirs(d: Path) -> list[Path]:
    return sorted(p for p in d.iterdir() if p.is_dir() and not _skipped(p))


def _topic(repo: Path, d: Path) -> Topic | None:
    posts = [p.relative_to(repo) for p in sorted(d.glob("*.ipynb"))]
    for p in posts:
        if p.stem == "index":
            raise SiteError(f"{p.as_posix()}: 'index' is reserved for topic pages; rename it")
    subtopics = [t for s in _subdirs(d) if (t := _topic(repo, s))]
    if not posts and not subtopics:
        return None
    return Topic(d.relative_to(repo), posts, subtopics)


def find_topics(repo: Path) -> list[Topic]:
    for p in sorted(repo.glob("*.ipynb")):
        warnings.warn(f"{p.name}: notebooks at the repo root have no topic; skipped")
    return [t for d in _subdirs(repo) if (t := _topic(repo, d))]
