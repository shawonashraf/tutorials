# Tutorial site from notebooks — design

## Intent

The repo is a collection of tutorials, each a Jupyter notebook. The parent
directory of a notebook is its topic. We want a static website built from these
notebooks and served on GitHub Pages at `https://shawonashraf.github.io/tutorials/`.

Visitors mostly browse: they want to see which topics exist and jump between
posts. The look follows the PyTorch tutorials site
(<https://docs.pytorch.org/tutorials/>), with one change: topics live in the left
sidebar, not in the top bar, because a top bar overflows as topics grow.

## What a visitor sees

A throwaway build (Sphinx + pydata-sphinx-theme + myst-nb) was shown to the
owner and approved. Build the real thing to match it:

- **Top bar:** site name "Tutorials" (links to the root), search, light/dark
  toggle, GitHub icon linking to `https://github.com/shawonashraf/tutorials`.
  No topic links in the top bar.
- **Left sidebar:** every topic, with its posts nested under it. Subtopics
  (sub-directories) nest the same way, to any depth. Each topic is collapsible.
  The topic containing the current page is expanded; the others are collapsed.
  The theme's "Collapse Sidebar" button hides the whole sidebar.
- **Content:** breadcrumbs (Home › Topic › Post), the rendered notebook
  (markdown, code, stored outputs, math).
- **Right sidebar:** "On this page" headings, "Edit on GitHub" (pointing at
  the real notebook path in the repo), "Show Source".
- **Root URL:** redirects to the first post of the first topic
  (currently `attention/bahdanau.html`).
- **Topic page** (clicking a topic name): its title and a list of its posts.

## Rules

- **Topic names:** directory name, split on `-` and `_`, each word
  capitalised. `generative-modelling` → "Generative Modelling". (Owner's rule.)
- **Post titles:** always the file name with the topic-name rule applied,
  ignoring any headings inside the notebook. `byte_pair_tokenisation.ipynb` →
  "Byte Pair Tokenisation", `vae.ipynb` → "Vae". (Owner's rule.) The title is
  used in the sidebar, the topic page, breadcrumbs, the browser tab and as the
  page's H1. It is injected as an H1 cell into the build copy only — source
  notebooks are never modified. The notebook's own headings become sections
  under that H1, so they show in "On this page" but never as separate entries
  in the sidebar or topic page.
- **URLs:** mirror the repo layout. `attention/bahdanau.ipynb` →
  `/tutorials/attention/bahdanau.html`; a topic is `/tutorials/<dir>/index.html`.
- **Discovery:** any directory that contains `.ipynb` files (directly or in a
  sub-directory) is a topic. Hidden directories (`.git`, `.ipynb_checkpoints`,
  …) and the site's own build directory are skipped. Directories without
  notebooks (e.g. `docs/`) never appear.
- **Ordering:** topics and posts sorted alphabetically by directory/file name.
  (My call.)
- **Execution:** notebooks are rendered with the outputs already saved in
  them; nothing is executed at build time (`nb_execution_mode = "off"`). Some
  notebooks train models; running them in CI is not wanted.

## How it gets built

Decided (my calls, shown to the owner via the spike):

- **Sphinx** with **pydata-sphinx-theme** and **myst-nb**. MyST extensions
  `dollarmath` and `amsmath` so `$...$` / `$$...$$` render.
- **Sidebar override:** a custom `sidebar-nav-bs.html` template calling
  `generate_toctree_html("sidebar", startdepth=0, show_nav_level=1,
  collapse=False, includehidden=True, titles_only=True)`, and
  `html_theme_options["navbar_center"] = []` to empty the top bar. This is
  what makes the whole topic tree appear in the sidebar.
- **Generator script:** before `sphinx-build`, a Python script walks the repo,
  mirrors notebooks into a generated source directory (gitignored), injects
  the title H1, writes one `index.md` per topic with a toctree of its posts
  and sub-topics, and writes the root `index.md` with a hidden toctree of the
  topics plus the redirect. Nothing generated is committed.
- **Python tooling:** `uv` only (owner's call; no pip/venv). A uv project at
  the repo root (`uv init`). `pyproject.toml` and `uv.lock` are committed.
- **Dependency split (owner's call):** the website's dependencies live in
  their own dependency group, separate from the tutorials' dependencies:
  - `site` group: `uv add --group site sphinx pydata-sphinx-theme myst-nb`
    (plus `pytest` for the generator tests, in `site` or `dev` — builder's
    call).
  - Tutorial dependencies (torch, jax, …) stay in the project's main
    dependencies or their own group, and are added by the owner as tutorials
    need them. None are added as part of this work.
  - The GitHub Action installs only the site group (e.g.
    `uv sync --locked --only-group site`), never the project's main
    dependencies, so torch/jax are never downloaded on the runner. This must
    hold even after the owner adds heavy tutorial dependencies.
- **Deploy:** a GitHub Actions workflow builds on every push to `main` and
  publishes with the official Pages actions (`upload-pages-artifact` +
  `deploy-pages`). The owner sets Settings › Pages › Source to
  "GitHub Actions" once.
- **Local preview:** one documented command that generates, builds, and
  serves the site locally.

The spike's working files are in the session scratchpad
(`spike/gen.py`, `spike/src_conf.py`, `spike/templates/sidebar-nav-bs.html`)
and can be used as a starting point, but they were throwaway and untested.
The spike used first-heading titles; the real build uses file-name titles.

## Edge cases (my calls)

- "Edit on GitHub" is hidden on generated pages (root and topic `index`
  pages), since they have no file in the repo.
- Notebooks at the repo root (none today) are skipped with a build warning.
- A notebook named `index.ipynb` fails the build with a clear error (it would
  clash with the generated topic page).
- `navigation_depth` is raised so deep subtopic nesting isn't cut off at the
  theme default of 4.
- Headings are found by parsing the markdown, not a line regex.
- The local preview command is documented in a root `README.md`.
- Notebooks with no stored outputs (currently all of `generative-modelling/`)
  show code only; re-running and saving them is up to the owner.

## Left to the builder

- Where the site tooling lives in the repo (e.g. a `site/` directory) and the
  name of the generated source/build directories.
- Whether build deps go in a root `pyproject.toml` dependency group or a
  separate project for the site.
- Suppressing myst heading-level warnings (notebooks start at `##`/`###`
  under the injected H1; this is expected).
- Tests for the generator (naming rule, titles, discovery, nesting).

## Non-goals

- Executing notebooks at build time.
- "Download notebook" / "Open in Colab" buttons.
- Custom branding, logo, versioned docs, comments, analytics.
- Hand-written per-topic landing pages or descriptions.
- Using PyTorch's own theme, name or logo.

## Anti-goals

- Topics in the top bar (overflows).
- A hand-rolled look (a plain custom HTML mockup was rejected).
- Changing the source notebooks or requiring per-notebook metadata to get a
  post onto the site — dropping a notebook into a directory must be enough.
