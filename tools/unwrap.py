#!/usr/bin/env python3
"""Join hard-wrapped prose back onto one line per paragraph.

A renderer wraps text to the reader's width, so a hard wrap in the source adds nothing to the
output and costs two things. A one-word edit rewraps the paragraph, so the diff shows every line
the rewrap touched instead of the sentence that changed. And in the Marp deck it was worse than
cosmetic: Marp Core sets markdown-it `breaks: true`, so every hard wrap rendered as a forced
line break on the slide and the text stopped reflowing to the slide width.

What keeps its line structure: YAML front matter, fenced code, `<style>` blocks, HTML lines,
headings, table rows, thematic breaks and Marp slide separators, and blank lines. What gets
joined: paragraphs, list items, and blockquotes.

Two things a joiner has to get right or it silently changes the document, both of which this got
wrong on the first attempt. A bullet may interrupt a paragraph in CommonMark, so a `- ` at the
start of a line opens a new item even with a paragraph already open; absorbing it turns the
marker into literal text and drops a list item. And a block's leading indentation is what nests
it inside a list item, so each block carries its own first line's indent rather than being
flattened to column zero.

Neither failure is visible to a check that collapses whitespace, so every rewrite is gated on two
conditions instead: the text must be unchanged once whitespace and quote markers are collapsed,
and the block skeleton must be unchanged. A file that fails either is left alone.

Usage:

    python tools/unwrap.py README.md sources/*.py   # rewrite the files given
    python tools/unwrap.py --check README.md        # report wrapped paragraphs, write nothing

`tools/check_style.py` applies the same check to every text file in the repo, so ordinarily
there is nothing to run by hand.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import re

FENCE = re.compile(r"^\s*(```|~~~)")
BULLET = re.compile(r"^[-*+]\s+")
ORDERED = re.compile(r"^(\d+)\.\s+")
BREAK = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
QUOTE = re.compile(r"^>\s?")
CELL = re.compile(r"^# %%(?P<rest>.*)$")

# Percent-format markdown cells are exactly one r-string; these are its delimiters.
OPENERS = {'r"""', "r'''"}
CLOSERS = {'"""', "'''"}


class Joiner:
    """Accumulates the lines of one paragraph, list item, or blockquote.

    Also records where a block spanned more than one line, which is what lets the checker name
    the offending line instead of only saying that a file is wrapped somewhere.
    """

    def __init__(self, out: list[str]) -> None:
        self.out = out
        self.parts: list[str] = []
        self.prefix = ""
        self.kind: str | None = None
        self.start_line = 0
        self.wrapped: list[tuple[int, str]] = []

    def flush(self) -> None:
        if self.parts:
            self.out.append(self.prefix + " ".join(self.parts))
            if len(self.parts) > 1:
                self.wrapped.append((self.start_line, self.parts[0]))
        self.parts = []
        self.prefix = ""
        self.kind = None

    def start(self, kind: str, text: str, lineno: int, prefix: str = "") -> None:
        self.flush()
        self.kind = kind
        self.prefix = prefix
        self.parts = [text]
        self.start_line = lineno

    def add(self, text: str) -> None:
        self.parts.append(text)

    def emit(self, line: str) -> None:
        self.flush()
        self.out.append(line)


def _walk(text: str, front_matter: bool) -> tuple[list[str], list[tuple[int, str]]]:
    """Return the joined lines, and the (line number, first line) of every wrapped block."""
    lines = text.split("\n")
    out: list[str] = []
    join = Joiner(out)
    index = 0

    # YAML front matter keeps every line: `marp: true` is not a sentence.
    if front_matter and lines and lines[0].strip() == "---":
        out.append(lines[0])
        index = 1
        while index < len(lines):
            out.append(lines[index])
            if lines[index].strip() == "---":
                index += 1
                break
            index += 1

    fence: str | None = None
    in_style = False

    while index < len(lines):
        line = lines[index]
        index += 1
        lineno = index  # 1-based, and `index` has just been advanced past this line
        stripped = line.strip()

        if fence is not None:
            out.append(line)
            if stripped.startswith(fence):
                fence = None
            continue
        if in_style:
            out.append(line)
            if "</style>" in line:
                in_style = False
            continue

        match = FENCE.match(line)
        if match:
            join.emit(line)
            fence = match.group(1)
            continue
        if stripped.startswith("<style"):
            join.emit(line)
            in_style = "</style>" not in line
            continue
        if not stripped:
            join.emit("")
            continue
        if BREAK.match(line) or stripped.startswith("#") or stripped.startswith("|") or stripped.startswith("<"):
            join.emit(line)
            continue

        indent = line[: len(line) - len(line.lstrip())]

        if stripped.startswith(">"):
            content = QUOTE.sub("", stripped)
            if not content:
                join.emit(stripped)
            elif join.kind == "quote":
                join.add(content)
            else:
                join.start("quote", content, lineno, prefix=indent + "> ")
            continue

        if join.kind == "quote":
            join.flush()

        ordered = ORDERED.match(stripped)
        # A bullet always opens an item: CommonMark lets one interrupt a paragraph, and an
        # ordered marker may too when it counts from one.
        starts_item = bool(BULLET.match(stripped)) or (
            ordered is not None and (join.kind != "para" or ordered.group(1) == "1")
        )
        if starts_item:
            join.start("list", stripped, lineno, prefix=indent)
        elif join.kind in ("para", "list"):
            join.add(stripped)
        else:
            join.start("para", stripped, lineno, prefix=indent)

    join.flush()
    return out, join.wrapped


def unwrap(text: str, *, front_matter: bool = False) -> str:
    """Return ``text`` with every paragraph, list item, and blockquote on one line."""
    return "\n".join(_walk(text, front_matter)[0])


