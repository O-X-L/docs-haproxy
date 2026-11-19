"""Convert HAProxy plain-text manuals into reStructuredText.

This module parses the official ``doc/*.txt`` manuals (``configuration.txt``
etc.) into a chapter/section model and renders each top-level chapter to RST.

The detection logic (section splitting, keyword / table / example / see-also /
arguments patterns) is adapted from the Apache-2.0 licensed
`haproxy-dconv` project (Copyright 2012 Cyril Bonté); see
``vendor/haproxy-dconv/`` for the vendored reference copy and license.
"""

import re

from . import rst

# ---------------------------------------------------------------------------
# Section / heading model (adapted from haproxy-dconv parser/converter.py)
# ---------------------------------------------------------------------------

_SECTION_START = re.compile(r"^\d")


def get_title_details(line):
    """Split a heading line into title / chapter / level / toplevel.

    Ported from ``haproxy-dconv`` ``parser/converter.py:getTitleDetails``.
    """
    parts = line.split(".")
    title = parts.pop().strip()
    chapter = ".".join(parts)
    level = max(1, len(parts))
    toplevel = parts[0] if parts else False
    return {"title": title, "chapter": chapter, "level": level, "toplevel": toplevel}


def _split_sections(lines):
    """Split the manual into a list of ``{details, content}`` sections.

    Ported from ``haproxy-dconv`` ``parser/converter.py:convert``.
    """
    sections = []
    current = {"details": get_title_details(""), "content": ""}
    nblines = len(lines)
    i = 0
    while i < nblines:
        line = lines[i].rstrip()
        nxt = lines[i + 1].rstrip() if i + 1 < nblines else ""
        if (line == "Summary" or _SECTION_START.match(line)) and nxt and nxt[0] == "-":
            sections.append(current)
            current = {"details": get_title_details(line), "content": ""}
            i += 1  # skip underline
            while i + 1 < nblines and not lines[i + 1].rstrip():
                i += 1
        else:
            current["content"] += line + "\n"
        i += 1
    sections.append(current)
    return sections


# ---------------------------------------------------------------------------
# Header parsing (title / subtitle / version / author / date)
# ---------------------------------------------------------------------------

_HEADER_SEP = re.compile(r"^-+$")


def parse_header(content):
    """Extract title / subtitle / version / author / date from the file header.

    Ported from ``haproxy-dconv`` ``parser/converter.py`` header handling.
    """
    result = {"title": "", "subtitle": "", "version": "", "author": "", "date": ""}
    lines = content.split("\n")
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and _HEADER_SEP.match(lines[i].strip()):
        i += 1
        result["title"] = lines[i].strip() if i < len(lines) else ""
        i += 1
        subtitle = []
        while i < len(lines) and not _HEADER_SEP.match(lines[i].strip()):
            subtitle.append(lines[i].strip())
            i += 1
        result["subtitle"] = " ".join(s for s in subtitle if s).strip()
        if not result["subtitle"] and result["title"].startswith("HAProxy "):
            result["subtitle"] = result["title"][8:]
            result["title"] = "HAProxy"
        i += 1  # skip separator
        result["version"] = lines[i].strip() if i < len(lines) else ""
        i += 1
        result["author"] = lines[i].strip() if i < len(lines) else ""
        i += 1
        result["date"] = lines[i].strip() if i < len(lines) else ""
    return result


# ---------------------------------------------------------------------------
# Inline markup
# ---------------------------------------------------------------------------

_CODE_SPAN = re.compile(r"`([^`]+)`")

# A bare URL (http/https/ftp). Used to de-link "example" URLs only.
_URL_RE = re.compile(r"(?:https?|ftp)://[^\s<>\"'()\[\]{}]+")


def _escape_plain(text):
    # Escape characters that reStructuredText would otherwise interpret as
    # emphasis / hyperlink markers.
    text = text.replace("\\", "\\\\").replace("*", "\\*").replace("_", "\\_")
    text = _de_link_example_urls(text)
    return text


def _de_link_example_urls(text):
    """Prevent auto-linking of URLs that contain the substring ``example``."""
    def repl(m):
        url = m.group(0)
        if "example" in url.lower():
            return url.replace("://", "\\://", 1)
        return url
    return _URL_RE.sub(repl, text)


