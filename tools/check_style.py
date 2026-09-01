#!/usr/bin/env python3
"""Check the tutorial text against the house style.

Three rules, all mechanical:

1. No em dashes or en dashes. Use a comma, parentheses, or two sentences.
2. No filler vocabulary from the banned list below.
3. No sentence shape over its per-file budget (see BUDGETS).

Rules 1 and 2 are line based and apply to every text file. Rule 3 counts sentence shapes in
prose only, per file, and applies to the globs in BUDGETED. Markdown cells are the prose of a
source file, so code, tables, fenced blocks, and inline code are all excluded before counting.

The budgets exist because the vocabulary list cannot catch rhythm. One `That is` opener reads
well and eight in a file read like a machine. Each budget is seeded from the file that was
already doing best, so the caps describe prose this repo has written rather than an ideal.

There is no per-file escape hatch, by design. If a budget is wrong, change the number here once
and say why in a comment, so the decision is visible instead of scattered through the sources.

Two conventions this file does not enforce, recorded so they are decisions and not drift:

- The register is formal. No contractions in prose: `it is`, not `it's`.
- `we` is the room during the session, `you` is your hands on the keyboard. Both are correct in
  their place, so a `we` heading above a `you` body is deliberate.

Usage:

    python tools/check_style.py                    # check every tracked text file
    python tools/check_style.py sources/01_*.py    # check specific files
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_GLOBS = ("README.md", "setup/*.md", "sources/*.py", "slides/*.md", "tools/build_notebooks.py")
SELF = Path(__file__).resolve()

DASHES = {"—": "em dash", "–": "en dash", "―": "horizontal bar"}

BANNED = [
    "delve",
    "leverage",
    "unlock",
    "elevate",
    "seamless",
    "seamlessly",
    "robust",
    "crucial",
    "pivotal",
    "holistic",
    "realm",
    "tapestry",
    "testament",
    "cutting-edge",
    "state-of-the-art",
    "game changer",
    "game-changer",
    "paradigm shift",
    "myriad",
    "plethora",
    "empower",
    "streamline",
    "comprehensive",
    "unleash",
    "supercharge",
    "deep dive",
    "dive in",
    "let's explore",
    "lets explore",
    "in this section we will",
    "in this section, we will",
    "it is worth noting",
    "it's worth noting",
    "it is important to note",
    "it's important to note",
    "as we can see",
    "at the end of the day",
    "the key takeaway",
    "not only",
    "great job",
]

PATTERNS = [(word, re.compile(rf"(?<![\w-]){re.escape(word)}(?![\w-])", re.IGNORECASE)) for word in BANNED]

# Sentence shapes with a per-file budget, and the cap for each. The first three are the
# append-a-meaning-clause habit: state the fact, then add a clause explaining what it meant.
# The fourth is the colon that the em dash ban keeps redirecting traffic into.
BUDGETS = (
    ("'That is' sentence opener", re.compile(r"(?:^|\.\s+)That is\b", re.MULTILINE), 3),
    ("', which is' tail", re.compile(r",\s+which is\b"), 3),
    ("'is what' construction", re.compile(r"\bis what\b"), 2),
    ("mid-sentence colon", re.compile(r"[a-z]:\s+[a-z]"), 12),
)

# Files the budgets apply to, the sources and the deck. Markdown needs the extra stripping in
# `prose` below before the counts mean anything, because a CSS block is nothing but mid-sentence
# colons.
BUDGETED = ("sources/*.py", "slides/*.md")

CELL = re.compile(r"^# %%(?P<rest>.*)$")
FENCE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`]*`")
DELIMITER = {'r"""', '"""'}

# Markdown-only furniture: YAML front matter, the deck's inline stylesheet, Marp's HTML-comment
# directives, and the raw tags around the QR grid. None of it is prose and all of it is punctuation.
FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
STYLE_BLOCK = re.compile(r"<style>.*?</style>", re.DOTALL)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")


def prose(path: Path) -> str:
    """The prose of a file: its markdown cells if it is a source, its whole text otherwise.

    Tables, fenced blocks, and inline code carry punctuation that is not prose punctuation, so
    they come out before anything is counted.
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".py":
        cells: list[str] = []
        current: list[str] | None = None
        kind: str | None = None
        for raw in text.splitlines():
            match = CELL.match(raw)
            if match is not None:
                if kind == "markdown" and current:
                    cells.append("\n".join(current))
                kind = "markdown" if match.group("rest").strip() == "[markdown]" else "code"
                current = []
                continue
            if current is not None and raw.strip() not in DELIMITER:
                current.append(raw)
        if kind == "markdown" and current:
            cells.append("\n".join(current))
        text = "\n\n".join(cells)
    else:
        text = FRONT_MATTER.sub("", text)
        text = STYLE_BLOCK.sub(" ", text)
        text = HTML_COMMENT.sub(" ", text)
    text = FENCE.sub(" ", text)
    text = "\n".join(line for line in text.splitlines() if not line.strip().startswith("|"))
    text = INLINE_CODE.sub("X", text)
    return HTML_TAG.sub(" ", text)


def budgets(path: Path) -> list[str]:
    """Report every sentence shape over its cap in one file."""
    text = prose(path)
    problems: list[str] = []
    for name, pattern, cap in BUDGETS:
        count = len(pattern.findall(text))
        if count > cap:
            problems.append(f"{path.relative_to(ROOT)}: {name}: {count}, over the cap of {cap}")
    return problems


def check(path: Path) -> list[str]:
    problems: list[str] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for char, name in DASHES.items():
            if char in line:
                problems.append(f"{path.relative_to(ROOT)}:{lineno}: {name} in {line.strip()[:80]!r}")
        for word, pattern in PATTERNS:
            if pattern.search(line):
                problems.append(f"{path.relative_to(ROOT)}:{lineno}: banned phrase {word!r} in {line.strip()[:80]!r}")
    return problems


def main(argv: list[str]) -> int:
    if argv:
        paths = [Path(a).resolve() for a in argv]
    else:
        paths = sorted(p for pattern in DEFAULT_GLOBS for p in ROOT.glob(pattern))
    # This file quotes every banned word, so checking it would always fail.
    paths = [path for path in paths if path.resolve() != SELF]
    budgeted = {p.resolve() for pattern in BUDGETED for p in ROOT.glob(pattern)}
    problems: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        problems.extend(check(path))
        if path.resolve() in budgeted:
            problems.extend(budgets(path))
    for problem in problems:
        print(problem)
    print(f"checked {len(paths)} files, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
