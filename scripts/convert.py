#!/usr/bin/env python3
"""Convert HAProxy manuals into Sphinx RST sources.

Usage:
    convert.py --docs DIR --out DIR [--manual configuration.txt]

Reads ``*.txt`` manuals from ``--docs`` and writes generated RST (one file per
top-level chapter, plus ``index.rst`` and ``keywords.rst``) into ``--out``.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from renderer import convert as converter  # noqa: E402
from scripts import generate_toc  # noqa: E402

DEFAULT_MANUALS = ["configuration.txt"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs", required=True, help="directory containing doc/*.txt")
    parser.add_argument("--out", required=True, help="Sphinx source output directory")
    parser.add_argument("--manual", action="append", default=[],
                        help="manual filename to convert (repeatable)")
    args = parser.parse_args(argv)

    manuals = args.manual or DEFAULT_MANUALS
    os.makedirs(args.out, exist_ok=True)

    converted = []
    for name in manuals:
        src = os.path.join(args.docs, name)
        if not os.path.isfile(src):
            print("Skipping missing manual: {0}".format(src), file=sys.stderr)
            continue
        base = name.replace(".txt", "")
        manual_dir = os.path.join(args.out, base)
        os.makedirs(manual_dir, exist_ok=True)
        print("Converting {0}...".format(name))
        manual = converter.convert(src)
        generate_toc.write_chapter_files(manual, manual_dir)
        generate_toc.write_keywords(manual, args.out)
        converted.append((base, manual))

    generate_toc.write_index(
        converted,
        {base: base for base, _ in converted},
        args.out,
    )
    print("Done. {0} manual(s) converted.".format(len(converted)))


if __name__ == "__main__":
    main()