def format_inline(text):
    """Format a source prose line as RST inline text.

    Converts single-backtick code spans to double-backtick literals and escapes
    ``*``/``_`` outside code spans so they are not interpreted as emphasis.
    """
    out = []
    pos = 0
    for m in _CODE_SPAN.finditer(text):
        out.append(_escape_plain(text[pos:m.start()]))
        out.append("``" + m.group(1) + "``")
        pos = m.end()
    out.append(_escape_plain(text[pos:]))
    return "".join(out)


# ---------------------------------------------------------------------------
# Keyword detection (adapted from haproxy-dconv parser/keyword.py)
# ---------------------------------------------------------------------------

_KEYWORD_RE = re.compile(
    r"^([a-z0-9\-\+_\.]*[a-z0-9\-\+_)])((?: [a-z0-9\-_]+)*)(\([^ ]*\))?"
)
# Argument text must look like "<args>", "[args]", "{args}", ": fetch ...",
# "(deprecated)", or be empty. (``<`` here, not the HTML-escaped ``&lt;``.)
_KEYWORD_PARAMS_RE = re.compile(
    r"^ +(/?([<\[]|\[|\{).*|(: [a-z0-9 +]+))?(\(deprecated\))?$"
)


def detect_keyword(line):
    """Return keyword info if ``line`` is a keyword definition, else ``None``."""
    if not line or line[0] == " ":
        return None
    m = _KEYWORD_RE.match(line)
    if not m:
        return None
    keyword = m.group(1) + (m.group(2) or "")
    arg = m.group(3) or ""
    # Reject separators / borders (all '-', '+', '.', '_' with no alphanumeric).
    if not re.search(r"[a-z0-9]", keyword):
        return None
    parameters = line[len(keyword) + len(arg):]
    if parameters and not _KEYWORD_PARAMS_RE.match(parameters):
        return None
    if len(keyword.split(" ")) > 4:
        return None
    return {"keyword": keyword, "arg": arg, "parameters": parameters}


def _label(name):
    """Derive a safe RST label from a keyword/section name."""
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", name).strip("-")


# ---------------------------------------------------------------------------
# Table detection
# ---------------------------------------------------------------------------

# A table border line: only '+', '-', and spaces, containing at least one '+'.
_BORDER_LINE = re.compile(r"^\s*[+\-][+\-\s]*\+[+\-\s]*$")
# The "dashes first" separator (format-1 pipe tables), e.g. "---+---+".
_PIPE_SEP = re.compile(r"^\s*-+(\+-+)+")
# The "plus first" grid border (format-2 grid tables), e.g. "+---+---+".
_GRID_BORDER = re.compile(r"^\s*\+(-+\+)+")
_MAYBE_USED = re.compile(r"^\s*(May be used in sections|Usable in|May be used)")


def _is_data_line(line):
    return line.lstrip().startswith("|")


def _is_table_line(line):
    """True if ``line`` is a table border or data line."""
    ls = line.lstrip()
    return (ls.startswith("|") or ls.startswith("+")
            or bool(_PIPE_SEP.match(line)))


def parse_pipe_table(lines, start):
    """Parse a format-1 ``|``-delimited table beginning at ``start``.

    ``lines[start]`` is the header row; subsequent rows are separated by
    ``---+`` border lines. A leading ``|`` marks an empty corner cell (a
    row-label column), which is preserved. Returns ``(rows, next_index)``.
    """
    rows = []
    i = start
    n = len(lines)
    rows.append(_split_pipe_table_row(lines[i]))
    i += 1
    while i < n:
        s = lines[i].rstrip("\n")
        if not s.strip():
            break
        if _PIPE_SEP.match(s) or _GRID_BORDER.match(s):
            i += 1
            continue
        if "|" not in s:
            break
        rows.append(_split_pipe_table_row(s))
        i += 1
    return rows, i


def _split_pipe_table_row(line):
    """Split a pipe-table row by ``|``, preserving a leading corner cell."""
    cells = line.split("|")
    if cells and not cells[-1].strip():
        cells = cells[:-1]  # trailing outer pipe
    return [" ".join(c.strip().split()) for c in cells]


def _split_pipe_row(line):
    cells = line.split("|")
    if cells and not cells[0].strip():
        cells = cells[1:]
    if cells and not cells[-1].strip():
        cells = cells[:-1]
    return [c.strip() for c in cells]


