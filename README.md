# Tutorials

Machine learning tutorials written as Jupyter notebooks. Each folder is a topic;
each notebook in it is a post. The site is published at
<https://shawonashraf.github.io/tutorials/>.

## Adding a tutorial

Drop a notebook into a topic folder (or a new folder). The folder name becomes
the topic name and the file name becomes the post title, with `-`/`_` turned
into spaces and each word capitalised: `generative-modelling/vae_cnn.ipynb` →
Generative Modelling › Vae Cnn. Save the notebook with its outputs; the site
shows them as-is and never runs the code.

## Preview the site

Needs [uv](https://docs.astral.sh/uv/).

```bash
website/build.sh && python3 -m http.server -d website/_build 8000
```

Then open <http://localhost:8000/>.

Tutorial dependencies (torch, jax, …) go in the project's main dependencies;
the site's build dependencies are in the `site` group, which is all the
deploy workflow installs.

## Deploy

Every push to `main` builds and deploys the site with GitHub Actions. One-time
setup: in the repo's Settings › Pages, set Source to "GitHub Actions".
