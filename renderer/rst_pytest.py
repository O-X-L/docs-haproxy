"""Tests for the RST formatting helpers in ``renderer.rst``."""

import pytest

from renderer import rst


def test_heading_levels():
    assert rst.heading("Title", 1) == "Title\n=====\n"
    assert rst.heading("Title", 2) == "Title\n-----\n"
    assert rst.heading("Title", 3) == "Title\n~~~~~\n"
    # Out-of-range levels clamp to a valid underline character.
    assert rst.heading("Title", 99) == "Title\n#####\n"


def test_heading_underline_matches_length():
    text = "A Much Longer Heading"
    char, rest = rst.heading(text, 1).split("\n")[1], ""
    assert len(char) >= len(text)


def test_anchor():
    assert rst.anchor("foo") == ".. _foo:\n"


def test_label_ref():
    assert rst.label_ref("foo", "bar") == ":ref:`bar <foo>`"


def test_inline_code():
    assert rst.inline_code("frontend <name>") == "``frontend <name>``"


def test_code_block():
    out = rst.code_block(["line one", "line two"], "text")
    assert out.startswith(".. code-block:: text\n")
    assert "    line one\n" in out
    assert "    line two\n" in out


def test_code_block_empty():
    assert rst.code_block([]) == ""


def test_seealso():
    assert rst.seealso("the foo keyword") == ".. seealso:: the foo keyword\n"


def test_escape_inline_backticks():
    assert rst.escape_inline("use `foo` here") == "use ``foo`` here"


def test_slug():
    assert rst.slug("Global section") == "global-section"
    assert rst.slug("TCP/HTTP  Proxies") == "tcp-http-proxies"
    assert rst.slug("!!!") == "chapter"


def test_list_table_basic():
    out = rst.list_table([["a", "b"], ["1", "2"]], header_rows=1)
    assert ".. list-table::" in out
    assert ":header-rows: 1" in out
    assert "* - a" in out
    assert "- b" in out
    assert "* - 1" in out


def test_list_table_pads_ragged_rows():
    # Row 2 has fewer cells than the header; it must be padded.
    out = rst.list_table([["h1", "h2", "h3"], ["x"]], header_rows=1)
    assert "- x" in out


def test_list_table_transform():
    def transform(cell):
        return "CHANGED" if cell == "x" else cell

    out = rst.list_table([["a", "x"], ["b", "x"]], header_rows=1, transform=transform)
    assert out.count("CHANGED") == 2


def test_list_table_raw_cell_not_escaped():
    rows = [[rst.Raw(":check:`\u2713`"), "plain"]]
    out = rst.list_table(rows, header_rows=1)
    assert ":check:`\u2713`" in out  # role emitted verbatim, not escaped
