"""Generate the Sphinx ``index.rst`` toctree and keyword index.

Used by ``convert.py``. Reads the converted manuals and writes the entry pages.
"""

import os

from renderer import convert as converter


def _manual_title(manual):
    header = manual["header"]
    if header["subtitle"]:
        return "{0} {1}".format(header["title"], header["subtitle"]).strip()
    return header["title"] or "HAProxy Documentation"


def write_chapter_files(manual, out_dir):
    """Write one RST file per chapter under ``out_dir`` and return relative
    paths (for the toctree)."""
    rel = []
    for slug, text in manual["rendered"].items():
        path = os.path.join(out_dir, slug + ".rst")
        with open(path, "w", encoding="utf-8") as fd:
            fd.write(text)
        rel.append(slug)
    return rel


def write_keywords(manual, out_dir):
    """Write the keyword index page."""
    chapters = manual["chapters"]
    by_chapter = {}
    for toplevel, name in manual["keywords"]:
        by_chapter.setdefault(toplevel, []).append(name)

    lines = []
    lines.append("Keyword Index")
    lines.append("=============")
    lines.append("")
    lines.append("All configuration keywords grouped by section.")
    lines.append("")
    for toplevel in manual["ordered"]:
        if toplevel not in by_chapter:
            continue
        title = chapters[toplevel]["title"]
        lines.append("{0}. {1}".format(toplevel, title))
        lines.append("-" * (len("{0}. {1}".format(toplevel, title))))
        lines.append("")
        seen = set()
        for name in by_chapter[toplevel]:
            if name in seen:
                continue
            seen.add(name)
            label = converter._label("{0}-{1}".format(toplevel, name))
            lines.append("- :ref:`{0} <{1}>`".format(name, label))
        lines.append("")

    path = os.path.join(out_dir, "keywords.rst")
    with open(path, "w", encoding="utf-8") as fd:
        fd.write("\n".join(lines))


def write_index(manuals, chapter_dirs, out_dir):
    """Write the top-level ``index.rst``.

    ``manuals`` is a list of (slug, manual) and ``chapter_dirs`` maps slug to
    the relative directory holding that manual's chapter files.
    """
    lines = []
    title = "HAProxy Documentation"
    lines.append(title)
    lines.append("=" * len(title))
    lines.append("")
    lines.append(
        "This is a mirror of the official HAProxy documentation "
        "(https://github.com/haproxy/haproxy), converted to reStructuredText "
        "and rendered with Sphinx."
    )
    lines.append("")

    for slug, manual in manuals:
        title = _manual_title(manual)
        lines.append(title)
        lines.append("-" * len(title))
        lines.append("")
        version = manual["header"]["version"]
        if version:
            lines.append("Version: **{0}**".format(version))
            lines.append("")
        lines.append(".. toctree::")
        lines.append("   :maxdepth: 2")
        lines.append("   :caption: {0}".format(title))
        lines.append("")
        base = chapter_dirs[slug]
        for chapter in manual["rendered"]:
            lines.append("   {0}/{1}".format(base, chapter))
        lines.append("")

    lines.append("Keyword Index")
    lines.append("-------------")
    lines.append("")
    lines.append(".. toctree::")
    lines.append("   :maxdepth: 1")
    lines.append("   :caption: Reference")
    lines.append("")
    lines.append("   keywords")
    lines.append("")

    path = os.path.join(out_dir, "index.rst")
    with open(path, "w", encoding="utf-8") as fd:
        fd.write("\n".join(lines))
