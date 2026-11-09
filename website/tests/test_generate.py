import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generate import (  # noqa: E402
    SiteError,
    find_topics,
    first_post,
    main,
    pretty_name,
    write_sources,
)


def make_nb(path: Path, cells=()) -> dict:
    nb = {
        "cells": list(cells),
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 4,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(nb))
    return nb


def test_pretty_name():
    assert pretty_name("generative-modelling") == "Generative Modelling"
    assert pretty_name("vae_cnn_fashionmnist") == "Vae Cnn Fashionmnist"
    assert pretty_name("byte_pair_tokenisation") == "Byte Pair Tokenisation"
    assert pretty_name("a--b__c") == "A B C"
    assert pretty_name("My VAE notes") == "My VAE Notes"


def test_find_topics_nested_and_sorted(tmp_path):
    for p in ["b/z.ipynb", "b/a.ipynb", "a/x.ipynb", "a/sub/y.ipynb"]:
        make_nb(tmp_path / p)
    topics = find_topics(tmp_path)
    assert [t.dir for t in topics] == [Path("a"), Path("b")]
    assert topics[0].posts == [Path("a/x.ipynb")]
    assert topics[0].subtopics[0].dir == Path("a/sub")
    assert topics[0].subtopics[0].posts == [Path("a/sub/y.ipynb")]
    assert topics[1].posts == [Path("b/a.ipynb"), Path("b/z.ipynb")]


def test_find_topics_skips(tmp_path):
    for p in [
        ".hidden/n.ipynb",
        "_x/n.ipynb",
        "website/n.ipynb",
        "a/.ipynb_checkpoints/n.ipynb",
        "a/real.ipynb",
    ]:
        make_nb(tmp_path / p)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/readme.md").write_text("hi")
    topics = find_topics(tmp_path)
    assert [t.dir for t in topics] == [Path("a")]
    assert topics[0].subtopics == []


def test_root_notebook_warns(tmp_path):
    make_nb(tmp_path / "stray.ipynb")
    make_nb(tmp_path / "a/x.ipynb")
    with pytest.warns(UserWarning, match="stray.ipynb"):
        assert [t.dir for t in find_topics(tmp_path)] == [Path("a")]


def test_index_notebook_rejected(tmp_path):
    make_nb(tmp_path / "a/index.ipynb")
    with pytest.raises(SiteError, match="a/index.ipynb"):
        find_topics(tmp_path)


CODE_CELL = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": ["print(1)"],
}


def test_write_sources_post(tmp_path):
    repo, out = tmp_path / "repo", tmp_path / "out"
    original = make_nb(repo / "a-b/my_post.ipynb", [CODE_CELL])
    write_sources(repo, out)
    nb = json.loads((out / "a-b/my_post.ipynb").read_text())
    assert nb["cells"][0]["source"] == ["# My Post"]
    assert nb["cells"][1] == CODE_CELL
    assert "id" not in nb["cells"][0]
    assert json.loads((repo / "a-b/my_post.ipynb").read_text()) == original


def test_write_sources_title_cell_id_for_nbformat_45(tmp_path):
    repo, out = tmp_path / "repo", tmp_path / "out"
    path = repo / "a/x.ipynb"
    make_nb(path)
    nb = json.loads(path.read_text())
    nb["nbformat_minor"] = 5
    path.write_text(json.dumps(nb))
    write_sources(repo, out)
    assert json.loads((out / "a/x.ipynb").read_text())["cells"][0]["id"] == "site-title"


def test_write_sources_indexes(tmp_path):
    repo, out = tmp_path / "repo", tmp_path / "out"
    for p in ["a/x.ipynb", "a/sub/y.ipynb", "b/z.ipynb"]:
        make_nb(repo / p)
    write_sources(repo, out)
    a = (out / "a/index.md").read_text()
    assert "\n# A\n" in a
    assert a.index("\nx\n") < a.index("\nsub/index\n")
    assert "\n# Sub\n" in (out / "a/sub/index.md").read_text()
    root = (out / "index.md").read_text()
    assert 'url=a/x.html"' in root
    assert ":hidden:" in root and "\na/index\n" in root and "\nb/index\n" in root


def test_first_post_topic_with_only_subtopics(tmp_path):
    for p in ["a/sub/y.ipynb", "b/z.ipynb"]:
        make_nb(tmp_path / p)
    assert first_post(find_topics(tmp_path)) == Path("a/sub/y.ipynb")


def test_rerun_removes_stale(tmp_path):
    repo, out = tmp_path / "repo", tmp_path / "out"
    make_nb(repo / "a/x.ipynb")
    make_nb(repo / "a/y.ipynb")
    write_sources(repo, out)
    (repo / "a/x.ipynb").unlink()
    write_sources(repo, out)
    assert not (out / "a/x.ipynb").exists()
    assert (out / "a/y.ipynb").exists()


def test_empty_notebook(tmp_path):
    repo, out = tmp_path / "repo", tmp_path / "out"
    make_nb(repo / "a/empty.ipynb")
    write_sources(repo, out)
    cells = json.loads((out / "a/empty.ipynb").read_text())["cells"]
    assert cells == [{"cell_type": "markdown", "metadata": {}, "source": ["# Empty"]}]


def test_main_reports_error(tmp_path, capsys):
    assert main([str(tmp_path), str(tmp_path / "out")]) == 1
    assert "no notebooks found" in capsys.readouterr().err


def test_write_sources_refuses_to_wipe_repo(tmp_path):
    make_nb(tmp_path / "a/x.ipynb")
    for out in [tmp_path, tmp_path.parent]:
        with pytest.raises(SiteError, match="output"):
            write_sources(tmp_path, out)
    assert (tmp_path / "a/x.ipynb").exists()


def md(*lines: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": ["\n".join(lines)]}


def test_notebook_h1_headings_demoted_below_title(tmp_path):
    repo, out = tmp_path / "repo", tmp_path / "out"
    make_nb(
        repo / "a/x.ipynb",
        [md("# Own Title", "text", "## Sub", "```", "# not a heading", "```"), md("Setext", "===="), CODE_CELL],
    )
    write_sources(repo, out)
    cells = json.loads((out / "a/x.ipynb").read_text())["cells"]
    assert cells[0]["source"] == ["# X"]
    assert "".join(cells[1]["source"]) == "\n".join(
        ["## Own Title", "text", "### Sub", "```", "# not a heading", "```"]
    )
    assert "".join(cells[2]["source"]) == "Setext\n----"
    assert cells[3] == CODE_CELL


def test_headings_kept_when_notebook_has_no_h1(tmp_path):
    repo, out = tmp_path / "repo", tmp_path / "out"
    make_nb(repo / "a/x.ipynb", [md("## Sub", "text")])
    write_sources(repo, out)
    assert "".join(json.loads((out / "a/x.ipynb").read_text())["cells"][1]["source"]) == "## Sub\ntext"


def test_write_sources_refuses_non_generated_output(tmp_path):
    repo = tmp_path / "repo"
    make_nb(repo / "a/x.ipynb")
    keep = tmp_path / "keep"
    keep.mkdir()
    (keep / "precious.ipynb").write_text("{}")
    with pytest.raises(SiteError, match="output"):
        write_sources(repo, keep)
    assert (keep / "precious.ipynb").exists()
    with pytest.raises(SiteError, match="output"):
        write_sources(repo, repo / "a")
    assert (repo / "a/x.ipynb").exists()
