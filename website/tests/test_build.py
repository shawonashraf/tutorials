import json
import re
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from sphinx.cmd.build import build_main

WEBSITE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEBSITE_DIR))

from generate import write_sources  # noqa: E402

POSTS = [
    "alpha/one.ipynb",
    "alpha/two.ipynb",
    "beta-gamma/three.ipynb",
    "beta-gamma/My VAE notes.ipynb",
    "deep/l1/l2/l3/l4/l5/bottom_post.ipynb",
    "alpha/zz_own_h1.ipynb",
]


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("site")
    repo, src, out = root / "repo", root / "src", root / "out"
    for p in POSTS:
        path = repo / p
        path.parent.mkdir(parents=True, exist_ok=True)
        text = "# Own Title\n\n# Another H1" if "own_h1" in p else "## Section\ntext"
        cell = {"cell_type": "markdown", "metadata": {}, "source": [text]}
        path.write_text(json.dumps({"cells": [cell], "metadata": {}, "nbformat": 4, "nbformat_minor": 4}))
    write_sources(repo, src)
    assert build_main(["-q", "-c", str(WEBSITE_DIR), str(src), str(out)]) == 0
    return out


def soup(path: Path) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(), "html.parser")


def test_post_page(site):
    html = soup(site / "alpha/one.html")
    assert html.title.text.startswith("One")
    sidebar = html.select_one(".bd-sidebar-primary").get_text()
    for name in ["Alpha", "Beta Gamma", "Deep", "One", "Two", "Three", "My VAE Notes", "Bottom Post"]:
        assert name in sidebar
    assert "Alpha" not in html.select_one(".bd-header").get_text()
    assert html.find("a", href=re.compile(r"/edit/main/alpha/one\.ipynb$"))


def test_topic_and_root_pages(site):
    assert not soup(site / "alpha/index.html").find("a", href=re.compile("/edit/"))
    assert "url=alpha/one.html" in (site / "index.html").read_text()


def test_topic_page_lists_each_post_once(site):
    links = [a.get_text(strip=True) for a in soup(site / "alpha/index.html").select("article .toctree-wrapper a")]
    assert links == ["One", "Two", "Zz Own H1"]


def test_ursine_theme_loaded(site):
    hrefs = [l.get("href", "") for l in soup(site / "alpha/one.html").find_all("link", rel="stylesheet")]
    assert any(h.endswith("_static/ursine.css") or "_static/ursine.css?" in h for h in hrefs)
    assert any(h.startswith("https://fonts.googleapis.com/css2?family=Fira+Mono") for h in hrefs)
    assert (site / "_static/ursine.css").exists()
