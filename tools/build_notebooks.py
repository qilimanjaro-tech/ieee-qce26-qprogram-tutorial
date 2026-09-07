#!/usr/bin/env python3
"""Build the tutorial notebooks from the percent-format sources in `sources/`.

Each `sources/NN_name.py` is a valid Python script *and* a notebook description. Cells are
separated by `# %%` markers:

    # %% [markdown]        a markdown cell: exactly one raw triple-quoted string
    # %%                   a code cell that appears in both notebook flavours
    # %% solution          a code cell that appears only in notebooks/solutions/
    # %% stub              a code cell that appears only in notebooks/ (attendee version)

Markdown lives in string literals and stub cells are comments, so every source file runs as a
plain script. That is the point: `python sources/02_basics.py` executes the same code
the notebook does, which is how the material is verified.

Usage:

    python tools/build_notebooks.py              # build both flavours
    python tools/build_notebooks.py --execute    # ... and run the solutions to embed outputs
    python tools/build_notebooks.py --check      # validate the sources without writing anything
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
ATTENDEE = ROOT / "notebooks"
SOLUTIONS = ATTENDEE / "solutions"

MARKER = re.compile(r"^# %%(?P<rest>.*)$")
KERNEL = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.13"},
}


@dataclass
class Cell:
    kind: str  # "markdown" | "code"
    flavour: str  # "both" | "solution" | "stub"
    lines: list[str] = field(default_factory=list)

    @property
    def source(self) -> str:
        return "\n".join(self.lines).strip("\n")


class SourceError(Exception):
    """A source file that does not follow the format."""


def parse(path: Path) -> list[Cell]:
    """Split one source file into cells, validating the format as we go."""
    cells: list[Cell] = []
    current: Cell | None = None
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = MARKER.match(raw)
        if match is None:
            if current is None:
                if raw.strip():
                    msg = f"{path.name}:{lineno}: content before the first '# %%' marker"
                    raise SourceError(msg)
                continue
            current.lines.append(raw)
            continue
        rest = match.group("rest").strip()
        if rest == "[markdown]":
            current = Cell("markdown", "both")
        elif rest == "":
            current = Cell("code", "both")
        elif rest in {"solution", "stub"}:
            current = Cell("code", rest)
        else:
            msg = f"{path.name}:{lineno}: unknown cell marker '# %% {rest}'"
            raise SourceError(msg)
        cells.append(current)

    cells = [cell for cell in cells if cell.source]
    _validate(path, cells)
    return cells


def _validate(path: Path, cells: list[Cell]) -> None:
    if not cells:
        msg = f"{path.name}: no cells found"
        raise SourceError(msg)
    if cells[0].kind != "markdown":
        msg = f"{path.name}: the first cell must be markdown (the title cell)"
        raise SourceError(msg)
    for index, cell in enumerate(cells):
        if cell.kind == "markdown":
            text = cell.source
            if not (text.startswith(('r"""', "r'''")) and text.endswith(('"""', "'''"))):
                msg = f"{path.name}: markdown cell {index} must be a single r-string literal"
                raise SourceError(msg)
        if cell.flavour == "stub":
            previous = cells[index - 1] if index else None
            if previous is None or previous.flavour != "solution":
                msg = f"{path.name}: '# %% stub' cell {index} must follow its '# %% solution' cell"
                raise SourceError(msg)
        if cell.flavour == "solution":
            following = cells[index + 1] if index + 1 < len(cells) else None
            if following is None or following.flavour != "stub":
                msg = f"{path.name}: '# %% solution' cell {index} must be followed by a '# %% stub' cell"
                raise SourceError(msg)


def markdown_body(text: str) -> str:
    """Strip the r-string wrapper off a markdown cell."""
    body = text[1:] if text.startswith("r") else text
    quote = body[:3]
    return body[3:-3].strip("\n")