def parse_grid_table(lines, start):
    """Parse a format-2 ``+---+`` grid table beginning at ``start``.

    Returns ``(title, rows, next_index)``. ``title`` is a single-cell caption
    (or ``None``); ``rows`` is a list of cell lists (header first).
    """
    n = len(lines)
    i = start
    block = []
    while i < n:
        s = lines[i].rstrip("\n")
        if not s.strip():
            break
        if s.lstrip().startswith("+") or s.lstrip().startswith("|"):
            block.append(s)
            i += 1
        else:
            break

    border_indices = [k for k, s in enumerate(block) if s.lstrip().startswith("+")]
    if not border_indices:
        return None, [], i

    # Widest border defines the column count.
    ncols = max(block[k].count("+") - 1 for k in border_indices)

    # Detect an optional single-column title box (border + single-cell line).
    title = None
    k = 0
    while k < len(block):
        if not block[k].lstrip().startswith("+"):
            k += 1
            continue
        if k + 1 < len(block) and block[k + 1].lstrip().startswith("|"):
            cells = _split_pipe_row(block[k + 1])
            if len(cells) == 1:
                title = cells[0]
                k += 2
                continue
        break

    # Header = '|' lines after the main top border (up to the next '+' line).
    header_lines = []
    j = k + 1
    while j < len(block) and block[j].lstrip().startswith("|"):
        if "+" not in block[j]:
            header_lines.append(_split_pipe_row(block[j]))
        j += 1
    # Skip the header-end border(s).
    while j < len(block) and block[j].lstrip().startswith("+"):
        j += 1
    # Data rows = remaining '|' lines (each is a separate row).
    data_rows = []
    while j < len(block):
        ls = block[j].lstrip()
        if ls.startswith("|") and "+" not in block[j]:
            data_rows.append(_split_pipe_row(block[j]))
        j += 1

    header = _flatten_grid_header(header_lines, ncols)
    rows = [header] + data_rows
    return title, rows, i


