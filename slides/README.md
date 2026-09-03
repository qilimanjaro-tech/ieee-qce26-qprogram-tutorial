# Slides: *Programming a Superconducting Qubit*

A [Marp](https://marp.app/) deck, written in Markdown. **The concepts live here.** The deck opens
with the physics and the hardware, a transmon, the fridge and the rack around it, how a gate becomes
a voltage, what a measurement really returns, and what decoherence costs, then argues why any of
that needs a language of its own. Only after all of that does QProgram appear. The notebooks in
[`../notebooks/`](../notebooks/) carry the code and explain the experiments; they leave the
background to these slides.

Seventy-two slides, roughly in four movements: logistics, the foundations block, the QProgram block,
then two to five slides per tutorial part. Ten diagrams carry the structure.

Every content slide carries at least one concrete thing, a number, a formula, a `.qp` excerpt, or a
diff, and the speaker carries the rest. A slide that is five compressed claims competes with the
person talking over it, so `tools/check_style.py` applies its sentence-shape budgets to this file
and to the deck as well as to `sources/*.py`.

- [`qprogram_tutorial.md`](qprogram_tutorial.md): the deck source. Edit this.
- `qprogram_tutorial.html`: the rendered deck, produced by the Marp CLI command below. It reads
  `img/` from alongside itself, so keep the two together.
- [`img/`](img/): ten diagrams and three QR codes (`qr-tutorial.svg`, `qr-qprogram.svg`,
  `qr-docs.svg`).

| Diagram | Shows | Slide |
|---|---|---|
| `transmon.svg` | the circuit, the cosine well, and the ladder that crowds as you climb | Two circuit elements, and the ladder that falls out |
| `rack.svg` | the signal chain, rack to fridge to chip and back | From a gate to a voltage and back |
| `fridge.svg` | the stages, attenuation going down and amplification coming up | The fridge, stage by stage |
| `rotation.svg` | carrier phase as the axis, envelope area as the angle | The two knobs, drawn |
| `dispersive.svg` | two dips $2\chi$ apart, the chain after the chip, and the IQ clouds | The measurement chain, end to end |
| `buses.svg` | instrument ports to bus names to chip, and what each bus kind accepts | A bus is one signal path |
| `stack.svg` | the software layers, script to instruments | The architecture |
| `timing.svg` | per-bus cursors, and what `sync` does about them | Part 1: every bus keeps its own clock |
| `anatomy.svg` | a Rabi program as a tree | Anatomy of a Rabi program |
| `plan.svg` | the real-time versus host-side split | One program, two domains |

The first five exist because most of the room writes circuits and has never seen a control rack.
They come early, before the deck asks anyone to care about a capability token.

### Diagrams worth adding

One gap, listed so the decision is visible rather than forgotten. It does not block the deck.

- **A two-qubit gate figure**: the flux excursion that brings $|11\rangle$ and $|02\rangle$ together,
  beside the chevron a calibration scan of it produces. "Two qubits, one gate" is currently carried
  by four bullets, and it is the one slide in the foundations block with no picture behind it. Part 6
  of the notebooks scans a real chevron, so the figure could come out of there.

An IQ-plane schematic on its own is deliberately **not** drawn. Part 4 plots 1200 real simulated
shots with a fitted threshold, and a schematic version would be strictly worse. `dispersive.svg`
carries the frequency-domain picture instead, which is the half that makes $2\chi/\kappa$ obvious
rather than asserted.

## Where the diagrams live

Diagrams live here rather than in the notebooks on purpose. A notebook is opened from two directory
depths in this repo and from Colab with no repo at all, so a relative image path is broken in at
least one of the three. The notebooks draw their own figures from the results instead, through
`result.plot(...)` and `waveform.plot()`, which render anywhere.

## Present or edit

The easiest route is VS Code with the "Marp for VS Code" extension, which gives you live preview,
presenter mode, and one-click export to HTML, PDF, or PPTX. In a browser, render
`qprogram_tutorial.html` (see below) and open it with the `img/` folder next to it. Arrow keys
navigate, `f` goes fullscreen, and `p` opens the presenter view.

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
are sized by height (`![h:470](img/stack.svg)`) so they fit 16:9 without cropping.

## Drawing a new diagram

The ten diagrams are hand-written SVG on a `0 0 1600 900` viewBox, with a `<title>` and a prose
`<desc>` for accessibility and the system font stack declared once on the root element. They share
one palette with the deck: accent `#0f766e`, soft accent `#e6f4f1`, ink `#1c1c2e`, muted `#6a6a82`,
panel `#f5f5fa`, white ground. Boxes are `rx="10"` with a 2px stroke, bands are `rx="14"`, and a box
title is 24px bold over 20 to 22px detail lines.

Nothing goes below 18px in that coordinate space, because 900 units of height render at about 470
CSS pixels on the slide. Read `rack.svg` before writing a new one; it is the file the rest were
matched to.

## Regenerate the QR codes

The three codes are made with [segno](https://segno.readthedocs.io/) (`pip install segno`). All three
are pinned to QR version 4, so they come out the same physical size and sit on the slide in a row
without one looking denser than the others.

```bash
cd slides

python -c "import segno; segno.make('https://github.com/qilimanjaro-tech/ieee-qce26-qprogram-tutorial', version=4).save('img/qr-tutorial.svg', scale=6, border=2, dark='#0f766e', light='#fff')"
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
