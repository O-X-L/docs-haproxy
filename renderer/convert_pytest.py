"""Tests for the HAProxy manual converter in ``renderer.convert``."""

import re

import pytest

from renderer import convert, rst


# ---------------------------------------------------------------------------
# Section / heading model
# ---------------------------------------------------------------------------

def test_get_title_details():
    d = convert.get_title_details("2.1.3.  Some title")
    assert d["title"] == "Some title"
    assert d["chapter"] == "2.1.3"
    assert d["level"] == 3
    assert d["toplevel"] == "2"


def test_get_title_details_toplevel():
    d = convert.get_title_details("4. Proxies")
    assert d["chapter"] == "4"
    assert d["level"] == 1
    assert d["toplevel"] == "4"


def test_parse_header():
    content = (
        "----------------------\n"
        "HAProxy\n"
        "Configuration Manual\n"
        "----------------------\n"
        "version 3.5\n"
        "2024/01/01\n"
    )
    h = convert.parse_header(content)
    assert h["title"] == "HAProxy"
    assert h["subtitle"] == "Configuration Manual"
    assert h["version"] == "version 3.5"
    assert h["author"] == "2024/01/01"


# ---------------------------------------------------------------------------
# Keyword detection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "line,expected",
    [
        ("balance <algorithm> [ <arguments> ]", "balance"),
        ("timeout client <timeout>", "timeout client"),
        ("daemon", "daemon"),
        ("master-worker", "master-worker"),
        ("http-request deny", "http-request deny"),
    ],
)
def test_detect_keyword_positive(line, expected):
    kw = convert.detect_keyword(line)
    assert kw is not None
    assert kw["keyword"] == expected


@pytest.mark.parametrize(
    "line",
    [
        "",                    # empty
        "   indented",         # leading whitespace
        "----+---+---",        # table separator
        "This is prose",       # uppercase first letter
        "acl valid-ua hdr(user-agent) -f x.lst",  # flags, not <args>
        "<algorithm> is used",  # starts with a bracket
    ],
)
def test_detect_keyword_negative(line):
    assert convert.detect_keyword(line) is None


def test_label():
    assert convert._label("3-balance") == "3-balance"
    assert convert._label("7-option forwardfor") == "7-option-forwardfor"


# ---------------------------------------------------------------------------
# Inline markup
# ---------------------------------------------------------------------------

def test_format_inline_code_span():
    assert convert.format_inline("use `foo` here") == "use ``foo`` here"


def test_format_inline_escapes_emphasis():
    assert convert.format_inline("a * b _ c") == "a \\* b \\_ c"


def test_format_inline_does_not_escape_inside_code():
    out = convert.format_inline("`a*b` and *x*")
    assert "``a*b``" in out  # code span content untouched
    assert "\\*x\\*" in out  # outside code span is escaped


# ---------------------------------------------------------------------------
# Feature-support cells
# ---------------------------------------------------------------------------

def _text(cell):
    return cell.text if isinstance(cell, rst.Raw) else cell


def test_support_cell_x():
    assert _text(convert._support_cell("X")) == ":check:`\u2713`"


def test_support_cell_dash():
    assert _text(convert._support_cell("-")) == ":cross:`\u2717`"


def test_support_cell_x_with_note():
    assert _text(convert._support_cell("X (!)")) == ":check:`\u2713` (!)"


def test_support_cell_star_x():
    assert _text(convert._support_cell("(*)  X")) == ":check:`\u2713` (*)"


def test_support_cell_other_passthrough():
    assert _text(convert._support_cell("string")) == "string"
    assert _text(convert._support_cell("")) == ""


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def test_split_pipe_row():
    assert convert._split_pipe_row("| a | b | c |") == ["a", "b", "c"]


def test_parse_pipe_table():
    lines = [
        "  Character | Unquoted | Weakly quoted | Strongly quoted",
        "  ---------+----------+---------------+----------------",
        "    <TAB>   |  \\t      |  \"<TAB>\"      |  '<TAB>'",
        "  ---------+----------+---------------+----------------",
        "  After the table",
    ]
    rows, ni = convert.parse_pipe_table(lines, 0)
    assert rows[0] == ["Character", "Unquoted", "Weakly quoted", "Strongly quoted"]
    assert rows[1] == ["<TAB>", "\\t", "\"<TAB>\"", "'<TAB>'"]
    assert ni == 4


def test_parse_space_table():
    lines = [
        " keyword                              defaults   frontend   listen    backend",
        "------------------------------------+----------+----------+---------+---------",
        "acl                                       X (!)      X         X         X",
        "backlog                                   X          X         X         -",
        "------------------------------------+----------+----------+---------+---------",
        "",
    ]
    rows, ni = convert.parse_space_table(lines, 0)
    assert rows[0] == ["keyword", "defaults", "frontend", "listen", "backend"]
    assert rows[1] == ["acl", "X (!)", "X", "X", "X"]
    assert rows[2] == ["backlog", "X", "X", "X", "-"]
    assert ni == 5


