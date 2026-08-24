# Slides: *Programming a Superconducting Qubit*

A [Marp](https://marp.app/) deck, written in Markdown. It is a **thin framing deck**: title, why
pulse-level control, the state of control software in 2026, links and QR codes, thirty seconds of
vocabulary, then a divider and one or two slides per tutorial part naming the experiment and the
feature it forces. Three diagrams carry the structure. The teaching happens in
[`../notebooks/`](../notebooks/); these slides orient and recap.

- [`qprogram_tutorial.md`](qprogram_tutorial.md): the deck source. Edit this.
- `qprogram_tutorial.html`: the rendered deck, produced by the Marp CLI command below. It reads
  `img/` from alongside itself, so keep the two together.
- [`img/`](img/): the three diagrams (`stack.svg` the layer stack, `anatomy.svg` a Rabi program as a
  tree, `plan.svg` the real-time versus host-side split) and the three QR codes
  (`qr-tutorial.svg`, `qr-qprogram.svg`, `qr-docs.svg`).

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
