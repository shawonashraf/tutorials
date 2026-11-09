# Tutorial Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the repo's notebooks into a static Sphinx site (topics nested in a collapsible sidebar) and deploy it to GitHub Pages on every push to `main`.

**Architecture:** `website/generate.py` walks the repo, copies notebooks (with an injected file-name H1) into a gitignored `website/_src/` mirror, and writes one `index.md` toctree per topic plus a root `index.md` that redirects to the first post. `sphinx-build -c website website/_src website/_build` renders it with pydata-sphinx-theme; a template override puts the whole topic tree in the left sidebar. A GitHub Actions workflow installs only the `site` dependency group, builds, and deploys.

**Tech Stack:** uv, Python, Sphinx, pydata-sphinx-theme, myst-nb, pytest, BeautifulSoup (comes with pydata-sphinx-theme), GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-09-tutorial-site-design.md`

## Global Constraints

- Use `uv` for everything; never pip/venv. Website deps live only in the `site` dependency group. No tutorial deps (torch, jax) are added.
- CI installs with `--only-group site`; it must never install the project's main dependencies.
- Name rule (topics and post titles): split on `-`, `_` and whitespace, drop empty parts, upper-case the first letter of each word, leave the rest of the word unchanged, join with one space. `generative-modelling` → `Generative Modelling`; `vae` → `Vae`.
- Post titles always come from the file name; notebook headings are ignored for titles.
- Source notebooks are never modified. Generated files never committed.
- Notebooks are never executed (`nb_execution_mode = "off"`).
- Sort topics and posts by directory/file name. Within a topic: posts first, then subtopics.
- Skip directories whose name starts with `.` or `_`, and the `website` directory. A directory with no notebooks anywhere below it is not a topic.
- Site name `Tutorials`; GitHub link `https://github.com/shawonashraf/tutorials`; branch `main`.
- Commits: short message in the repo's style, no `Co-Authored-By` or "Generated with" lines.

## Review Focus

1. File/dir names with spaces or capitals (`My VAE notes.ipynb`) — expect title `My VAE Notes`, build still succeeds. Tests in Task 1 (name) and Task 3 (build).
2. Re-running the generator after a notebook is deleted — expect the stale copy gone from `_src`. Test in Task 2.
3. A notebook with zero cells — expect a page with just the title. Test in Task 2.
4. A topic that holds only subtopics (no direct posts) as the first topic — expect the redirect to go to the first post inside its first subtopic. Test in Task 2.
5. Nesting deeper than the theme default of 4 levels — expect the deepest post to appear in the sidebar. Test in Task 3.

---

### Task 1: uv project, name rule and topic discovery

**Files:**
- Create: `pyproject.toml`, `uv.lock` (via uv), `website/generate.py`, `website/tests/test_generate.py`
- Modify: `.gitignore` (append `.venv/`, `website/_src/`, `website/_build/`)

**Interfaces:**
- Produces, in `website/generate.py`:
  - `pretty_name(name: str) -> str`
  - `class SiteError(Exception)`
  - `@dataclass class Topic: dir: Path; posts: list[Path]; subtopics: list["Topic"]` — all paths relative to the repo root; `posts` are `.ipynb` paths.
  - `find_topics(repo: Path) -> list[Topic]`

- [ ] **Step 1: Create the uv project and site group**

```bash
uv init --bare --name tutorials
uv add --group site sphinx pydata-sphinx-theme myst-nb pytest
```
Expected: `pyproject.toml` has no `dependencies` entries and a `[dependency-groups] site = [...]` with the four packages; `uv.lock` exists.

- [ ] **Step 2: Write failing tests** in `website/tests/test_generate.py`. Import with `sys.path.insert(0, <website dir>)` then `import generate`. Use a helper `make_nb(path, cells=())` that writes a minimal nbformat 4.4 notebook.