def test_parse_space_table_skips_repeat_headers():
    lines = [
        " keyword     a   b",
        "----------+---+---",
        "foo         X   -",
        "-- keyword  a - b -",
        " keyword     a   b",
        "bar         -   X",
        "",
    ]
    rows, _ = convert.parse_space_table(lines, 0)
    names = [r[0] for r in rows]
    assert names == ["keyword", "foo", "bar"]


def test_parse_grid_table():
    lines = [
        "   +---------------------+-----------------+",
        "   | Sample or converter | Default         |",
        "   |    output type      | matching method |",
        "   +---------------------+-----------------+",
        "   | boolean             | bool            |",
        "   +---------------------+-----------------+",
        "   | string              | str             |",
        "   +---------------------+-----------------+",
        "",
    ]
    title, rows, ni = convert.parse_grid_table(lines, 0)
    assert title is None
    assert rows[0] == ["Sample or converter output type", "Default matching method"]
    assert rows[1] == ["boolean", "bool"]
    assert rows[2] == ["string", "str"]
    assert ni == 8


def test_parse_grid_table_title_box():
    lines = [
        "   +-----------------+",
        "   | Input type      |",
        "   +------+----------+",
        "   | a    | b        |",
        "   +------+----------+",
        "",
    ]
    title, rows, _ = convert.parse_grid_table(lines, 0)
    assert title == "Input type"
    assert rows[0] == ["a", "b"]


# ---------------------------------------------------------------------------
# deindent
# ---------------------------------------------------------------------------

def test_deindent():
    lines = ["  foo", "    bar", "  baz"]
    assert convert.deindent(lines) == ["foo", "  bar", "baz"]


# ---------------------------------------------------------------------------
# Content rendering (end-to-end through ContentRenderer)
# ---------------------------------------------------------------------------

def render(lines, **kw):
    return convert.render_content(lines, "3", [], set(), **kw)


def test_render_keyword_and_description():
    out = "\n".join(render([
        "daemon",
        "  Runs in background.",
        "  See also: master-worker",
    ]))
    assert ".. _3-daemon:" in out
    assert "daemon" in out
    assert "Runs in background." in out
    assert ".. seealso:: master-worker" in out


def test_render_example_code_block():
    out = "\n".join(render([
        "Example:",
        "      haproxy -D",
    ]))
    assert ".. code-block:: text" in out
    assert "haproxy -D" in out


def test_render_inline_example():
    out = "\n".join(render(["Example :  bind :8443 ssl crt example.pem"]))
    assert ".. code-block:: text" in out
    assert "bind :8443 ssl crt example.pem" in out


def test_render_indented_code_block():
    out = "\n".join(render([
        "The syntax is :",
        "",
        "   acl <aclname> <criterion> [flags]",
        "",
        "More prose.",
    ]))
    assert ".. code-block:: text" in out
    assert "acl <aclname> <criterion> [flags]" in out


def test_render_bullet_syntax_inline_code():
    out = "\n".join(render([
        " - defaults [<name>]",
        " - frontend <name> [ from <defaults_name> ]",
    ]))
    assert "- ``frontend <name> [ from <defaults_name> ]``" in out


def test_render_feature_table():
    out = "\n".join(render([
        " keyword    defaults  frontend",
        "---------+----------+---------",
        "foo            X          -",
        "bar            -          X",
    ]))
    assert ":check:`\u2713`" in out
    assert ":cross:`\u2717`" in out


# ---------------------------------------------------------------------------
# Full manual conversion
# ---------------------------------------------------------------------------

FIXTURE_MANUAL = (
    "----------------------\n"
    "HAProxy\n"
    "Configuration Manual\n"
    "----------------------\n"
    "version 1.0\n"
    "2024/01/01\n"
    "\n"
    "Summary\n"
    "-------\n"
    "1.    Test chapter\n"
    "\n"
    "1. Test chapter\n"
    "---------------\n"
    "\n"
    "daemon\n"
    "  Runs in background.\n"
)


def test_convert_full(tmp_path):
    p = tmp_path / "configuration.txt"
    p.write_text(FIXTURE_MANUAL)
    result = convert.convert(str(p))

    assert result["header"]["version"] == "version 1.0"
    assert result["ordered"] == ["1"]
    assert "1-test-chapter" in result["rendered"]
    assert ".. _1-daemon:" in result["rendered"]["1-test-chapter"]
    # keyword was collected for the index
    assert ("1", "daemon") in result["keywords"]
