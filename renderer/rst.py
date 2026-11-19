"""RST formatting helpers for the HAProxy documentation converter.

These are pure string-building utilities with no knowledge of the HAProxy
document format; the detection/parsing logic lives in ``convert.py``.
"""

import re

# Underline characters mapped by RST heading level (1-based). Must be applied in
# this descending order per Sphinx/docutils conventions.
HEADING_CHARS = ["=", "-", "~", "^", '"', "'", "*", "+", "#"]


def heading(text, level):
    """Render an RST heading at the given 1-based level."""
    char = HEADING_CHARS[min(max(level, 1), len(HEADING_CHARS)) - 1]
    text = text.strip()
    return "{0}\n{1}\n".format(text, char * len(text))


def anchor(label):
    """Render an explicit RST anchor/label."""
    return ".. _{0}:\n".format(label)


def label_ref(label, text):
    """Render a cross-reference to an explicit label."""
    return ":ref:`{0} <{1}>`".format(text, label)


class Raw:
    """A cell/value emitted verbatim (already valid RST, e.g. an inline role)."""

    def __init__(self, text):
        self.text = text


def inline_code(text):
    """Render inline literal code."""
    return "``{0}``".format(text)


def code_block(lines, language="haproxy"):
    """Render a fenced code block."""
    if not lines:
        return ""
    body = "\n".join(lines)
    if not body.endswith("\n"):
        body += "\n"
    return ".. code-block:: {0}\n\n{1}\n".format(language, _indent(body, 4))


def list_table(rows, widths=None, header_rows=1, transform=None):
    """Render a ``.. list-table::`` directive.

    ``rows`` is a list of rows; each row is a list of cell strings. ``transform``
    is an optional per-cell callable (e.g. to rewrite feature-support markers).
    """
    if not rows:
        return ""
    max_cols = max(len(row) for row in rows)
    rows = [list(row) + [""] * (max_cols - len(row)) for row in rows]
    if transform:
        rows = [[transform(cell) for cell in row] for row in rows]
    out = [".. list-table::", "   :header-rows: {0}".format(header_rows)]
    if widths:
        out.append("   :widths: " + " ".join(str(w) for w in widths))
    out.append("")
    for row in rows:
        out.append("   * - " + _cell(row[0]))
        for cell in row[1:]:
            out.append("     - " + _cell(cell))
    out.append("")
    return "\n".join(out)


def seealso(text):
    """Render a ``.. seealso::`` directive."""
    return ".. seealso:: {0}\n".format(text.strip())


def _cell(text):
    if isinstance(text, Raw):
        return text.text
    text = text.strip()
    if "\n" in text:
        # Multi-line cell: keep as a single line separated by spaces; list-table
        # does not support multi-paragraph cells cleanly.
        text = " ".join(line.strip() for line in text.split("\n") if line.strip())
    return escape_inline(text)


def _indent(text, spaces):
    prefix = " " * spaces
    return "\n".join(prefix + line if line else "" for line in text.split("\n"))


# Inline markup handling.
#
# The upstream .txt uses single backticks for inline code (e.g. `foo`), which
# reStructuredText interprets as "interpreted text" (role-qualified). We convert
# them to double-backtick literals so Sphinx renders them verbatim without
# warnings.
_BACKTICK = re.compile(r"`([^`]+)`")


def escape_inline(text):
    """Escape inline markup from a source text line for use in RST prose."""
    return _BACKTICK.sub(r"``\1``", text)


def slug(text):
    """Derive a stable, filesystem-safe slug from a title or chapter number."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "chapter"
