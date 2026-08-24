#!/usr/bin/env python3
"""Check the tutorial text against the house style.

Two rules, both mechanical:

1. No em dashes or en dashes. Use a comma, a colon, parentheses, or two sentences.
2. No filler vocabulary from the banned list below.

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
    problems = [problem for path in paths if path.is_file() for problem in check(path)]
    for problem in problems:
        print(problem)
    print(f"checked {len(paths)} files, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