def _flatten_grid_header(header_lines, ncols):
    """Flatten grid-table header lines into a single row of ``ncols`` cells."""
    if not header_lines:
        return [""] * ncols
    counts = [len(l) for l in header_lines]
    if len(set(counts)) == 1:
        # Multi-line cells: merge by column.
        merged = []
        for c in range(counts[0]):
            parts = [l[c].strip() for l in header_lines if c < len(l) and l[c].strip()]
            merged.append(" ".join(parts))
        return (merged + [""] * ncols)[:ncols]
    # Two-level header: top-level labels + sub-column labels.
    top = header_lines[0]
    sub = (header_lines[-1] + [""] * ncols)[:ncols]
    lead = next((idx for idx, v in enumerate(sub) if v != ""), len(sub))
    result = []
    if lead > 0 and top:
        result.append(top[0].strip())
    rest_top = top[1:] if lead > 0 else top
    rest_sub = sub[lead:]
    if rest_top and rest_sub:
        span = max(1, len(rest_sub) // len(rest_top))
        for idx, t in enumerate(rest_top):
            for s in rest_sub[idx * span:(idx + 1) * span]:
                label = " ".join(x for x in (t.strip(), s.strip()) if x)
                result.append(label)
    return (result + [""] * ncols)[:ncols]


def _merge_grid_row(lines):
    """Merge multi-line grid cells into a single row (join with a space)."""
    ncols = max(len(l) for l in lines)
    merged = []
    for c in range(ncols):
        parts = [l[c].strip() for l in lines if c < len(l) and l[c].strip()]
        merged.append(" ".join(parts))
    return merged


def _split_by_positions(line, positions):
    """Split ``line`` into cells using ``+`` column positions from a separator."""
    cells = []
    prev = 0
    for p in positions:
        cells.append(" ".join(line[prev:p].split()))
        prev = p + 1
    cells.append(" ".join(line[prev:].split()))
    return cells


def parse_space_table(lines, start):
    """Parse a space-aligned ``---+`` table into rows of cells.

    ``lines[start]`` is the header row and ``lines[start+1]`` the ``---+``
    separator. Column boundaries are read from the ``+`` positions in the
    separator. Returns ``(rows, next_index)``; ``rows[0]`` is the header.
    """
    header = lines[start].rstrip("\n")
    sep = lines[start + 1].rstrip("\n")
    positions = [i for i, ch in enumerate(sep) if ch == "+"]
    rows = [_split_by_positions(header, positions)]
    i = start + 2
    n = len(lines)
    while i < n:
        s = lines[i].rstrip("\n")
        if not s.strip():
            break
        if _PIPE_SEP.match(s) or _GRID_BORDER.match(s):
            i += 1
            continue
        if s.lstrip().startswith("--"):
            i += 1  # periodic repeat-header line, skip
            continue
        if "  " not in s and "+" not in s:
            break  # not a data row (prose)
        cells = _split_by_positions(s, positions)
        if cells and cells[0] == "keyword":
            i += 1  # repeated header row, skip
            continue
        rows.append(cells)
        i += 1
    return rows, i


def _support_cell(cell):
    """Rewrite feature-support matrix markers into theme icons."""
    c = cell.strip()
    if c == "X":
        return rst.Raw(":check:`\u2713`")
    if c == "-":
        return rst.Raw(":cross:`\u2717`")
    if c.startswith("X ") or c.startswith("X("):
        return rst.Raw(":check:`\u2713` " + c[1:].strip())
    if c.startswith("(*)") and "X" in c:
        return rst.Raw(":check:`\u2713` (*)")
    if c.startswith("(*)") and "-" in c:
        return rst.Raw(":cross:`\u2717` (*)")
    return cell


def _looks_like_syntax(line):
    """True if the (stripped) line reads like a keyword/syntax signature."""
    return bool(detect_keyword(line.strip()))


def _looks_like_code(line):
    """True if the (stripped) line reads like config/code rather than prose."""
    s = line.strip()
    if not s:
        return False
    if s.startswith("#") or "#" in s:
        return True  # comment
    if "  " in s:
        return True  # aligned config (multiple spaces)
    if _looks_like_syntax(s):
        return True
    return any(c in s for c in ('"', "%", "\\", "<", ">", "[", "]", "{", "}",
                                "(", ")", "`"))


# ---------------------------------------------------------------------------
# Block-level content renderer
# ---------------------------------------------------------------------------

def deindent(lines):
    """Remove the minimum common indentation from a list of lines."""
    min_indent = -1
    for line in lines:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        if min_indent < 0 or indent < min_indent:
            min_indent = indent
    if min_indent > 0:
        return [line[min_indent:] if line.strip() else line for line in lines]
    return list(lines)


_SEEALSO_RE = re.compile(r"^\s*(See also *:|See also \"|See also )")
_EXAMPLE_RE = re.compile(r"^\s*(Examples? *:)(.*)")
_ARGUMENTS_RE = re.compile(r"^\s*(Arguments? *:)(.*)")
_BULLET_RE = re.compile(r"^(\s*)([-*]) (.*)")
_NUMBERED_RE = re.compile(r"^(\s*)(\d+)\. (.*)")
# Definition-style bullet: a short term followed by " : " and a description.
_DEF_RE = re.compile(r"^(.*?)\s+:\s+(.*)$")
# Definition-style bullet: a single-word term followed by ": " (e.g. env vars).
_DEF2_RE = re.compile(r"^([^\s:]+):\s+(.*)$")
# Definition-style bullet: a term and a description aligned by 2+ spaces.
_SPACED_DEF_RE = re.compile(r"^(\S+)\s{2,}(\S.*)$")


def _indent_of(line):
    return len(line) - len(line.lstrip(" "))


def _nest_indent(indent, base):
    """Map a source indent to an RST nesting indent (2 spaces per level).

    HAProxy's source indentation is not a consistent "N spaces per level", so
    we treat any deeper indent as a single nesting level to avoid producing
    RST block quotes.
    """
    return "  " if indent > base else ""


def _is_structural(line, section_mode=True):
    """True if ``line`` starts a structural block (not plain prose)."""
    s = line.rstrip("\n")
    if not s.strip():
        return False
    if _SEEALSO_RE.match(s) or _EXAMPLE_RE.match(s) or _ARGUMENTS_RE.match(s):
        return True
    if _MAYBE_USED.match(s) or _GRID_BORDER.match(s):
        return True
    if _PIPE_SEP.match(s):
        return True
    if "|" in s:
        return True
    if _BULLET_RE.match(s):
        return True
    if not s.startswith(" "):
        return bool(detect_keyword(s))  # keyword definition at column 0
    if section_mode and s.startswith(" "):
        return True  # indented literal block in section content
    return False


class ContentRenderer:
    """Render a section's content lines to RST."""

    def __init__(self, toplevel, keywords, seen_labels):
        self.toplevel = toplevel
        self.keywords = keywords  # shared list of (toplevel, name)
        self.seen_labels = seen_labels  # shared set of emitted anchor labels

    def render(self, lines, section_mode=True):
        out = []
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            s = line.rstrip("\n")
            if not s.strip():
                i += 1
                continue

            # Tables
            handled, result, i = self._try_table(lines, i)
            if handled:
                out.extend(result)
                continue

            # See also
            if _SEEALSO_RE.match(s):
                desc = _SEEALSO_RE.sub("", s).strip()
                out.append(rst.seealso(format_inline(desc)))
                out.append("")
                i += 1
                continue

            # Examples
            m = _EXAMPLE_RE.match(s)
            if m:
                inline = m.group(2).strip()
                if inline:
                    out.append(rst.code_block([inline], "text"))
                    i += 1
                else:
                    code, i = self._collect_indented(lines, i)
                    if code:
                        out.append(rst.code_block(code, "text"))
                    i += 1
                continue

            # Arguments
            if _ARGUMENTS_RE.match(s):
                out.append("**Arguments:**")
                out.append("")
                i += 1
                continue

            # Bullet list
            if _BULLET_RE.match(s):
                i = self._render_list(out, lines, i)
                continue

            # Numbered list
            if _NUMBERED_RE.match(s):
                i = self._render_numbered_list(out, lines, i)
                continue

            # Indented literal block (section-level code/config examples)
            if section_mode and s.startswith(" "):
                block, i = self._collect_literal(lines, i)
                if block and any(_looks_like_code(b) for b in block):
                    out.append(rst.code_block(block, "text"))
                elif block:
                    # Centered table caption / title -> bold paragraph.
                    out.append("**" + format_inline(" ".join(b.strip() for b in block)) + "**")
                    out.append("")
                else:
                    i += 1  # e.g. a table data line not detected above
                continue

            # Keyword (column 0)
            kw = detect_keyword(s) if not s.startswith(" ") else None
            if kw:
                i = self._render_keyword(out, lines, i)
                continue

            # Paragraph (gather until blank or structural line)
            para = []
            while i < n and lines[i].strip() and not _is_structural(lines[i], section_mode):
                para.append(lines[i].strip())
                i += 1
            if para:
                out.append(format_inline(" ".join(para)))
                out.append("")
            else:
                i += 1

        return out

    # -- tables -------------------------------------------------------------

    def _try_table(self, lines, i):
        line = lines[i].rstrip("\n")
        if _MAYBE_USED.match(line):
            return self._render_maybe_used(lines, i)
        n = len(lines)
        nxt = lines[i + 1].rstrip("\n") if i + 1 < n else ""
        if _GRID_BORDER.match(line):
            title, rows, ni = parse_grid_table(lines, i)
            result = []
            if title:
                result.append("**" + format_inline(title) + "**")
                result.append("")
            if rows:
                result.append(rst.list_table(rows, header_rows=1,
                                             transform=_support_cell))
            return True, result, ni
        if _PIPE_SEP.match(nxt):
            if "|" in line:
                rows, ni = parse_pipe_table(lines, i)
                return True, [rst.list_table(rows, header_rows=1,
                                             transform=_support_cell)], ni
            rows, ni = parse_space_table(lines, i)
            return True, [rst.list_table(rows, header_rows=1,
                                         transform=_support_cell)], ni
        return False, None, i

    def _render_maybe_used(self, lines, i):
        line = lines[i].rstrip("\n")
        label = line.split(":", 1)[0].strip()
        rest = line.split(":", 1)[1].strip() if ":" in line else ""
        nxt = lines[i + 1].rstrip("\n") if i + 1 < len(lines) else ""

        # "May be used in sections : a | b | c" followed by a "x | y | z" line
        if "|" in rest and "|" in nxt:
            header = [c.strip() for c in rest.split("|") if c.strip() != ""]
            values = [c.strip() for c in nxt.split("|")]
            if values and not values[0].strip():
                values = values[1:]
            if values and not values[-1].strip():
                values = values[:-1]
            out = ["**" + label + ":**", ""]
            if header and values:
                out.append(rst.list_table(rows=[header, values], header_rows=1,
                                          transform=_support_cell))
            return True, out, i + 2

        # Inline values, e.g. "May be used in the following contexts: tcp, http"
        out = ["**" + label + ":** " + format_inline(rest), ""]
        return True, out, i + 1

    # -- keywords -----------------------------------------------------------

    def _render_keyword(self, out, lines, i):
        signatures = []
        n = len(lines)
        while i < n and detect_keyword(lines[i].rstrip("\n")):
            signatures.append(lines[i].rstrip("\n"))
            i += 1
        name = detect_keyword(signatures[0])["keyword"]
        label = _label("{0}-{1}".format(self.toplevel, name))
        if label not in self.seen_labels:
            self.seen_labels.add(label)
            self.keywords.append((self.toplevel, name))
            out.append(rst.anchor(label))
        # Collect description (indented lines) and render recursively.
        desc = []
        while i < n and (lines[i].startswith(" ") or not lines[i].strip()):
            desc.append(lines[i])
            i += 1
        if len(signatures) == 1:
            out.append(rst.inline_code(" ".join(signatures[0].split())))
        else:
            for sig in signatures:
                out.append("| " + rst.inline_code(" ".join(sig.split())))
        out.append("")
        if desc:
            out.extend(self.render(deindent(desc), section_mode=False))
        return i

    # -- bullets ------------------------------------------------------------

    def _render_list(self, out, lines, i):
        n = len(lines)
        first = lines[i].rstrip("\n")
        base = _indent_of(first)
        while i < n:
            s = lines[i].rstrip("\n")
            if not s.strip():
                # blank line: end of list unless the next non-blank is a bullet
                # at (or nested deeper than) the base indent
                j = i + 1
                while j < n and not lines[j].strip():
                    j += 1
                if j < n and _BULLET_RE.match(lines[j].rstrip("\n")) and \
                        _indent_of(lines[j].rstrip("\n")) >= base:
                    i = j
                    continue
                break
            m = _BULLET_RE.match(s)
            if not m:
                break
            indent = _indent_of(s)
            if indent < base:
                break
            content = m.group(3)
            parts = [content]
            i += 1
            # continuation lines (more indented, non-bullet)
            while i < n and lines[i].strip():
                c = lines[i].rstrip("\n")
                if _BULLET_RE.match(c):
                    break
                if _indent_of(c) > indent:
                    parts.append(c.strip())
                    i += 1
                else:
                    break
            marker = "-"
            item = " ".join(parts)
            indent_str = _nest_indent(indent, base)
            if indent > base and out and out[-1] != "":
                out.append("")  # separate a nested list from the parent item
            dm = _DEF_RE.match(content) or _DEF2_RE.match(content) or _SPACED_DEF_RE.match(content)
            if dm:
                term = dm.group(1).strip()
                desc = dm.group(2).strip()
                cont = " ".join(p.strip() for p in parts[1:])
                if cont:
                    desc = (desc + " " + cont).strip()
                out.append(indent_str + marker + " " +
                           rst.inline_code(" ".join(term.split())))
                out.append("")
                out.append(indent_str + "  " + format_inline(desc))
            elif _looks_like_syntax(content):
                term = rst.inline_code(" ".join(content.split()))
                out.append(indent_str + marker + " " + term)
                if len(parts) > 1:
                    desc = " ".join(p.strip() for p in parts[1:])
                    out.append("")
                    out.append(indent_str + "  " + format_inline(desc))
            else:
                item = format_inline(item)
                out.append(indent_str + marker + " " + item)
        out.append("")
        return i

    def _render_numbered_list(self, out, lines, i):
        n = len(lines)
        first = lines[i].rstrip("\n")
        base = _indent_of(first)
        while i < n:
            s = lines[i].rstrip("\n")
            if not s.strip():
                j = i + 1
                while j < n and not lines[j].strip():
                    j += 1
                if j < n and _NUMBERED_RE.match(lines[j].rstrip("\n")) and \
                        _indent_of(lines[j].rstrip("\n")) >= base:
                    i = j
                    continue
                break
            m = _NUMBERED_RE.match(s)
            if not m:
                break
            indent = _indent_of(s)
            if indent < base:
                break
            content = m.group(3)
            parts = [content]
            i += 1
            while i < n and lines[i].strip():
                c = lines[i].rstrip("\n")
                if _NUMBERED_RE.match(c) or _BULLET_RE.match(c):
                    break
                if _indent_of(c) > indent:
                    parts.append(c.strip())
                    i += 1
                else:
                    break
            item = " ".join(parts)
            indent_str = _nest_indent(indent, base)
            out.append(indent_str + "#. " + format_inline(item))
        out.append("")
        return i

    # -- helpers ------------------------------------------------------------

    def _collect_literal(self, lines, i):
        """Collect an indented literal (code) block starting at ``lines[i]``."""
        n = len(lines)
        block = []
        while i < n:
            s = lines[i].rstrip("\n")
            ls = s.lstrip()
            if not s.strip():
                # include blank line only if the block continues indented
                j = i + 1
                while j < n and not lines[j].strip():
                    j += 1
                if j < n and lines[j].startswith(" ") and \
                        not _is_table_line(lines[j]):
                    block.append("")
                    i += 1
                    continue
                break
            if s.startswith(" ") and not (ls.startswith("|") or ls.startswith("+")):
                block.append(s)
                i += 1
            else:
                break
        while block and not block[-1].strip():
            block.pop()
        block = deindent(block)
        return block, i

    def _collect_indented(self, lines, i):
        """Collect the indented code block following an Example: line."""
        n = len(lines)
        ref_indent = _indent_of(lines[i])
        i += 1
        while i < n and not lines[i].strip():
            i += 1
        # Only collect content indented more deeply than the "Example" label;
        # otherwise there is no block (avoids swallowing following prose).
        if i >= n or _indent_of(lines[i]) <= ref_indent:
            return [], i - 1
        base_indent = _indent_of(lines[i])
        block = []
        while i < n:
            line = lines[i].rstrip("\n")
            if not line.strip():
                block.append("")
                i += 1
                continue
            indent = _indent_of(line)
            if indent >= base_indent:
                block.append(line[base_indent:])
                i += 1
            else:
                break
        while block and not block[-1].strip():
            block.pop()
        return block, i - 1


def render_content(lines, toplevel, keywords, seen_labels):
    return ContentRenderer(toplevel, keywords, seen_labels).render(lines)


# ---------------------------------------------------------------------------
# Chapter rendering
# ---------------------------------------------------------------------------

def render_chapter(sections, toplevel, keywords, seen_labels):
    """Render all sections belonging to ``toplevel`` into one RST document."""
    out = []
    for sec in sections:
        details = sec["details"]
        if details["toplevel"] != toplevel and details["chapter"]:
            continue
        title = details["title"]
        full = (details["chapter"] + ". " + title) if details["chapter"] else title
        out.append(rst.heading(full, details["level"]))
        out.append("")
        if sec["content"].strip():
            out.extend(render_content(sec["content"].split("\n"), toplevel,
                                      keywords, seen_labels))
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Top-level conversion
# ---------------------------------------------------------------------------

def convert(infile):
    """Convert a manual file into a structured result.

    Returns a dict with ``header``, ``chapters`` (ordered), ``rendered``
    (slug -> RST), and ``keywords`` (ordered unique keyword names).
    """
    with open(infile, encoding="utf-8") as fd:
        lines = [line.replace("\t", " " * 8).rstrip() for line in fd]

    sections = _split_sections(lines)
    header = parse_header(sections[0]["content"])

    chapters = {}
    for sec in sections:
        details = sec["details"]
        if details["chapter"] and details["toplevel"]:
            chapters.setdefault(details["toplevel"], details)

    ordered = sorted(chapters.keys(), key=lambda c: [int(x) for x in c.split(".")])

    groups = {}
    for sec in sections:
        tl = sec["details"]["toplevel"]
        if tl:
            groups.setdefault(tl, []).append(sec)

    keywords = []  # list of (toplevel, name)
    seen_labels = set()
    rendered = {}
    for tl in ordered:
        slug = "{0}-{1}".format(tl, rst.slug(chapters[tl]["title"]))
        rendered[slug] = render_chapter(groups[tl], tl, keywords, seen_labels)

    return {"header": header, "chapters": chapters, "ordered": ordered,
            "rendered": rendered, "keywords": keywords}