```python
def test_pretty_name():
    assert pretty_name("generative-modelling") == "Generative Modelling"
    assert pretty_name("vae_cnn_fashionmnist") == "Vae Cnn Fashionmnist"
    assert pretty_name("byte_pair_tokenisation") == "Byte Pair Tokenisation"
    assert pretty_name("a--b__c") == "A B C"
    assert pretty_name("My VAE notes") == "My VAE Notes"

def test_find_topics_nested_and_sorted(tmp_path):
    # b/z.ipynb, b/a.ipynb, a/x.ipynb, a/sub/y.ipynb
    topics = find_topics(tmp_path)
    assert [t.dir for t in topics] == [Path("a"), Path("b")]
    assert topics[0].posts == [Path("a/x.ipynb")]
    assert topics[0].subtopics[0].posts == [Path("a/sub/y.ipynb")]
    assert topics[1].posts == [Path("b/a.ipynb"), Path("b/z.ipynb")]

def test_find_topics_skips(tmp_path):
    # .hidden/n.ipynb, _x/n.ipynb, website/n.ipynb, a/.ipynb_checkpoints/n.ipynb,
    # docs/readme.md (no notebooks), a/real.ipynb
    assert [t.dir for t in find_topics(tmp_path)] == [Path("a")]
    assert find_topics(tmp_path)[0].subtopics == []

def test_root_notebook_warns(tmp_path):
    # stray.ipynb at root, a/x.ipynb
    with pytest.warns(UserWarning, match="stray.ipynb"):
        assert [t.dir for t in find_topics(tmp_path)] == [Path("a")]

def test_index_notebook_rejected(tmp_path):
    # a/index.ipynb
    with pytest.raises(SiteError, match="a/index.ipynb"):
        find_topics(tmp_path)
```

- [ ] **Step 3: Run tests, expect failure**

Run: `uv run --only-group site pytest website/tests -v`
Expected: FAIL (import errors / missing names).

- [ ] **Step 4: Implement `pretty_name`, `SiteError`, `Topic`, `find_topics` in `website/generate.py`**

Recursive walk with `sorted(...)`; drop a directory from the result when it has no posts and no subtopics.

- [ ] **Step 5: Run tests, expect pass**

Run: `uv run --only-group site pytest website/tests -v` → all pass.

- [ ] **Step 6: Commit** `pyproject.toml uv.lock .gitignore website/generate.py website/tests/test_generate.py` — message `site: uv project and topic discovery`.

### Task 2: Write Sphinx sources

**Files:**
- Modify: `website/generate.py`, `website/tests/test_generate.py`

