# Slides: *Programming a Superconducting Qubit*

A [Marp](https://marp.app/) deck, written in Markdown. It is a **thin framing deck**: title, why a
chip arrives with no numbers on it, the state of control software in 2026, links and QR codes, the
device under test, thirty seconds of vocabulary, then a divider and two or three slides per tutorial
part. Three diagrams carry the structure. The teaching happens in
[`../notebooks/`](../notebooks/); these slides orient and recap.

Every content slide carries at least one concrete thing, a number, a formula, a `.qp` excerpt, or a
diff, and the speaker carries the rest. A slide that is five compressed claims competes with the
person talking over it, so `tools/check_style.py` now applies its sentence-shape budgets to this
file as well as to `sources/*.py`.

- [`qprogram_tutorial.md`](qprogram_tutorial.md): the deck source. Edit this.
- `qprogram_tutorial.html`: the rendered deck, produced by the Marp CLI command below. It reads
  `img/` from alongside itself, so keep the two together.
- [`img/`](img/): five diagrams and three QR codes (`qr-tutorial.svg`, `qr-qprogram.svg`,
  `qr-docs.svg`).

| Diagram | Shows | Slide |
|---|---|---|
| `rack.svg` | the signal chain, rack to fridge to chip and back | From a gate to a voltage and back |
| `buses.svg` | instrument ports to bus names to chip, and what each bus kind accepts | A bus is one signal path |
| `timing.svg` | per-bus cursors, and what `sync` does about them | Part 1: every bus keeps its own clock |
| `stack.svg` | the software layers, script to instruments | The architecture |
| `anatomy.svg` | a Rabi program as a tree | Anatomy of a Rabi program |
| `plan.svg` | the real-time versus host-side split | One program, two domains |

`rack.svg` and `buses.svg` exist because most of the room writes circuits and has never seen a
control rack. They come early, before the deck asks anyone to care about a capability token.

### Diagrams worth adding

Two gaps, listed so the decision is visible rather than forgotten. Neither blocks the current
deck.

- **A rotation figure**: envelope area against rotation angle, carrier phase against axis, one Bloch
  sphere and one envelope side by side. It would firm up the "What a gate turns into" slide. Lower
  priority, because Part 1 of the notebooks already plots a real DRAG envelope.
- **An IQ-plane figure** for single-shot readout. Deliberately *not* drawn: Part 4 plots 1200 real
  simulated shots with a fitted threshold, and a schematic version would be strictly worse. If the
  measurement slide ever needs a picture, take the figure out of the notebook.

## Where the diagrams live

Diagrams live here rather than in the notebooks on purpose. A notebook is opened from two directory
depths in this repo and from Colab with no repo at all, so a relative image path is broken in at
least one of the three. The notebooks carry the same content as text figures and tables, which
render everywhere.

## Present or edit

- **Easiest:** VS Code with the **"Marp for VS Code"** extension. Live preview, presenter mode, and
  one-click export to HTML, PDF, or PPTX.
- **Browser:** render `qprogram_tutorial.html` (see below) and open it, with the `img/` folder next to
  it. Arrow keys navigate, `f` goes fullscreen, `p` opens the presenter view.

Bring the HTML on a USB stick as the fallback. It needs no network and no Node install, which is the
right thing to have when the conference room projector is the only thing that works.

## Re-render with the Marp CLI

```bash
cd slides

# HTML (no browser needed)
npx @marp-team/marp-cli@latest qprogram_tutorial.md --html -o qprogram_tutorial.html

# PDF or PPTX (needs a local Chrome or Chromium; --allow-local-files lets it read img/)
npx @marp-team/marp-cli@latest qprogram_tutorial.md --pdf  --allow-local-files
npx @marp-team/marp-cli@latest qprogram_tutorial.md --pptx --allow-local-files
```

The deck uses KaTeX math (`$...$`), a custom teal theme in an inline `<style>` block (accent
`#0f766e`, soft accent `#e6f4f1`), and `class:` directives for the title and divider slides. Diagrams
are sized by height (`![h:520](img/stack.svg)`) so they fit 16:9 without cropping.

## Regenerate the QR codes

The three codes are made with [segno](https://segno.readthedocs.io/) (`pip install segno`). All three
are pinned to QR version 4, so they come out the same physical size and sit on the slide in a row
without one looking denser than the others.

```bash
cd slides

python -c "import segno; segno.make('https://github.com/qilimanjaro-tech/qce26-qprogram-tutorial', version=4).save('img/qr-tutorial.svg', scale=6, border=2, dark='#0f766e', light='#fff')"
python -c "import segno; segno.make('https://github.com/qilimanjaro-tech/qprogram', version=4).save('img/qr-qprogram.svg', scale=6, border=2, dark='#0f766e', light='#fff')"
python -c "import segno; segno.make('https://qilimanjaro-tech.github.io/qprogram', version=4).save('img/qr-docs.svg', scale=6, border=2, dark='#0f766e', light='#fff')"
```

Those three commands reproduce the committed files byte for byte. Drop the styling arguments if you
want plain black codes on a transparent ground:

```bash
python -c "import segno; segno.make('<url>').save('img/qr-tutorial.svg', scale=6)"
```

Point a phone at each one after you regenerate. A QR code that scans on your monitor and fails from
the back of the room is usually too small on the slide, not wrong in the file.
