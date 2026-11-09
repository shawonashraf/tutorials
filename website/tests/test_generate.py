import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generate import SiteError, find_topics, pretty_name  # noqa: E402


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
