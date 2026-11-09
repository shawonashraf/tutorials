"""Turn the repo's notebook folders into Sphinx sources for the tutorial site."""

import argparse
import json
import re
import shutil
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path

SKIP_DIRS = {"website"}
# Generated pages have no file in the repo, so drop the right sidebar
# (its "Edit on GitHub" link would 404).
GENERATED_PAGE = "---\nhtml_theme.sidebar_secondary.remove: true\n---\n\n"


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


def first_post(topics: list[Topic]) -> Path:
    for t in topics:
        if t.posts:
            return t.posts[0]
        try:
            return first_post(t.subtopics)
        except SiteError:
            continue
    raise SiteError("no notebooks found")


def _copy_post(repo: Path, out: Path, post: Path) -> None:
    nb = json.loads((repo / post).read_text())
    title = {"cell_type": "markdown", "metadata": {}, "source": [f"# {pretty_name(post.stem)}"]}
    if nb.get("nbformat", 4) > 4 or nb.get("nbformat_minor", 0) >= 5:
        title["id"] = "site-title"
    nb["cells"].insert(0, title)
    dest = out / post
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(nb, indent=1))


def _write_topic(repo: Path, out: Path, topic: Topic) -> None:
    for post in topic.posts:
        _copy_post(repo, out, post)
    for sub in topic.subtopics:
        _write_topic(repo, out, sub)
    entries = [p.stem for p in topic.posts] + [f"{s.dir.name}/index" for s in topic.subtopics]
    (out / topic.dir / "index.md").write_text(
        GENERATED_PAGE
        + f"# {pretty_name(topic.dir.name)}\n\n"
        "```{toctree}\n:maxdepth: 1\n:titlesonly:\n\n" + "\n".join(entries) + "\n```\n"
    )


def write_sources(repo: Path, out: Path) -> None:
    repo, out = repo.resolve(), out.resolve()
    if repo == out or repo.is_relative_to(out):
        raise SiteError(f"output {out} would contain the repo; refusing to delete it")
    topics = find_topics(repo)
    start = first_post(topics).with_suffix(".html").as_posix()
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    for topic in topics:
        _write_topic(repo, out, topic)
    (out / "index.md").write_text(
        GENERATED_PAGE
        + "# Tutorials\n\n"
        f'```{{raw}} html\n<meta http-equiv="refresh" content="0; url={start}">\n```\n\n'
        "```{toctree}\n:hidden:\n\n"
        + "\n".join(f"{t.dir.as_posix()}/index" for t in topics)
        + "\n```\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args(argv)
    try:
        write_sources(args.repo, args.out)
    except SiteError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