def to_notebook(cells: list[Cell], flavour: str) -> dict:
    """Render the cells for one notebook flavour ('solution' or 'stub')."""
    keep = "solution" if flavour == "solution" else "stub"
    out = []
    for cell in cells:
        if cell.flavour not in {"both", keep}:
            continue
        # nbformat 4.5 wants an id per cell. Derive it from the position so a rebuild of an
        # unchanged source produces a byte-identical notebook.
        cell_id = f"cell-{len(out):03d}"
        if cell.kind == "markdown":
            out.append(
                {
                    "cell_type": "markdown",
                    "id": cell_id,
                    "metadata": {},
                    "source": _split(markdown_body(cell.source)),
                }
            )
        else:
            out.append(
                {
                    "cell_type": "code",
                    "id": cell_id,
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": _split(cell.source),
                }
            )
    return {"cells": out, "metadata": KERNEL, "nbformat": 4, "nbformat_minor": 5}


def _split(text: str) -> list[str]:
    """nbformat wants a list of lines, each keeping its trailing newline except the last."""
    lines = text.split("\n")
    return [line + "\n" for line in lines[:-1]] + [lines[-1]]


def carry_outputs(executed: dict, target: dict) -> dict:
    """Copy outputs from the executed solution notebook onto the attendee notebook.

    Cells are matched by source text, so the exercise stubs (whose source differs) stay empty
    while every shared cell keeps the output the reader will see.
    """
    by_source = {
        "".join(cell["source"]): cell
        for cell in executed["cells"]
        if cell["cell_type"] == "code"
    }
    for cell in target["cells"]:
        if cell["cell_type"] != "code":
            continue
        match = by_source.get("".join(cell["source"]))
        if match is not None:
            cell["outputs"] = match.get("outputs", [])
            cell["execution_count"] = match.get("execution_count")
    return target


def write(path: Path, notebook: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def execute(path: Path, timeout: int = 900) -> None:
    """Run a notebook in place with nbconvert.

    `MPLBACKEND` is stripped from the child environment on purpose. A non-interactive backend
    inherited from the shell turns every `plt.show()` into a warning and embeds no figure, so a
    whole set of notebooks can ship with the pictures missing and nothing failing.
    """
    env = {key: value for key, value in os.environ.items() if key != "MPLBACKEND"}
    subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "nbconvert",
            "--to",
            "notebook",
            "--execute",
            "--inplace",
            f"--ExecutePreprocessor.timeout={timeout}",
            str(path),
        ],
        check=True,
        env=env,
    )


def count_figures(notebook: dict) -> int:
    """How many outputs carry an image. Zero after an execute means the backend was wrong."""
    return sum(
        1
        for cell in notebook["cells"]
        for output in cell.get("outputs", [])
        if any(key.startswith("image/") for key in output.get("data", {}))
    )


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--execute", action="store_true", help="run the solution notebooks to embed outputs")
    cli.add_argument("--check", action="store_true", help="validate the sources and write nothing")
    cli.add_argument("sources", nargs="*", help="specific source files (default: all of sources/*.py)")
    args = cli.parse_args(argv)

    paths = [Path(p) for p in args.sources] if args.sources else sorted(SOURCES.glob("*.py"))
    if not paths:
        print("no sources found", file=sys.stderr)
        return 1

    for path in paths:
        cells = parse(path)
        counts = {
            "markdown": sum(1 for c in cells if c.kind == "markdown"),
            "code": sum(1 for c in cells if c.kind == "code" and c.flavour == "both"),
            "exercises": sum(1 for c in cells if c.flavour == "stub"),
        }
        if args.check:
            print(f"{path.name}: ok ({counts['markdown']} md, {counts['code']} code, {counts['exercises']} exercises)")
            continue

        name = path.stem + ".ipynb"
        solution = SOLUTIONS / name
        attendee = ATTENDEE / name
        write(solution, to_notebook(cells, "solution"))
        write(attendee, to_notebook(cells, "stub"))
        print(f"{path.name} -> notebooks/{name}, notebooks/solutions/{name}")

        if args.execute:
            execute(solution)
            done = json.loads(solution.read_text(encoding="utf-8"))
            write(attendee, carry_outputs(done, to_notebook(cells, "stub")))
            figures = count_figures(done)
            print(f"  executed ({figures} figures) and copied outputs into notebooks/{name}")
            if not figures:
                print(f"  WARNING: {name} embedded no figures; check MPLBACKEND", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
