---
marp: true
size: 16:9
paginate: true
math: katex
title: Programming a Superconducting Qubit with QProgram
footer: 'Programming a Superconducting Qubit · QCE 2026'
---

<style>
:root {
  --accent: #0f766e;
  --accent-soft: #e6f4f1;
  --ink: #1c1c2e;
}
section {
  font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 26px;
  color: var(--ink);
  padding: 56px 72px;
  background: #ffffff;
}
h1, h2 { color: var(--accent); font-weight: 700; line-height: 1.1; }
h1 { font-size: 1.9em; }
h2 { font-size: 1.35em; }
h3 { color: var(--ink); }
strong { color: var(--accent); }
a { color: var(--accent); text-decoration: none; }
ul, ol { line-height: 1.45; }
code {
  background: var(--accent-soft); color: #0b5f58;
  padding: 2px 7px; border-radius: 5px; font-size: 0.86em;
}
pre { font-size: 0.72em; line-height: 1.35; }
pre code { background: none; padding: 0; }
table { font-size: 0.76em; }
th { background: var(--accent-soft); color: var(--accent); }
blockquote { font-size: 0.86em; color: #4a4a62; border-left: 4px solid var(--accent); padding-left: 16px; }
footer { color: #9a9ab0; font-size: 0.5em; }
section::after { color: #b6b6c8; font-weight: 600; }

section.lead { text-align: center; justify-content: center; }
section.lead h1 { font-size: 2.4em; margin-bottom: 0.1em; }
section.lead .sub { font-size: 1.15em; color: #55556e; }
section.lead .meta { font-size: 0.8em; color: #8a8aa0; margin-top: 1.4em; }

section.divider {
  background: linear-gradient(135deg, #0f766e 0%, #08403c 100%);
  color: #fff; justify-content: center;
}
section.divider h1, section.divider h2, section.divider h3 { color: #fff; }
section.divider strong { color: #ffd866; }
section.divider .kicker { font-size: 0.8em; letter-spacing: .18em; text-transform: uppercase; opacity: .8; }
section.divider code { background: rgba(255,255,255,.18); color: #fff; }

.cap { font-size: 0.72em; color: #6a6a82; text-align: center; margin-top: 6px; }
.center { text-align: center; }
.small { font-size: 0.82em; }

.qrgrid { display: flex; gap: 40px; justify-content: center; align-items: flex-start; margin-top: 28px; }
.qrgrid > div { text-align: center; width: 300px; }
.qrgrid img { width: 280px; height: 280px; background: #fff; padding: 8px; border: 1px solid #e6e6ef; border-radius: 10px; }
.qrgrid .lbl { font-weight: 700; color: var(--accent); margin: 14px 0 4px; font-size: 0.95em; }
.qrgrid .url { font-size: 0.72em; line-height: 1.35; word-break: break-word; }
.qrgrid .url a { color: #55556e; }
</style>

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: '' -->

# Programming a Superconducting Qubit

<p class="sub">Pulse-Level Control and Calibration with QProgram</p>

<p class="meta">IEEE Quantum Week · QCE 2026</p>

---

## Introduction

- **Vyron Vasileiadis**, Tech Lead at **Qilimanjaro Quantum Tech** · vyron@qilimanjaro.tech
- **Qilimanjaro** builds quantum computers and the software stack that drives them.
- **QProgram** is the pulse-level layer of that stack: an open-source Python DSL for the pulses, sweeps, and measurements a calibration is made of.
- It ships a pure-Python reference platform, which is why every experiment today runs on your laptop.

---

## Why pulse-level control

- A circuit says "apply $X$ to qubit 0". An instrument needs a 40 ns envelope on an IQ pair at 4.85 GHz, and somebody had to measure that number.
- **Calibration is where lab time goes**, and calibration lives below the gate: spectroscopy, Rabi, $T_1$, Ramsey, readout.
- There is no gate for "sweep the readout frequency across 81 points and average 200 shots at each one".
- The same chip is a good chip or a bad chip depending on how well those numbers are tuned.
- So the control layer has to say sweeps, waveform parameters, timing, and feedback out loud.

---

## The state of control software in 2026

- Every vendor ships a sequencer dialect: assembly-shaped, timing-exact, specific to one box.
- Calibration code gets written in that dialect, so the physics you learned is welded to the rack you learned it on.
- A second rack means rewriting experiments that were already correct, and re-earning trust in them.
- One split decides whether a sweep is even possible: sequencer loop, or control-PC loop. Most tools make you hard-code it on line one.
- Physics moves between labs. Control code, today, mostly does not.

---

## What QProgram is, and what it leaves alone

- A Python builder that produces an **AST**. `program.play(...)` appends a node, it does not send bytes.
- A **text format**, `.qp`, that the tree round-trips through, so an experiment is a file you can diff, review, and rerun next year.
- A **capability protocol**: a platform declares what it supports per bus and per domain, and a program is checked against that before anything reaches hardware.
- A **reference platform** that interprets the tree in pure Python, which is the oracle vendor compilers get tested against.
- It is not a compiler, a scheduler, or a physics model. Those stay with the vendor, behind one interface.

---

## Links & QR codes

<div class="qrgrid">
<div>
<img src="img/qr-tutorial.svg" alt="QR code for the QCE 2026 tutorial repository" />
<div class="lbl">This tutorial</div>
<div class="url"><a href="https://github.com/qilimanjaro-tech/qce26-qprogram-tutorial">github.com/qilimanjaro-tech/<br>qce26-qprogram-tutorial</a></div>
</div>
<div>
<img src="img/qr-qprogram.svg" alt="QR code for the QProgram GitHub repository" />
<div class="lbl">QProgram source</div>
<div class="url"><a href="https://github.com/qilimanjaro-tech/qprogram">github.com/qilimanjaro-tech/qprogram</a></div>
</div>
<div>
<img src="img/qr-docs.svg" alt="QR code for the QProgram documentation" />
<div class="lbl">Documentation</div>
<div class="url"><a href="https://qilimanjaro-tech.github.io/qprogram">qilimanjaro-tech.github.io/qprogram</a></div>
</div>
</div>

---

## Follow along

**Two ways to run everything, pick one:**

- **Local**: `pip install "qprogram[viz]" scipy` (Python 3.11 to 3.14), then open the notebooks.
- **Colab**: the first cell of every notebook installs what is missing, pinned to `0.1.0`.

**Right now:** open and run `notebooks/00_setup.ipynb`. Its last cell draws a resonator dip near 7.2 GHz. If you see the dip, you are ready.

> No hardware, no vendor package, no cloud account. The reference platform is part of the wheel.

---

## How we will work

- **Coding first.** These slides are the map. The work is in the notebooks.
- Each part: a short concept, a live code-along, then one or two 🧩 exercises on real problems.
- Two notebook flavours: `notebooks/` has blank `# TODO` cells, `notebooks/solutions/` has the answers and the outputs.
- Every snippet was run against `qprogram 0.1.0`. What a slide claims, a cell proves.
- Interrupt me. Lab stories are welcome, above all the ones that contradict the slide.

---

## Schedule

| Part | Notebook | Topic | Time |
|---|---|---|---|
| 1 | `01_pulse_programs` | The program is data | 35 min |
| 2 | `02_sweeps_and_results` | Sweeps, averaging, and results | 35 min |
| 3 | `03_finding_the_qubit` | Finding and driving the qubit | 40 min |
|  |  | break | 15 min |
| 4 | `04_coherence_and_feedback` | Coherence, single shots, feedback | 40 min |
| 5 | `05_one_program_many_machines` | Capabilities, plans, porting | 30 min |
| 6 | `06_extending_and_shipping` | Extending, shipping, capstone | 25 min |

3 hours 40 minutes with the break, which lands after Part 3. Times are approximate and we flex with
the room: Part 6's capstone and the second exercise in Parts 2 and 5 are the pieces built to come
out if we run long.

---

## What you will build

- a **calibrated qubit**: resonator frequency, qubit frequency, and a pi pulse, all fitted from raw sweeps (Parts 2 and 3);
- a **coherence set**: $T_1$, $T_2^{*}$, and $T_2$ from echo, built out of reusable pulse fragments (Part 4);
- **single-shot readout** with a threshold, and **active reset** that reads the outcome and acts on it (Part 4);
- the **same calibration ported to a second rack**, checked against that rack before it runs (Part 5);
- your **own waveform, sweep source, and vendor operation**, then the whole bring-up as one script (Part 6).

By the end: a calibration set for a simulated qubit, and the files that produced it.

---

## The architecture

![h:480](img/stack.svg)

<p class="cap">Your script builds a tree. Validation decides what runs where. The platform compiles and runs it. The <code>.qp</code> and <code>.wfl</code> files fall out as artifacts.</p>

---

## 30 seconds of vocabulary

- **Bus**: a named signal path, `q[0].drive`. A string that also knows its channel type and whether it can acquire.
- **Waveform**: an envelope as data, `Gaussian(amplitude=0.3, duration=40, sigma=10)`. Comparable, serializable, swappable.
- **Sweep source**: what a loop iterates over. `Range`, `Linspace`, `Values`, `Logspace`, `File`. One loop block, pluggable source.
- **Average**: the shot loop. It adds no dimension to the result, it averages one away.
- **Measurement handle**: what `measure()` returns. Use it to pull the array out, and to read `handle.state` for feedback.

---

## One more word: capability

- A **token** is a feature name: `op.play`, `block.conditional`, `sweep.logspace`, `waveform.iq_drag`, `measure.fields.state`.
- A platform declares tokens per **(bus, domain)** slot: what this line can do in real time, and what it can do host-side.
- **Limits** are numbers (`max_loop_nesting`). **Predicates** are functions that inspect the actual node and its operands.
- Validation returns **diagnostics** and never raises. The caller decides what an error means.
- Alongside them comes an **execution plan**: every node labelled `[rt]`, `[host]`, `[rt|host]`, or `[--]`.

---

## The simulator, honestly

- `qp.simulate(program, model=...)` walks the tree in Python. Loops bind variables, measurements write records.
- It models the **shape** of an experiment: nesting, averaging, one record per `measure`, `NaN` where a conditional arm never ran.
- It models **no timing and no waveform physics**. `wait` and `sync` change nothing in the numbers that come back.
- The numbers come from a `MeasurementModel` you write. A $T_1$ curve decays because the model reads `env["delay"]`, not because a qubit relaxed.
- That is the deal for today: the **program** and the **analysis** are real, the fridge is a stand-in. A fit that works here works on data.

---

<!-- _class: divider -->

<p class="kicker">Part 1 · notebooks/01_pulse_programs.ipynb</p>

# The Program Is Data

### A readout pulse, a drive pulse, and the tree they build

---

## Part 1: readout and drive force buses and operations

- The experiment: play a 2 us readout tone and acquire it, then a 40 ns drive pulse on a second line.
- A **bus** is a signal path. `BusSchema.transmon()` hands you `q[0].drive` and `q[0].readout`, and the readout line knows it has an ADC.
- `BusRef` subclasses `str`, so it is a plain string everywhere downstream while still carrying `element`, `idx`, `kind`, `channel`, `acquires`.
- Two checks come for free: an IQ waveform on a single-channel line, and a `measure` on a line with no ADC. Both raise at build time.
- A raw string bus, `"drive_q0"`, works and skips every check. Sometimes that is what you want. Know that you chose it.

---

## Part 1: waveforms are data, and so is the program

- `play`, `wait`, `sync`, `set_frequency`, `set_phase`, `set_gain`, `set_offset`, `measure`. Each call appends exactly one node.
- Waveforms are value objects: `Gaussian(amplitude=0.3, duration=40, sigma=10)`. Equal by structure, plotted with `envelope()`.
- A waveform can also be a **string alias**, `play(q[0].drive, "pi")`. That alias is the seam calibration data flows through.
- The tree is yours to inspect: `program.body.elements`, `body.walk()`, `program.buses`, `program.variables`.
- `qp.dumps` and `qp.loads` round-trip it. `qp.loads(qp.dumps(p)).body == p.body` is `True`, and the notebook asserts it.

> 🧩 Build a two-qubit prepare-and-read sequence, then edit a `.qp` file by hand and prove what changed.

---

<!-- _class: divider -->

<p class="kicker">Part 2 · notebooks/02_sweeps_and_results.ipynb</p>

# Sweeps, Averaging, and What Comes Back

### Resonator spectroscopy, then a punchout map

---

## Part 2: resonator spectroscopy forces variables and sweeps

- The experiment: sweep the readout frequency across the resonator, average, find the dip. The first measurement on any new chip.
- `program.variable("ro_freq")` declares the swept parameter. Anywhere a number is accepted, an expression is accepted too.
- One loop block, `sweep(var, source)`, with a pluggable source: `Range`, `Linspace`, `Values`, `Logspace`, `File`, plus `Repeat`, `Rotate`, `Concat`.
- `Range` includes its stop value: `Range(0, 10, 2)` gives six points. `Range` and `Linspace` are `linear`, the rest are `arbitrary`, and `Values` of an even ramp is still arbitrary.
- `average(shots=200)` is the shot loop. It adds **no** dimension: `iq` becomes a mean, `state` becomes an excited-state population.

---

## Part 2: punchout forces nested and parallel loops

- The experiment: readout power against readout frequency, watching the resonator slide from $f_r + \chi$ at low power to bare $f_r$ when it saturates.
- Nested `with` statements are nested loops. Result dims are the enclosing sweeps, outermost first, named after your variable ids.
- Results come back as `xarray`: `result.get(m0)` has dims `("ro_amp", "ro_freq", "IQ")`, so `sel` and `plot` behave as you expect.
- `sweep(a, src) | sweep(b, src)` steps two variables in lockstep and yields one dim named `"a|b"` carrying both coordinate arrays. That is a diagonal cut, not a grid.
- Variable `label` and `units` do not reach the xarray coords. Label your axes by hand.

> 🧩 Take the power axis log-spaced with `qp.Logspace`, then write the scan as a parallel pair and explain the dims.

---

## Anatomy of a Rabi program

![h:430](img/anatomy.svg)

<p class="cap">Every node contributes something to the answer: <code>sweep</code> creates an axis, <code>average</code> collapses one, <code>measure</code> creates a record, <code>play</code> carries the variable into the waveform.</p>

---

<!-- _class: divider -->

<p class="kicker">Part 3 · notebooks/03_finding_the_qubit.ipynb</p>

# Finding and Driving the Qubit

### Two-tone spectroscopy, Rabi, and the flux arc

---

## Part 3: qubit spectroscopy forces expressions and the state field

- The experiment: park the readout on $f_r$, sweep a second tone, and watch the population rise at $f_{01}$.
- You need the resonator before you can look for the qubit. That ordering is why Part 2 comes first, in the tutorial and in the lab.
- `measure(..., fields=(MF.STATE,))` asks the platform for a discriminated state, and `average` turns those ones and zeros into a population.
- Expressions are an AST as well: `amp * 0.5`, `qp.eq(a, b)`, `qp.where(cond, x, y)`. Plain `==` on a variable is identity, so reach for `qp.eq` when you mean a condition.
- Then `scipy.optimize.curve_fit` on a Lorentzian, and your fitted $f_{01}$ goes up against the device's true 4.85 GHz.

---

## Part 3: Rabi forces waveform parameters, the flux arc forces host-side loops

- Rabi: sweep the drive amplitude with the variable sitting **inside** the waveform, fit $\sin^2$, read off the pi-pulse amplitude.
- The fitted number becomes a concrete `IQDrag`, bound to the alias `"pi"` through `program.with_waveforms(...)`. The program text holds still while the calibration moves.
- Flux arc: a 2D map of flux bias against drive frequency, `set_offset` on the flux line, and the cosine arc everybody recognises.
- That bias loop steps a slow DAC. It cannot be a sequencer loop, and you never wrote down which kind of loop it was.
- Keep hold of that until Part 5. It is the reason the capability protocol exists at all.

> 🧩 Fit the pi/2 amplitude and check it against half the pi amplitude, then solve the arc for a target frequency.

---

<!-- _class: divider -->

<p class="kicker">Part 4 · notebooks/04_coherence_and_feedback.ipynb</p>

# Coherence, Single Shots, and Feedback

### T1, Ramsey, echo, and a reset that reads the outcome

---

## Part 4: T1, Ramsey, and echo force fragments

- Every coherence experiment is the same three moves with a different middle: prepare, wait, read out.
- A `@fragment` is a named, parameterized sub-program. `program.call(x180, q[0].drive, 0.62)` appends one `Call` node.
- `program.expand()` inlines them: parameters substituted, fragment-local variables renamed, measurement names kept unique. `validate` and `execute` do it for you.
- Fragments round-trip into `.qp` as `fragment` sections ahead of `body:`, so a shared pulse library is a text file too.
- Three fits: exponential for $T_1$, damped cosine for $T_2^{*}$ (the fitted detuning is your frequency correction), exponential again for $T_2$ with echo.

---

## Part 4: single shots force fields, active reset forces conditionals

- One measurement can hand back several fields: `iq` (two numbers), `state` (one number), `raw` (the whole trace). Ask for what you need.
- Single-shot readout: put the shot index in an explicit `sweep` instead of `average`, and every individual shot lands in the array.
- The blobs come from a model you wrote: any object with `sample(bus, env) -> qp.MeasurementSample` and a `raw_samples` attribute.
- Active reset: `measure` the state, then `if_(handle.state == 1)` and play a pi pulse. The arm that did not run holds `NaN`.
- Feedback inside a program used to be a vendor-specific operation. Here it is `if_` / `else_`, and a token a platform either has or does not.

> 🧩 Write the echo experiment from the fragments already defined, then report the population before and after reset.

---

<!-- _class: divider -->

<p class="kicker">Part 5 · notebooks/05_one_program_many_machines.ipynb</p>

# One Program, Many Machines

### The same calibration, a different rack

---

## Part 5: porting forces capability checks

- Two labs, two racks, one experiment. What has to be true before your program reaches an instrument?
- `required_capabilities()` is per node and instance-aware: `Play(Square)` asks for `waveform.square`, `Play(IQDrag)` for `waveform.iq_drag`, `Play("pi")` for `waveform.alias`.
- A descriptor has three parts: per-`(element, kind)` bus profiles, one platform profile for blocks and expressions, and a fallback for raw-string buses.
- Every slot has an `rt` half and a `host` half, and either may be `None`. A flux DAC with no sequencer is `rt=None`, and that one field carries the whole story.
- `qp.validate(program, caps)` returns `(diagnostics, plan)` and never raises. `execute` is what turns an error into an exception.

---

## Part 5: read the plan, then let optimize fix it

```
body
└─ average 200:                                               [host]    ~ forced-host
   └─ for bias in Linspace(start=-0.05, stop=0.15, num=101):  [host]
      ├─ set_offset q[0].flux bias                            [host]
      ├─ play q[0].drive "saturation"                         [rt|host]
      ├─ sync q[0].drive q[0].readout                         [rt|host]
      └─ measure q[0].readout "readout" "weights" ...         [rt|host]
```

- The `average` fell to `[host]` because it contains a host-side-only sweep. A `warning`, not an error: it runs, and it crawls.
- `qp.optimize(program, caps)` rewrites `average { sweep { ... } }` into `sweep { setup; average { ... } }`, and the averaging goes back to real time.
- A bare `program.sync()` broadcasts across every bus in the program, picks up the flux line, and blocks the rewrite. `program.sync([q[0].drive, q[0].readout])` does not.

---

## Part 5: rebind and waveform libraries

- `program.rebind(naming=BusNaming("{kind}_{element}{index}"))` renames every bus structurally, and the refs stay typed, so the file still serializes as paths.
- `rebind(elements={("q", 0): ("q", 3)})` moves the experiment to another qubit. `rebind(schema=...)` moves it to another chip layout.
- `WaveformLibrary` resolves a string alias per bus in three tiers: exact `(element, idx, kind, name)`, then family `(element, kind, name)`, then global `(name,)`.
- Binding is a step you take before running: `program.with_waveforms(library)`. `execute` takes concrete programs and knows nothing about libraries.
- The library lives outside the `.qp` file, in its own `.wfl` format. The experiment is portable, the calibration is local to a fridge, and one file for both would spoil each of them.

> 🧩 Write a predicate that enforces your own rule, then port the Part 3 program to a lab that names buses `drive_q0` style.

---

## One program, two domains

![h:430](img/plan.svg)

<p class="cap">The drive and readout lines sit on a fast sequencer, the flux line on a slow DAC. The bias loop lands host-side, the shot loop stays in hardware, and <code>optimize()</code> is what gets them into that order.</p>

---

<!-- _class: divider -->

<p class="kicker">Part 6 · notebooks/06_extending_and_shipping.ipynb</p>

# Extending the Language and Shipping the Work

### Your own waveform, your own vendor, and the bring-up in one script

---

## Part 6: three extension points, used live

- A **waveform**: subclass `Waveform`, implement `envelope()` and `get_duration()`, decorate with `@qp.register_waveform`. Serialization comes from the constructor signature.
- A **sweep source**: subclass `qp.SweepSource`, declare `KIND` and `TOKEN`, implement `length()` and `values()`. A source may not wrap a callable, and that restriction is worth five minutes of your attention.
- A **vendor namespace**: one `Operation` subclass, one `VendorNamespace` method, four registration calls. Then `program.fridge.set_attenuation(q[0].drive, 20.0)` works on any program.
- The file grows a `require fridge 0.1` line, round-trips, and validates. A platform without the token reports `missing-capability` and names it.
- All three fit in a notebook cell. That is the test of an extension point: no fork, no patch to the core.

---

## Part 6: shipping it

- A `.qp` file is the artifact. Two calibration runs diff as text, and the diff is the physics that moved.
- `python -m qprogram.lsp check run.qp` prints JSON diagnostics and exits non-zero. `explain` prints the plan tree. Neither needs an extra dependency.
- The VS Code extension is that same checker plus a TextMate grammar, so a broken file underlines while you type.
- `PlatformProtocol` is six abstract members: four `get_*` discovery methods, a `capabilities` property, and `execute`. A real platform compiles, uploads, arms, and streams. The reference one interprets, and vendor compilers are tested against it.
- **Capstone**: one script runs the whole bring-up in order, writes a `.qp` per step and a single `.wfl`, and prints your fitted numbers next to the device's true ones.

> 🧩 Add a vendor measurement field or a second vendor operation, then break a `.qp` file and fix it from the checker output.

---

## The bring-up, end to end

**resonator** → **qubit** → **pi pulse** → **coherence** → **single shots** → **active reset** → **ported** → **shipped**

A dozen experiments, one set of primitives:

`BusSchema` · `Waveform` · `Variable` · `SweepSource` · `Fragment` · `MeasurementField`
 → assembled into an **AST** → checked against **capabilities** → run by a swappable **platform**.

> Nothing today needed a vendor package, and nothing today was written twice.

---

## Where to go next

- **Docs**: [qilimanjaro-tech.github.io/qprogram](https://qilimanjaro-tech.github.io/qprogram) · **Source**: [github.com/qilimanjaro-tech/qprogram](https://github.com/qilimanjaro-tech/qprogram)
- The two specifications, `.specs/qprogram-dsl.md` and `.specs/qp-file-format.md`, are the normative reference, and `grammar/qp.lark` is the machine-readable grammar.
- `qprogram-qblox` and `qprogram-qdac` are worked vendor extensions. Read one before you write your own.
- Bring a rule your lab cares about and write it as a predicate. That is the cheapest way to find out whether the protocol fits your rack.
- Issues and pull requests are welcome. The extension points are the API.

---

<!-- _class: lead -->
<!-- _footer: '' -->

# Thank you

<p class="sub">Questions, and the notebooks are yours to keep</p>

<p class="meta">vyron@qilimanjaro.tech · QCE 2026</p>
