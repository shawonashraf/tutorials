project = "Tutorials"
author = "Shawon Ashraf"

extensions = ["myst_nb"]
nb_execution_mode = "off"
myst_enable_extensions = ["dollarmath", "amsmath"]
suppress_warnings = ["myst.header"]
templates_path = ["_templates"]

html_theme = "pydata_sphinx_theme"
html_title = "Tutorials"
html_theme_options = {
    "navbar_center": [],
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/shawonashraf/tutorials",
            "icon": "fa-brands fa-github",
        },
    ],
    "use_edit_page_button": True,
    "show_toc_level": 2,
}
html_context = {
    "github_user": "shawonashraf",
    "github_repo": "tutorials",
    "github_version": "main",
    "doc_path": "",
}