**Interfaces:**
- Consumes: `pretty_name`, `find_topics`, `Topic` (Task 1).
- Produces:
  - `first_post(topics: list[Topic]) -> Path` — first post in sidebar order (topic's posts, then recurse into subtopics); raises `SiteError("no notebooks found")` if none.
  - `write_sources(repo: Path, out: Path) -> None` — deletes `out` if it exists, then writes the mirror.
  - `main(argv: list[str] | None = None) -> int` — CLI `python website/generate.py <repo> <out>`; prints `SiteError` to stderr and returns 1.

Output of `write_sources`:
- Each post copied to `out/<same relative path>` with a markdown cell inserted at index 0: `{"cell_type": "markdown", "metadata": {}, "source": ["# <pretty_name(stem)>"]}`, plus `"id": "site-title"` only when `nbformat_minor >= 5`. All other notebook content unchanged.
- `out/<topic dir>/index.md`:

  ````
  # <pretty_name(dir name)>

  ```{toctree}
  :maxdepth: 1
  :titlesonly:

  <post stem, one per line>
  <subtopic name>/index
  ````
- `out/index.md`:

  ````
  # Tutorials

  ```{raw} html
  <meta http-equiv="refresh" content="0; url=<first_post with .html suffix, posix>">
  ```

  ```{toctree}
  :hidden:

  <topic dir>/index, one per line
  ```
  ````

- [ ] **Step 1: Write failing tests**

```python
def test_write_sources_post(tmp_path):
    # repo/a-b/my_post.ipynb with one code cell; out = tmp_path/"out"
    write_sources(repo, out)
    nb = json.loads((out / "a-b/my_post.ipynb").read_text())
    assert nb["cells"][0]["source"] == ["# My Post"]
    assert nb["cells"][1] == original_code_cell
    assert "id" not in nb["cells"][0]               # nbformat 4.4 source
    assert json.loads((repo / "a-b/my_post.ipynb").read_text()) == original  # untouched

def test_write_sources_indexes(tmp_path):
    # repo/a/x.ipynb, repo/a/sub/y.ipynb, repo/b/z.ipynb
    write_sources(repo, out)
    a = (out / "a/index.md").read_text()
    assert a.startswith("# A\n")
    assert a.index("\nx\n") < a.index("\nsub/index\n")
    root = (out / "index.md").read_text()
    assert 'url=a/x.html"' in root
    assert ":hidden:" in root and "\na/index\n" in root and "\nb/index\n" in root

def test_first_post_topic_with_only_subtopics(tmp_path):
    # repo/a/sub/y.ipynb, repo/b/z.ipynb
    assert first_post(find_topics(repo)) == Path("a/sub/y.ipynb")

def test_rerun_removes_stale(tmp_path):
    # write_sources, delete repo/a/x.ipynb (keep another post), write_sources again
    assert not (out / "a/x.ipynb").exists()

def test_empty_notebook(tmp_path):
    # repo/a/empty.ipynb with cells == []
    write_sources(repo, out)
    assert json.loads((out / "a/empty.ipynb").read_text())["cells"][0]["source"] == ["# Empty"]

def test_main_reports_error(tmp_path, capsys):
    assert main([str(tmp_path), str(tmp_path / "out")]) == 1   # empty repo
    assert "no notebooks found" in capsys.readouterr().err
```

- [ ] **Step 2: Run tests, expect failure** — `uv run --only-group site pytest website/tests -v`.
- [ ] **Step 3: Implement `first_post`, `write_sources`, `main`** (`if __name__ == "__main__": sys.exit(main())`).
- [ ] **Step 4: Run tests, expect pass.**
- [ ] **Step 5: Run on the real repo**

Run: `uv run --only-group site python website/generate.py . website/_src && find website/_src -type f | sort`
Expected: 7 notebooks, `attention/index.md`, `generative-modelling/index.md`, `tokenisation/index.md`, `index.md` containing `url=attention/bahdanau.html`. `git status` shows no changes to notebooks.

- [ ] **Step 6: Commit** `website/generate.py website/tests/test_generate.py` — `site: generate sphinx sources from notebooks`.

### Task 3: Sphinx config, sidebar, build script, README

**Files:**
- Create: `website/conf.py`, `website/_templates/sidebar-nav-bs.html`, `website/build.sh` (executable), `website/tests/test_build.py`, `README.md`

**Interfaces:**
- Consumes: `write_sources` (Task 2).
- Produces: `website/build.sh` — from any cwd, runs the generator into `website/_src` and `sphinx-build -c website website/_src website/_build`, both via `uv run --locked --only-group site`. Output site in `website/_build`. Task 4 calls it.

`website/conf.py` values:
- `project = "Tutorials"`, `author = "Shawon Ashraf"`, `extensions = ["myst_nb"]`, `nb_execution_mode = "off"`, `myst_enable_extensions = ["dollarmath", "amsmath"]`, `suppress_warnings = ["myst.header"]`, `templates_path = ["_templates"]`, `html_theme = "pydata_sphinx_theme"`, `html_title = "Tutorials"`.
- `html_theme_options`: `navbar_center: []`; `icon_links: [{"name": "GitHub", "url": "https://github.com/shawonashraf/tutorials", "icon": "fa-brands fa-github"}]`; `use_edit_page_button: True`; `show_toc_level: 2`; `secondary_sidebar_items: {"**": ["page-toc", "edit-this-page", "sourcelink"], "index": ["page-toc"], "**/index": ["page-toc"]}`.
- `html_context = {"github_user": "shawonashraf", "github_repo": "tutorials", "github_version": "main", "doc_path": ""}`.

`website/_templates/sidebar-nav-bs.html` (overrides the theme's; this exact call is what puts the full tree in the sidebar — verified in the spike):

```html
<nav class="bd-docs-nav bd-links" aria-label="Topics">
  <div class="bd-toc-item navbar-nav">
    {{- generate_toctree_html("sidebar", startdepth=0, show_nav_level=1, maxdepth=MAXDEPTH, collapse=False, includehidden=True, titles_only=True) -}}
  </div>
</nav>
```
`MAXDEPTH`: the value Sphinx treats as unlimited (try `0`, else `-1`); the deep-nesting test decides.

- [ ] **Step 1: Write failing tests** in `website/tests/test_build.py`. Fixture: tmp repo with `alpha/one.ipynb`, `alpha/two.ipynb`, `beta-gamma/three.ipynb`, `beta-gamma/My VAE notes.ipynb`, and `deep/l1/l2/l3/l4/l5/bottom_post.ipynb`; run `write_sources`, then `sphinx.cmd.build.build_main(["-q", "-c", str(WEBSITE_DIR), str(src), str(out)]) == 0`. Parse pages with BeautifulSoup.

```python
def test_post_page(site):
    html = soup(site / "alpha/one.html")
    assert html.title.text.startswith("One")
    sidebar = html.select_one(".bd-sidebar-primary").get_text()
    for name in ["Alpha", "Beta Gamma", "Deep", "One", "Two", "Three", "My VAE Notes", "Bottom Post"]:
        assert name in sidebar
    assert "Alpha" not in html.select_one(".bd-header").get_text()   # no topics in top bar
    assert html.find("a", href=re.compile(r"/edit/main/alpha/one\.ipynb$"))

def test_topic_and_root_pages(site):
    assert not soup(site / "alpha/index.html").find("a", href=re.compile("/edit/"))
    assert 'url=alpha/one.html' in (site / "index.html").read_text()
```

- [ ] **Step 2: Run tests, expect failure** — `uv run --only-group site pytest website/tests/test_build.py -v` (missing conf/template).
- [ ] **Step 3: Create `conf.py` and the template.**
- [ ] **Step 4: Run all tests, expect pass** — `uv run --only-group site pytest website/tests -v`.
- [ ] **Step 5: Write `website/build.sh`** (`set -euo pipefail`, `cd` to repo root via the script's own path) **and `README.md`** (one paragraph on what the repo is, then "Preview the site": `website/build.sh && python3 -m http.server -d website/_build 8000`, open `http://localhost:8000/`; and one line: deploys on push to `main`; Pages source must be set to "GitHub Actions" once).
- [ ] **Step 6: Build the real site and look at it**

Run: `website/build.sh && python3 -m http.server -d website/_build 8000`
Expected: build exits 0. In a browser: root redirects to Attention › Bahdanau; sidebar lists Attention / Generative Modelling / Tokenisation with posts "Bahdanau", "General Attention", "Self Attention", "Byte Pair Tokenisation", "Vae"…; math renders; Collapse Sidebar works; topic page lists posts once each; light/dark toggle works.

- [ ] **Step 7: Commit** `website/conf.py website/_templates/sidebar-nav-bs.html website/build.sh website/tests/test_build.py README.md` — `site: sphinx config, sidebar and build script`.

### Task 4: GitHub Pages workflow

**Files:**
- Create: `.github/workflows/pages.yml`

**Interfaces:**
- Consumes: `website/build.sh` (Task 3), `site` group in `uv.lock` (Task 1).

Workflow: triggers `push` to `main` and `workflow_dispatch`; `permissions: {contents: read, pages: write, id-token: write}`; `concurrency: {group: pages, cancel-in-progress: false}`.
- `build` job (`ubuntu-latest`): `actions/checkout@v4`; `astral-sh/setup-uv@v6`; `uv sync --locked --only-group site`; `uv run --locked --only-group site pytest website/tests`; `website/build.sh`; `actions/upload-pages-artifact@v3` with `path: website/_build`.
- `deploy` job: `needs: build`, `environment: {name: github-pages, url: ${{ steps.deployment.outputs.page_url }}}`, `actions/deploy-pages@v4` with `id: deployment`.

Use the latest major of each action if a newer one exists at implementation time.

- [ ] **Step 1: Write the workflow.**
- [ ] **Step 2: Validate**

Run: `uv run --only-group site python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/pages.yml'))"` (PyYAML ships with the site deps; if not, use `uvx --from pyyaml python -c ...`). If `actionlint` is installed, run it too.
Expected: no errors.

- [ ] **Step 3: Prove the runner install stays light**

Run: `uv sync --locked --only-group site && uv pip list | grep -Ei '^(torch|jax) ' || echo "no heavy deps"`
Expected: `no heavy deps`.

- [ ] **Step 4: Commit** `.github/workflows/pages.yml` — `site: deploy to github pages`. Do not push; ask the owner.