def wrapped(text: str, *, front_matter: bool = False) -> list[tuple[int, str]]:
    """Return the 1-based line number and opening text of every hard-wrapped block."""
    return _walk(text, front_matter)[1]


def _cells(text: str):
    """Yield ``(block_lines, is_markdown, first_line_index)`` for each percent-format cell."""
    lines = text.split("\n")
    block: list[str] = []
    markdown = False
    start = 0
    for index, line in enumerate(lines):
        match = CELL.match(line)
        if match is not None:
            if block:
                yield block, markdown, start
            block = []
            markdown = match.group("rest").strip() == "[markdown]"
            start = index + 1
            continue
        block.append(line)
    if block:
        yield block, markdown, start


def _inner(block: list[str]) -> tuple[int, int]:
    """Return the indices bounding a markdown cell's r-string body, exclusive of the quotes."""
    opener = next(i for i, ln in enumerate(block) if ln.strip() in OPENERS)
    closer = len(block) - 1 - next(i for i, ln in enumerate(reversed(block)) if ln.strip() in CLOSERS)
    return opener, closer


def unwrap_source(text: str) -> str:
    """Unwrap the markdown cells of a percent-format source, leaving every code cell untouched."""
    lines = text.split("\n")
    out: list[str] = []
    cursor = 0  # every line before the current cell's body, markers included, is copied verbatim
    for block, markdown, start in _cells(text):
        out.extend(lines[cursor:start])
        cursor = start + len(block)
        if not markdown:
            out.extend(block)
            continue
        opener, closer = _inner(block)
        out.extend(block[: opener + 1])
        out.extend(unwrap("\n".join(block[opener + 1 : closer])).split("\n"))
        out.extend(block[closer:])
    out.extend(lines[cursor:])
    return "\n".join(out)


def wrapped_in_source(text: str) -> list[tuple[int, str]]:
    """Return the wrapped blocks of a percent-format source, numbered against the whole file."""
    found: list[tuple[int, str]] = []
    for block, markdown, start in _cells(text):
        if not markdown:
            continue
        opener, closer = _inner(block)
        offset = start + opener + 1
        body = "\n".join(block[opener + 1 : closer])
        found.extend((lineno + offset, first) for lineno, first in wrapped(body))
    return found


def normalized(text: str) -> str:
    """What must not change: the words, once every run of whitespace and every quote marker goes."""
    return re.sub(r"\s+", " ", re.sub(r"(?m)^\s*>\s?", " ", text)).strip()


def _kind(stripped: str) -> str:
    if stripped.startswith("#"):
        return "heading"
    if stripped.startswith("|"):
        return "table"
    if stripped.startswith("<"):
        return "html"
    if re.match(r"^(?:-{3,}|\*{3,}|_{3,})$", stripped):
        return "rule"
    if stripped.startswith(">"):
        return "quote"
    if BULLET.match(stripped) or ORDERED.match(stripped):
        return "list"
    return "para"


def skeleton(text: str) -> list[str]:
    """The document's block structure: one entry per run of non-blank lines, plus every blank.

    A block and the joined version of it are the same run, so the two agree unless a blank line
    moved, a block changed type, or a block lost the indentation that nested it. Collapsing
    whitespace cannot see any of that, which is why it is checked separately.
    """
    out: list[str] = []
    fence: str | None = None
    open_block = False
    for line in text.split("\n"):
        stripped = line.strip()
        if fence is not None:
            if stripped.startswith(fence):
                fence = None
            continue
        if stripped.startswith(("```", "~~~")):
            out.append("code")
            fence = stripped[:3]
            open_block = True
            continue
        if not stripped:
            out.append("blank")
            open_block = False
            continue
        if not open_block:
            indent = len(line) - len(line.lstrip())
            out.append(f"{_kind(stripped)}@{indent}")
            open_block = True
    return out


def rewrite(path: Path) -> str | None:
    """Unwrap one file in place. Returns a message when the rewrite is refused."""
    original = path.read_text(encoding="utf-8")
    result = unwrap_source(original) if path.suffix == ".py" else unwrap(original, front_matter=True)
    if normalized(result) != normalized(original):
        return f"{path}: refused, the text changed and not just its line breaks"
    before, after = skeleton(original), skeleton(result)
    if before != after:
        spot = next((i for i, (x, y) in enumerate(zip(before, after)) if x != y), min(len(before), len(after)))
        return (
            f"{path}: refused, the block structure changed at block {spot}: "
            f"{before[spot - 1 : spot + 2]} became {after[spot - 1 : spot + 2]}"
        )
    if result != original:
        path.write_text(result, encoding="utf-8")
    return None


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--check", action="store_true", help="report wrapped paragraphs and write nothing")
    cli.add_argument("paths", nargs="+", help="files to unwrap")
    args = cli.parse_args(argv)

    problems = 0
    for name in args.paths:
        path = Path(name)
        text = path.read_text(encoding="utf-8")
        if args.check:
            found = wrapped_in_source(text) if path.suffix == ".py" else wrapped(text, front_matter=True)
            for lineno, first in found:
                print(f"{path}:{lineno}: hard-wrapped paragraph, {first[:60]!r}")
            problems += len(found)
            continue
        before = len(text.split("\n"))
        refused = rewrite(path)
        if refused is not None:
            print(refused, file=sys.stderr)
            return 1
        after = len(path.read_text(encoding="utf-8").split("\n"))
        print(f"{path}: unchanged" if before == after else f"{path}: {before} -> {after} lines")
    if args.check:
        print(f"checked {len(args.paths)} files, {problems} wrapped paragraphs")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
