#!/usr/bin/env python3
"""Estimate how full each slide of the Marp deck is, and report the ones at risk of overflow.

Marp cannot be rasterized on this machine (the CLI needs a local Chrome and there is none), so
this is the stand-in: it lays each slide out arithmetically from the deck's own CSS and reports
the ratio of estimated content height to the height a 16:9 slide has after its padding.

The model is deliberately crude and deliberately pessimistic, because its only job is to sort
slides by risk. A slide over 1.0 needs looking at, a slide over 0.9 is worth a second read, and
the absolute numbers mean nothing on their own. Compare a new slide against the ones the deck
has always had: those render, so a new slide scoring no worse than the busiest of them is safe.

Usage:

    python tools/slide_fit.py                 # every slide over the warn threshold
    python tools/slide_fit.py --all            # every slide, in deck order
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

DECK = Path(__file__).resolve().parent.parent / "slides" / "qprogram_tutorial.md"

# From the deck's inline stylesheet and a 1280x720 slide.
SLIDE_H = 720.0
PADDING_Y = 56.0 * 2
CONTENT_H = SLIDE_H - PADDING_Y  # 608
CONTENT_W = 1280.0 - 72.0 * 2  # 1136

BASE = 26.0  # section font-size
BODY_LINE = BASE * 1.45  # ul, ol line-height
BODY_CHARS = 88  # characters of body text that fit on one line, measured off the rendered deck
H2 = BASE * 1.35 * 1.1 + 30  # one heading line plus its margins
PRE_LINE = BASE * 0.72 * 1.35  # pre font-size and line-height
TABLE_LINE = BASE * 0.76 * 1.7  # table font-size, and rows are roomier than their text
TABLE_CHARS = 110  # per cell-row, before it wraps
QUOTE_LINE = BASE * 0.86 * 1.45
MATH_BLOCK = 62.0  # a display formula, whatever is in it
CAP_LINE = BASE * 0.72 * 1.4

FENCE = re.compile(r"^```")
IMAGE = re.compile(r"!\[h:(\d+)\]")
DIRECTIVE = re.compile(r"^<!--.*-->$")


def slides(text: str) -> list[list[str]]:
    """Split the deck into slides on its horizontal rules, dropping the YAML front matter."""
    body = text.split("\n---\n", 1)[1] if text.startswith("---\n") else text
    return [chunk.split("\n") for chunk in body.split("\n---\n")]


def height(lines: list[str]) -> float:
    """The estimated content height of one slide, in CSS pixels."""
    total = 0.0
    in_fence = False
    in_style = False
    for raw in lines:
        line = raw.rstrip()
        if "<style>" in line:
            in_style = True
        if in_style:
            in_style = "</style>" not in line
            continue
        if FENCE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            total += PRE_LINE
            continue
        stripped = line.strip()
        if not stripped or DIRECTIVE.match(stripped):
            continue
        found = IMAGE.search(stripped)
        if found is not None:
            total += float(found.group(1)) + 12
            continue
        if stripped.startswith("#"):
            total += H2
            continue
        if stripped.startswith("$$"):
            total += MATH_BLOCK
            continue
        if stripped.startswith("|"):
            cells = len(stripped.strip("|").split("|"))
            wrapped = max(1, -(-len(stripped) // (TABLE_CHARS if cells > 2 else BODY_CHARS)))
            total += TABLE_LINE * wrapped
            continue
        if stripped.startswith(">"):
            total += QUOTE_LINE * max(1, -(-len(stripped) // BODY_CHARS))
            continue
        if 'class="cap"' in stripped:
            total += CAP_LINE
            continue
        if stripped.startswith("<"):
            total += BODY_LINE  # any other raw block, counted as one line
            continue
        total += BODY_LINE * max(1, -(-len(stripped) // BODY_CHARS))
    return total


def title(lines: list[str]) -> str:
    for line in lines:
        if line.startswith("#"):
            return line.lstrip("# ").strip()
    for line in lines:
        if line.strip() and not DIRECTIVE.match(line.strip()):
            return line.strip()[:40]
    return "(untitled)"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="report every slide, in deck order")
    parser.add_argument("--warn", type=float, default=0.9, help="report slides at or above this fill")
    args = parser.parse_args()

    deck = slides(DECK.read_text(encoding="utf-8"))
    rows = [(height(s) / CONTENT_H, i + 1, title(s)) for i, s in enumerate(deck)]
    shown = rows if args.all else sorted((r for r in rows if r[0] >= args.warn), reverse=True)
    for fill, number, name in shown:
        flag = "OVER" if fill > 1.0 else "    "
        print(f"{flag} {fill:5.2f}  slide {number:3d}  {name}")
    over = sum(1 for fill, _, _ in rows if fill > 1.0)
    print(f"{len(deck)} slides, {over} over the estimate, busiest {max(r[0] for r in rows):.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
