import os

# pylint: disable=W0622

project = 'HAProxy Docs'
copyright = ''
author = 'https://github.com/haproxy/haproxy'

extensions = ['sphinx_immaterial']
exclude_patterns = []
html_theme = 'sphinx_immaterial'
html_static_path = ['_static']
master_doc = 'index'
display_version = True
sticky_navigation = True
html_favicon = '_static/img/favicon.svg'
source_suffix = {
    '.rst': 'restructuredtext',
}

rst_prolog = """
.. role:: check
.. role:: cross
"""

# Read the upstream source commit (written by fetch-upstream.sh) for the footer.
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
commit_file = os.path.join(repo_root, 'vendor', 'haproxy-docs', 'COMMIT')
haproxy_commit = ''
if os.path.isfile(commit_file):
    with open(commit_file, encoding='utf-8') as fd:
        haproxy_commit = fd.read().strip()

html_theme_options = {
    "site_url": "https://haproxy.docs.oxl.app",
    "repo_url": "https://github.com/haproxy/haproxy",
    "repo_name": "haproxy/haproxy",
    "globaltoc_collapse": True,
    "features": [
        "navigation.expand",
        # "navigation.tabs",
        # "navigation.tabs.sticky",
        # "toc.integrate",
        "navigation.sections",
        # "navigation.instant",
        # "header.autohide",
        "navigation.top",
        "navigation.footer",
        # "navigation.tracking",
        # "search.highlight",
        "search.share",
        "search.highlight",
        "search.suggest",
        "toc.follow",
        "toc.sticky",
        "toc.integrate",
        "content.tabs.link",
        "content.code.copy",
        "content.tooltips",
        "announce.dismiss",
    ],
    "palette": [
        {
            "media": "(prefers-color-scheme: light)",
            "scheme": "default",
            "primary": "light-blue",
            "accent": "light-green",
            "toggle": {
                "icon": "material/lightbulb",
                "name": "Switch to dark-mode",
            },
        },
        {
            "media": "(prefers-color-scheme: dark)",
            "scheme": "slate",
            "primary": "deep-orange",
            "accent": "lime",
            "toggle": {
                "icon": "material/lightbulb-outline",
                "name": "Switch to light-mode",
            },
        },
    ],
    "version_dropdown": True,
    "version_info": [
        {
            "version": "https://www.haproxy.org",
            "title": "HAProxy-Community Project",
            "aliases": [],
        },
        {
            "version": "https://github.com/haproxy/haproxy",
            "title": "HAProxy-Community Repository on GitHub",
            "aliases": [],
        },
    ],
    "social": [],
}

html_title = 'HAProxy-Community Docs'
html_short_title = 'HAProxy-Community Docs'
html_js_files = ['https://files.oxl.at/js/feedback.js']
html_css_files = ['css/main.css', 'https://files.oxl.at/css/feedback.css']

# Display the upstream source commit in the footer.
html_context = {
    "haproxy_commit": haproxy_commit,
}
