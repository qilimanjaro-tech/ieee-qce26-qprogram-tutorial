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
.big { font-size: 1.5em; color: var(--accent); font-weight: 700; text-align: center; margin: 0.3em 0; }

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

## The presenters

- **Vyron Vasileiadis**, Tech Lead at **Qilimanjaro Quantum Tech** · vyron@qilimanjaro.tech
- **Flavie Le Bars**, Quantum Software Engineer at **Qilimanjaro Quantum Tech** · flavie.lebars@qilimanjaro.tech
- **Qilimanjaro** builds quantum computers and the software stack that drives them.
- **QProgram** is the pulse-level layer of that stack, an open-source Python DSL.

---

## Links

<div class="qrgrid">
<div>
<img src="img/qr-tutorial.svg" alt="QR code for the QCE 2026 tutorial repository" />
<div class="lbl">This tutorial</div>
<div class="url"><a href="https://github.com/qilimanjaro-tech/ieee-qce26-qprogram-tutorial">github.com/qilimanjaro-tech/<br>ieee-qce26-qprogram-tutorial</a></div>
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

- **Local**: `pip install "qprogram[viz]==0.1.0"`, Python 3.11 to 3.14.
- **Colab**: the first cell of each notebook installs what is missing.
- The Advanced notebook adds two vendor packages, and its own first cell installs them.
- No hardware and no cloud account, since the reference platform ships in the wheel.
- Open `notebooks/01_introduction.ipynb` now. Its first two cells are the environment check.

---

## How we work

- The slides are the map, and the notebooks are the work.
- Two movements of concepts first, covered by no notebook.
- Then one part per notebook, each a code-along and one 🧩 exercise.
- `notebooks/` holds the `# TODO` cells, `notebooks/solutions/` the answers.
- Interrupt me, above all with a lab story that contradicts the slide.

---

## Schedule

| Part | Notebook | Topic | Time |
|---|---|---|---|
| | | the chip, the rack, and why a language of its own | 40 min |
| 1 | `01_introduction` | The program is data | 25 min |
| 2 | `02_basics` | Variables, sweeps, and results | 25 min |
| 3 | `03_advanced` | Fragments, feedback, extending, and the machine | 75 min |
| | | questions and close | 10 min |

Three notebooks, three parts, one 🧩 exercise each. The break between the two sessions lands after Part 2, so the whole of the second session is Part 3, whose six sections stand on their own and can be taken in any order.

---

## What you will build

- a **pulse program** you can read, save, load and diff (Part 1)
- a **resonator scan**, a **two-dimensional map**, and a **lockstep sweep** (Part 2)
- **active reset**, one measurement deciding the next pulse
- your **own waveform, sweep source, and vendor operation**
- a **platform** of your own, and a rack's **execution plan** (all three in Part 3)

---

<!-- _class: divider -->

<p class="kicker">Concepts · slides only</p>

# The chip and the rack

### What a gate has to become before an instrument can emit it

---

## The harmonic problem

- What you calibrate is an LC circuit on a chip at 10 mK.
- Its energy levels are evenly spaced.
- A tone driving $|0\rangle \to |1\rangle$ drives $|1\rangle \to |2\rangle$ as hard.
- So no two levels can be addressed alone, and there is no qubit yet.

---

## The Josephson junction

- A Josephson junction replaces the inductor.
- Two aluminium films with a nanometre of oxide between them.
- Its current goes as $I_c\sin\varphi$, so it is nonlinear.
- Its inductance therefore depends on the current already flowing.
- It is the only nonlinear element in the circuit.

---

## Anharmonicity

$$\hat H = 4E_C\hat n^2 - E_J\cos\hat\varphi$$

- A parabola gives evenly spaced rungs.
- A cosine well gets shallower as you climb, so the rungs crowd.
- $f_{01}$ and $f_{12}$ then differ by the anharmonicity $\alpha$, here $-300$ MHz.
- A pulse narrower in spectrum than $|\alpha|$ addresses the bottom two levels.

---

## The transmon

![h:450](img/transmon.svg)

<p class="cap">A capacitor across a Josephson junction, and the crowded ladder the cosine well gives it.</p>

---

## The design ratio

- $E_J/E_C$ large puts the phase deep in the cosine well.
- Stray charge then stops shifting the levels.
- Charge dispersion falls as $e^{-\sqrt{8E_J/E_C}}$, anharmonicity only as $-E_C$.
- Above roughly 50 the charge sensitivity has gone.
- The ratio trades charge noise against gate speed.

---

## Why 5 GHz

- The thermal scale $hf/k_B$ at $f_{01}$ is 233 mK.
- A 10 mK stage sits far below it.
- The band is also where coax, circulators and generators can be bought.
- Real devices sit warmer, at 40 to 60 mK, leaving about one percent excited.
- Part 3 resets that population rather than waiting for it.

---

## Tuning with flux

- Split the junction into a loop of two and the effective $E_J$ becomes tunable.
- A DC bias threads flux through that loop and moves $f_{01}$.
- The curve is a square root of a cosine, and its flat top is the **sweet spot**.
- There the slope against bias vanishes, so flux noise stops moving the frequency.

$$f_{01}(V) = f_{\max}\sqrt{\left|\cos\frac{\pi(V - V_0)}{V_\Phi}\right|}$$

---

## The control rack

![h:470](img/rack.svg)

<p class="cap">Three lines down to the chip and one line back, with attenuation going in and gain coming out.</p>

---

## Attenuation

- A 50 ohm resistor at room temperature radiates into every mode.
- At the drive frequency that is 1300 photons per mode.
- The qubit sits on one of them.
- Each stage's attenuator therefore re-thermalizes the line to its own plate.
- Microwatts at the generator arrive as attowatts at the chip.

---

## The fridge

![h:460](img/fridge.svg)

<p class="cap">Attenuation stage by stage going down, and the coldest amplifier sets the noise figure for the rest.</p>

---

## Three lines

| line | what runs on it | what it does |
|---|---|---|
| **drive** | a microwave tone near $f_{01}$ = 4.85 GHz | rotates the state |
| **readout** | a microwave tone near $f_r$ = 7.20 GHz | interrogates a resonator coupled to the qubit |
| **flux** | a slow, near-DC voltage through a coil | moves $f_{01}$ |

- The drive line has no ADC, so nothing sent down it comes back.
- Every operation today writes a voltage onto one of these three lines.

---

## The rotating frame

- The Bloch vector precesses about $z$ at the qubit frequency.
- Move to a frame spinning about $z$ at the drive frequency.
- On resonance the precession stops and the state holds still.
- The instrument keeps that frame as a running phase on each output.

---

## Area and phase

$$\theta = \int_0^{\tau}\Omega(t)\,\mathrm{d}t$$

- The Rabi rate $\Omega(t)$ is proportional to the envelope, so only the area matters.
- Half the amplitude is half the area, so `X/2` is the same shape halved.
- The carrier phase $\phi$ is the azimuth, so `Y` is `X` advanced 90 degrees.

---

## Axis and angle

![h:450](img/rotation.svg)

<p class="cap">The carrier phase picks the axis in the equatorial plane, the envelope area picks the angle.</p>

---

## Leakage

- A transmon is a ladder, not a two-level system.
- The $|1\rangle \to |2\rangle$ transition sits $|\alpha|$ below the one you drive.
- Population reaches it at order $(\Omega/\alpha)^2$, so a faster gate leaks more.
- Most comes back, and what stays is leakage no later gate recovers.
- A square edge is broadband and feeds the transition you are avoiding.

---

## DRAG

$$Q(t) = \beta\,\dot{I}(t)$$

- DRAG adds a second envelope on the quadrature 90 degrees from the one you play.
- Its shape is the derivative of the in-phase envelope.
- It cancels the leading transfer into $|2\rangle$ and the phase error left behind.
- First order gives $\beta \approx 1/|\alpha|$, and $\beta$ is calibrated per qubit.

---

## Virtual Z gates

- A $Z$ rotation turns the frame the instrument already keeps.
- Apply $Z(\theta)$ by advancing the phase of every later pulse on that line.
- No waveform and no samples, so no duration and no error.
- A single-qubit unitary becomes two `X/2` pulses with phase advances around them.

---

## Two-qubit gates

Two qubits interact through a coupling, and a gate is an interval where you let it act.

| route | what you do | duration |
|---|---|---|
| **flux** | push one qubit until $\lvert 11\rangle$ and $\lvert 02\rangle$ meet, hold, come back | 40 to 100 ns |
| **all-microwave** | drive A at B's frequency and let the coupling condition B on A | 200 to 500 ns |

- The flux route drags a qubit off its sweet spot, the bias where flux noise stops moving its frequency.
- The microwave route moves neither qubit.
- Two-qubit error runs five to ten times single-qubit error.
- Each pair is calibrated by a two-dimensional scan, amplitude against duration.

---

## Dispersive readout

- Every gate so far went out on a drive line that has no ADC.
- The qubit is read through a **resonator** beside it, coupled at rate $g$.
- The detuning $\Delta = f_{01} - f_r$ is far larger than $g$.
- At that ratio the two cannot exchange energy, so they shift each other.

---

## The dispersive shift

- The resonator sits at $f_r + \chi$ or $f_r - \chi$, and the qubit picks which.
- Park a tone between the two, and the transmission past the resonator carries the answer.
- The shift grows with the coupling and shrinks with the detuning.

$$\chi = \frac{g^2}{\Delta}\cdot\frac{\alpha}{\Delta+\alpha} = -1.8\ \text{MHz}, \qquad 2\chi = 3.6\ \text{MHz}$$

---

## The readout chain

![h:340](img/dispersive.svg)

1. The resonator fills, and the return picks up a state-dependent phase.
2. A parametric amplifier at 10 mK, a HEMT at 4 K, then warm amplifiers.
3. Down-conversion to an intermediate frequency, an ADC, then demodulation.
4. Multiply by the weights, sum over the window, one complex number per shot.

---

## Integration weights

- The weights $w(t)$ are their own calibration, measured like any other number.
- Optimal is the difference between the mean $|0\rangle$ and $|1\rangle$ responses.
- That difference is taken sample by sample across the record.
- The window then weights the part where the two states separate.

---

## Readout fidelity

- The resonator has to fill before the return says anything, at rate $\kappa$.
- Integrating longer beats down the amplifier noise, and $T_1$ caps the window.
- Cloud separation $d$ grows with photon number and with $2\chi/\kappa$.
- Information per photon peaks near $2\chi = \kappa$, and this chip sits at 2.4.
- The error is an erfc of $d$ against the cloud width $\sigma$.

$$\varepsilon = \tfrac{1}{2}\,\mathrm{erfc}\!\left(\frac{d}{2\sqrt{2}\,\sigma}\right) \qquad 4\sigma \to 2\% \qquad 6\sigma \to 0.1\%$$

---

## How hard to read out

$$n_{\text{crit}} = \frac{\Delta^2}{4g^2} \approx 37 \ \text{photons on this chip}$$

- More photons separate the two clouds, so the temptation is to turn the tone up.
- The dispersive approximation has a limit, and the limit is a photon number.
- Below it the resonator reports the qubit, above it it sits on bare $f_r$ and reports nothing.

---

## Coherence times

| | this chip | what it measures |
|---|---|---|
| $T_1$ | 18 us | energy leaving the qubit and not coming back |
| $T_2^{*}$ | 9 us | plus every source of frequency wander, unfiltered |
| $T_2$ echo | 16 us | plus a $\pi$ pulse in the middle, refocusing slow noise |

$$\frac{1}{T_2} = \frac{1}{2T_1} + \frac{1}{T_\varphi}$$

- Relaxation feeds half its rate into dephasing, so $T_2 \le 2T_1$ always.
- Pure dephasing $T_\varphi$ is the rest, and the gap between the last two rows is its slow part.

---

## Three coherence experiments

| experiment | the sequence | what it isolates |
|---|---|---|
| inversion recovery | $\pi$, wait, read | $T_1$, energy leaving and not coming back |
| Ramsey | $\pi/2$, wait, $\pi/2$, read | $T_2^{*}$, and the drive frequency error as a fringe |
| Hahn echo | $\pi/2$, wait, $\pi$, wait, $\pi/2$, read | $T_2$, with slow noise refocused |

- Only the middle of the sequence changes, and that is why a **fragment** earns its place.
- Ramsey runs deliberately off resonance, so the fringe rate reads out the frequency error.
- Sweep out to about three time constants, since later points measure only noise.

---

## Noise sources

- **Two-level defects** in the junction oxide and every metal interface.
- **Quasiparticles**, broken Cooper pairs raised by stray infrared and cosmic rays.
- **$1/f$ flux noise**, the reason a tunable qubit has a sweet spot.
- **Purcell decay** down the readout line, at rate $\kappa(g/\Delta)^2$.
- All four drift, so one coherence number is a snapshot.

---

## The device

| | | |
|---|---|---|
| $f_{01}$ = 4.85 GHz | $f_r$ = 7.20 GHz | $\Delta$ = $-2.35$ GHz |
| $\kappa$ = 1.5 MHz ($Q_L$ = 4800) | $\chi$ = $-1.8$ MHz | $2\chi/\kappa$ = 2.4 |
| $T_1$ = 18 us | $T_2^{*}$ = 9 us | $T_2$ = 16 us |

Every fit you run has to land on these, and a circuit carries none of them.

---

## Six measured numbers

A circuit says `X(q0)`. Before an instrument can emit it, somebody has to supply this.

```text
40 ns DRAG envelope,  IQ pair,  carrier 4.8500 GHz,  amplitude 0.6200,  sigma 10 ns,  beta 0.15
```

- Nothing in `X(q0)` names a line, a carrier, or an envelope.
- The carrier and the amplitude came out of their own scans, and the rest are choices.
- They drift, so the scans are run again.

---

## Calibration order

<p class="big">resonator → qubit → π pulse → coherence → readout → reset</p>

- Each scan consumes the answer from the one before it.
- You cannot find the qubit before you can read it out.
- You cannot fit a $\pi$ amplitude before you know where the qubit is.

---

<!-- _class: divider -->

<p class="kicker">Concepts · slides only</p>

# Why a language of its own

### Six requirements, and what a vendor dialect does to them

---

## Six requirements

- **Timed waveforms on named lines**, not gates on qubits.
- **A clock per line**, with barriers as explicit instructions.
- **Parameter sweeps**, nested or stepped in lockstep.
- **Shot averaging**, collapsing repeats into one number.
- **Acquisition with weights**, and a choice of what to keep.
- **A branch on a measurement**, inside the shot.

---

## One dialect per rack

- A paper travels between labs, and the control code behind it never has.
- Every vendor ships its own sequencer dialect.
- They are assembly shaped, because an FPGA has to meet every clock edge.
- Loops come out of registers, and waveform memory is addressed by hand.
- Porting to a second rack means rewriting experiments that were already correct.

---

## The loop decision

- Each script hard codes which loops run in the sequencer.
- Whatever is left runs on the host, one round trip per step.
- Running on the host can cost a factor of a hundred.
- The choice belongs to the rack, so it should not sit in the file.

---

## A Python DSL

- The experiment goes in the file, the rack stays outside it.
- QProgram is a Python builder that produces an AST.
- `program.play(...)` appends a typed `Play` node and sends nothing.
- Every other tool in the library reads that one tree.
- Not a compiler or a scheduler, since those sit behind `PlatformProtocol`.

---

## The architecture

![h:480](img/stack.svg)

<p class="cap">Your script builds a tree, a platform runs that tree, and files fall out as artifacts.</p>

---

<!-- _class: divider -->

<p class="kicker">Part 1 · notebooks/01_introduction.ipynb</p>

# The program is data

### The operations, the lines they run on, the shapes they play, and the file they save to

---

## Creating a program

```python
import qprogram as qp

first = qp.QProgram(label="first_program", description="One drive pulse on qubit 0.")
first.set_frequency("q0/drive", 4.85e9)
first.play("q0/drive", IQDrag(amplitude=0.62, duration=40, sigma=10, beta=0.15))

print(qp.dumps(first))
print(sorted(first.buses))        # ['q0/drive']
```

- A program is a label, an optional description, an optional schema, and the calls you append.
- Every call appends one typed node to a tree and sends nothing anywhere.
- Bus names here are plain strings, which is legal and checks nothing.

---

## Operations

The verbs are instrument actions rather than gates, and each call appends one node.

| what it does | QProgram |
|---|---|
| output one pulse envelope | `play` |
| output a pulse and integrate the return | `measure`, returns a handle |
| idle one bus | `wait` |
| bring buses to a common time | `sync` |
| set the modulation frequency of a line | `set_frequency` |
| set or zero the phase reference | `set_phase`, `reset_phase` |
| scale the whole output path | `set_gain` |
| write a DC level onto a line | `set_offset` |
| write or read a platform setting | `set_parameter`, `get_parameter` |
| invoke a named sub-program | `call` |

---

## Prepare and read

```text
body:
  block:
    set_frequency "q0/drive" 4850000000.0
    set_gain "q0/drive" 1.0
    reset_phase "q0/drive"
    play "q0/drive" IQDrag(amplitude=0.62, duration=40, sigma=10, beta=0.15)
    wait "q0/drive" 4
  set_frequency "q0/readout" 7200000000.0
  sync "q0/drive" "q0/readout"
  measure "q0/readout" IQZero(...) IQPair(...) name="m0" fields=["state", "iq"]
```

- Prepare on the drive bus, hold at a barrier, then read on the readout bus.
- Durations are nanoseconds, frequencies hertz, phases radians, gain and offset dimensionless.
- The two shapes on the `measure` are the readout tone and the integration weights.
- Every bus here is a quoted string, legal and unchecked, and the next slides fix that.

---

## One clock per bus

![h:430](img/timing.svg)

<p class="cap">Each bus advances only when you write to it, so the readout can start during the drive.</p>

---

## The sync barrier

```python
program.sync(["q0/drive", "q0/readout"])   # hold both buses
program.sync()                             # every bus in the program
program.sync([])                           # raises, rather than guess
```

- A barrier holds every named bus until the furthest-ahead one has finished.
- Without it you measure the pulse rather than the state.
- The compiler turns that declaration into real timing on the sequencer.

---

## Measurement handles

```python
m0 = program.measure("q0/readout", readout_pulse, weights)

print(m0.name)                              # m0
print(m0 == qp.MeasurementHandle("m0"))     # True
```

- `measure` returns a handle, and the handle is only a name.
- A schema-backed bus prefixes it, so the same call there gives `q0/readout/m0`.
- Pass `name=` to choose one yourself, and a name already taken is refused.
- `result.get(m0)` reads the data back after the run, and a handle rebuilt from a file still names it.

---

## Measurement fields

| field | shape | what it is |
|---|---|---|
| `MF.RAW` | `(*sweeps, time, IQ)` | the ADC trace, averaged over shots |
| `MF.IQ` | `(*sweeps, IQ)` | integrated I and Q, the default |
| `MF.STATE` | `(*sweeps)` | classified per shot, averaged into a population |

- One `measure` call can ask for all three.
- Multiply `raw` by the weights and sum to get `iq`.
- Threshold `iq` and you get `state`.
- `get` raises rather than substituting a field you never requested.

---

## Buses

- A bus is one signal path, from an instrument port to the chip.
- One qubit owns several lines that have nothing in common.
- One feedline carries every readout at once, each on its own frequency.
- So an operation names the line, never the qubit.

---

## One signal path

![h:470](img/buses.svg)

<p class="cap">Instrument ports on the left, bus names in the middle, and the chip lines on the right.</p>

---

## Build-time checks

```python
schema = BusSchema.flux_tunable_transmon()
q = schema.q                      # every bus below is now a checked reference

program.play(q[0].drive, Square(amplitude=0.5, duration=40))
-> Bus 'q0/drive' is an IQ channel but received a single-channel Waveform (Square).

program.measure(q[0].drive, "readout", "weights")
-> Bus 'q0/drive' does not support acquisition (acquires=False).
```

- A schema hands back a `BusRef`, still a string, carrying `channel` and `acquires`.
- The schema types each operation against the bus it names.
- `qp.ValidationError` raises at the call that made the mistake, not at run time.
- Raw string bus names skip both checks, on purpose.

---

## Waveforms

- A waveform describes one envelope and knows nothing about hardware.
- `envelope()` gives samples, `get_duration()` gives nanoseconds, `plot()` draws it.
- `Square` for readout, `Gaussian` for drive, `FlatTop` for a swept length.
- `Arbitrary` for samples you bring, `Ramp` and `SuddenNetZero` for flux.
- Drive and readout lines are IQ, so they take an `IQPair` or an `IQDrag`.

---

## Waveforms are data

```
equal by structure: True      # Gaussian(0.5, 40, 8) == Gaussian(0.5, 40, 8)
a + b concatenates: 20 ns     # into a Chained
peak I:   0.6192
peak |Q|: 0.0056              # the DRAG correction, from the concept slides
```

- Waveforms compare and hash by structure rather than by identity.
- So a program can report how many distinct envelopes it really plays.
- Two shapes add, and `a + b` is a `Chained` that plays one after the other.
- An IQ shape hands back its two halves as ordinary single-channel waveforms.

---

## Waveform aliases

```text
  play q[0].drive "pi"
after binding: play q[0].drive IQDrag(amplitude=0.62, duration=40, sigma=10, beta=0.15)
```

- `play(q[0].drive, "pi")` names a pulse instead of writing one down.
- `with_waveforms(dict)` returns a new program with the numbers bound in.
- An amplitude in the script goes stale, so keep amplitudes in a `qp.WaveformLibrary` of their own, resolved per bus.
- `rebind` re-resolves every bus through a schema, so another rack's naming needs no find and replace.

---

## Plotting

```python
ax = waveform.plot()                          # one Axes back, per envelope
ax_i, ax_q = pi_pulse.plot()                  # an IQ shape draws two panels
waveform.plot(target=panel)                   # or draw onto a layout you opened

ax = result.plot(m0, channels="magnitude", title="Resonator spectroscopy")
ax.axvline(f_r, color="grey", ls=":")         # the fit and the truth go on top
```

- Every figure in the notebooks comes from the library, and none is hand-rolled matplotlib.
- The call draws the data and hands back the `Axes`, so a reference line is one more call.
- `result.plot` reads the array's shape: one swept dimension is a line, two are a heatmap.

---

## Blocks

```python
with program.block():                                  # grouping, changes nothing
    ...
with program.average(shots=200):                       # the shot loop, Part 2
    with program.sweep(freq, qp.Range(...)):           # one dimension per sweep, Part 2
        ...
with program.sweep(a, ...) | program.sweep(b, ...):    # lockstep, Part 2
    ...
with program.if_(m0.state == 1):                       # a branch on a classified bit, Part 3
    ...
```

- Five containers nest, and nesting in the file is nesting in the result.
- `sweep` adds a dimension, `average` adds none, and a lockstep pair adds one between them.
- `if_` reads a measurement outcome inside the shot, before the shot has finished.

---

## The text form

```python
qp.save(program, "out/prepare_and_read.qp")
reloaded = qp.load("out/prepare_and_read.qp")

assert reloaded.body == program.body
assert qp.loads(qp.dumps(program)).body == program.body
```

- `.qp` is one statement per line, with indentation for nesting.
- Quoting is the type distinction, so a bare `q[0].readout` is a bus.
- Nothing is truncated and nothing is implied.
- It depends on no numpy version, no sidecar, and no database.

---

## The file as a diff

```diff
-    play "q0/drive" IQDrag(amplitude=0.62, duration=40, sigma=10, beta=0.15)
+    play "q0/drive" IQDrag(amplitude=0.31, duration=40, sigma=10, beta=0.15)
```

- The `.qp` text is line oriented, so a retune shows up as one changed line.
- Compare `body.elements` pairwise to find which child moved.
- The change localises to `body[0][3]`, the `play` inside the block.

---

## The simulator

- `qp.simulate(program, model=...)` walks the tree in pure Python.
- It models the shape: nesting, averaging, one record per `measure`.
- It models no timing and no waveform physics, so `wait` changes no number.
- The program and the analysis are byte-identical here and on hardware.

---

## Exercise 1.1

> 🧩 Bias the flux line, prepare the qubit, read it out, and round-trip the program through a file.

- `set_offset` on the flux bus, `set_frequency` on the other two, then `sync` and `measure`.
- Save it, load it back, and compare the two bodies.
- Then measure the flux bus, and let the schema say why not.

---

<!-- _class: divider -->

<p class="kicker">Part 2 · notebooks/02_basics.ipynb</p>

# Variables, sweeps, and results

### One swept variable, two of them nested, and two of them in lockstep

---

## Anatomy of a program

![h:430](img/anatomy.svg)

<p class="cap"><code>sweep</code> creates an axis, <code>average</code> creates none, <code>measure</code> creates a record, and <code>play</code> carries the variable down.</p>

---

## Variables

```python
freq = program.variable("ro_freq", label="Readout frequency", units="Hz")
with program.average(shots=200):
    with program.sweep(freq, qp.Range(7.19e9, 7.21e9, 0.2e6)):
        program.set_frequency(q[0].readout, freq)
        m0 = program.measure(q[0].readout, "readout", "weights")
```

- A variable is a hole in the program, and the sweep fills it.
- You need the hole because the fab does not deliver an exact frequency.
- Arithmetic on a variable builds an expression tree, computing nothing.

---

## Sweep sources

| source | kind | reach for it when |
|---|---|---|
| `qp.Range(start, stop, step)` | linear | you know the spacing |
| `qp.Linspace(start, stop, num)` | linear | you know the point count |
| `qp.Values(seq)` | arbitrary | you have a measured or calibrated list |
| `qp.Logspace(start, stop, num)` | arbitrary | the axis spans decades |
| `qp.File(path)` | arbitrary | the points live in a `.npy` beside the program |
| `qp.Repeat`, `qp.Rotate`, `qp.Concat` | arbitrary | the order or the multiplicity is the choice |

- Eight ship, and the last three take a source and hand back one, so they compose.
- A linear source runs out of a sequencer register, with nothing uploaded.
- An arbitrary source is a table, and `Values` stays arbitrary even when evenly spaced.

---

## The measurement model

```python
def s21(bus, env):
    """Transmission past one resonator: a notch, 90 percent deep on resonance."""
    delta = (env["ro_freq"] - F_READOUT) / (KAPPA / 2)
    return 1.0 - 0.9 / (1.0 + 1j * delta)

qp.simulate(program, model=qp.MockMeasurementModel(response=s21, noise=0.02, seed=7))
```

- The interpreter asks a model for one sample per shot, and nothing else in a run makes a number.
- `env` holds every variable a loop currently binds, keyed by the id you declared.
- Any object with a `sample(bus, env)` method does the job, so a model may carry state.

---

## Averaging

- `average(shots)` repeats the body and hands back the mean.
- It is the one block that adds no dimension, where every `sweep` around it does.
- Amplifier noise and projection noise both fall as $1/\sqrt{N}$.
- Halving the noise therefore costs four times the measurement time.

---

## Resonator spectroscopy

```
dims ('ro_freq', 'IQ')   shape (101, 2)
dip at   7.200000 GHz
true     7.200000 GHz
the sweep steps 200 kHz, which bounds what an argmin can say
```

- The resonator hangs off the feedline, so the trace dips on resonance.
- A 20 MHz window in 200 kHz steps puts seven samples across a 1.5 MHz resonance.
- `channels=` picks the quadrature pair, the magnitude, or the phase.
- An argmin can never beat the step size you chose.

---

## Two tones

- The qubit answers only through the resonator, so finding it takes two tones.
- Park the readout in the dip, then sweep a second tone past $f_{01}$.
- Where it hits the transition, the qubit spends part of its time excited.
- Repeat that scan at a series of drive amplitudes and one line becomes a map.

```text
  average 200:
    for drive_amp in Linspace(start=0.05, stop=0.3, num=21):
      for drive_freq in Linspace(start=4830000000.0, stop=4870000000.0, num=41):
        set_frequency q[0].drive drive_freq
        play q[0].drive IQZero(envelope=Square(amplitude=drive_amp, duration=20000))
        sync q[0].drive q[0].readout
        measure q[0].readout "readout" "weights" name="q0/readout/m0" fields=["state"]
```

---

## The saturation ceiling

$$P_1(f, a) = \frac{1}{2}\,\frac{\Omega^2}{\Omega^2 + (f - f_{01})^2}, \qquad \Omega \propto a$$

- A strong continuous drive balances excitation against decay, so the population saturates at one half.
- A two-tone peak above that ceiling means the classifier is wrong.
- The same formula broadens the line, and the full width is twice the rotation rate.
- So the map shows the peak rising and the ridge widening at once.

---

## Labeled results

```
one sweep, integrated:  dims ('ro_freq', 'IQ')                shape (101, 2)
two sweeps, classified: dims ('drive_amp', 'drive_freq')      shape (21, 41)
coordinate: {'long_name': 'Readout frequency', 'units': 'Hz'}
```

- `result.get(m0)` hands back a labeled `xarray`, one record per `measure`.
- One dimension per enclosing sweep, outermost first, named after your variable ids.
- The label and units you declared arrive on the coordinate, and every axis label comes from there.
- `result.plot(m0)` picks a line or a heatmap from the shape and hands back the `Axes`.

---

## Lockstep sweeps

```
dims:   ('drive_amp|drive_freq',)   shape (21,)
coords: ['drive_amp', 'drive_freq']
measurements: 21 against 861 for the full map
```

- Nested `with` statements are nested loops, so a two-deep nest is a rectangle.
- `sweep(a) | sweep(b)` advances both on the same tick instead.
- One dimension comes back with two coordinate arrays, a diagonal cut through the map.
- Walking the ridge costs 21 measurements against 861, and unequal lengths raise when the block opens.

---

## Rabi

$$P(a) = \sin^2\!\left(\frac{\pi a}{2 a_\pi}\right)$$

- Park the drive on resonance, fix the shape and the duration, then sweep the amplitude.
- The angle follows the envelope area, so the population traces $\sin^2$ to a ceiling of one.
- The top of that curve is the worst place to read $a_\pi$, and the half-way crossing is the steepest.

---

## Exercise 2.1

> 🧩 Park the drive on resonance, step its amplitude, and calibrate a full rotation from the curve.

- The swept variable goes inside the `IQDrag`, not into an operation.
- Read the half rotation off the rising branch, then double it.

---

<!-- _class: divider -->

<p class="kicker">Session 2 · Part 3 · notebooks/03_advanced.ipynb</p>

# Fragments, feedback, and the machine

### Six sections, each one standing on its own

---

## Fragments

- The three coherence experiments are prepare, wait, read out, and only the middle changes.
- So write the pulse once. A `@fragment` is a named, parameterized sub-program.
- Its first argument is the fragment being built, and the rest are untyped parameters.
- `expand()` inlines every call, so keep `measure` in the program where the handle stays yours.

```text
fragment x_pulse(drive, amp):
  play drive IQDrag(amplitude=amp, duration=40, sigma=10, beta=0.1)

body:
  x_pulse("q0/drive", 0.5)
  x_pulse("q0/drive", 0.25)
```

---

## Conditionals

- A measurement handle is the one value a branch can read.
- `if_`, `elif_` and `else_` are context managers that chain.
- The condition must be a measurement-state predicate, nothing wider.
- An FPGA evaluates it between one pulse and the next, in tens of nanoseconds.

```text
  average 4000:
    measure "q0/readout" "probe" "weights" name="before" fields=["state"]
    if before.state == 1:
      play "q0/drive" "pi"
    else:
      wait "q0/drive" 40
    measure "q0/readout" "probe" "weights" name="after" fields=["state"]
```

---

## Active reset

```
excited before: 0.305   expected 0.300
excited after:  0.029   expected 0.030
```

- Passive reset idles for several $T_1$ before every shot, and active reset measures first.
- The $\pi$ pulse then fires only on the shots that came back excited.
- The arm that did not run holds `NaN` rather than a zero, so two arms combine.

---

## Three extension seams

| you want | you write | you get for free |
|---|---|---|
| a pulse shape the DSL lacks | a `Waveform` subclass | serialization, structural equality, validation, plotting |
| a sweep axis the DSL lacks | a `SweepSource` subclass | serialization, a capability token, length checks, coordinates |
| an operation the DSL will never have | an `Operation` plus a `VendorNamespace` | `program.<vendor>.<op>()`, a `require` line, a capability token |

- A language that cannot be extended gets forked, and a fork is not portable.
- A capability token is a dotted name a rack can refuse the node by.
- Serialization is read off your constructor, so the arguments have to be the state.

---

## A custom waveform

```python
def resolved(v):
    return v.evaluate_or_raise() if isinstance(v, qp.Expression) else v

class HalfSine(qp.waveforms.Waveform):
    def __init__(self, amplitude: float | qp.Expression, duration: int) -> None:
        self.amplitude, self.duration = amplitude, duration
    def envelope(self, resolution: int = 1) -> np.ndarray:
        n = self.duration // resolution
        return resolved(self.amplitude) * np.sin(np.pi * np.arange(n) / n)
    def get_duration(self) -> int: return self.duration
```

- You owe two methods, `envelope(resolution)` and `get_duration()`.
- `plot`, `area`, `peak_amplitude` and structural equality arrive from the base class.
- Without `resolved` a swept amplitude reaches numpy and fails there.
- `register_waveform` teaches the file format, and a token gives a rack a name to refuse it by.

---

## A custom sweep source

```python
@qp.register_sweep_source
class Chebyshev(qp.SweepSource):
    """Chebyshev nodes between two endpoints, so the points crowd towards the edges."""
    KIND = "arbitrary"
    TOKEN = "sweep.chebyshev"
    def __init__(self, start: float, stop: float, num: int) -> None:
        self.start, self.stop, self.num = start, stop, num
    def length(self) -> int: return self.num
    def values(self) -> np.ndarray:
        unit = -np.cos(np.pi * (2 * np.arange(self.num) + 1) / (2 * self.num))
        return self.start + (unit + 1) / 2 * (self.stop - self.start)
```

- `length()` is static, so a lockstep pair checks it before anything runs.
- `KIND` declares linear or arbitrary, and a sequencer generates only the linear kind.
- `values()` feeds the interpreter, the xarray coordinate, and `optimize`.
- Registration puts `TOKEN` in the registry too, where a waveform needs a second call.

---

## A vendor operation

```python
class TwpaNamespace(qp.VendorNamespace):
    def set_pump(self, bus: str, frequency: float) -> None:
        self._append(SetPump(bus=bus, frequency=frequency))

qp.QProgram.register_vendor("twpa", TwpaNamespace)
qp.register_vendor_operation("twpa", "set_pump", SetPump)
qp.register_capability_tokens("vendor.twpa.set_pump")
qp.register_vendor_version("twpa", "0.1.0")
```

- `SetPump` is an `Operation` subclass, and it owes only `required_capabilities()`.
- `register_vendor` makes `program.twpa` resolve on any `QProgram`.
- `register_vendor_operation` teaches the writer and the parser.
- `register_vendor_version` fixes the version the `require` line carries.

---

## One portable file

```text
#!QProgram 1.0

require twpa 0.1

body:
  var flux_amp label="Flux amplitude" units="DAC units"

  twpa.set_pump "q0/readout" 7900000000.0
  average 200:
    for flux_amp in Chebyshev(start=0.0, stop=0.5, num=21):
      play "q0/flux" HalfSine(amplitude=flux_amp, duration=40)
      sync "q0/flux" "q0/readout"
      measure "q0/readout" "readout" "weights" name="m0" fields=["state"]
```

- The three seams of the last three slides, in one file, with no patch to the core.
- The `require` line names the vendor and the version the file was written against.
- A rack without `vendor.twpa.set_pump` marks that node `[--]`, as a diagnostic and not a syntax error.

---

## Entry points

```toml
[project.entry-points."qprogram.vendors"]
qblox = "qprogram_qblox"
```

- The entry-point name is the vendor namespace, the value is the module.
- A `require` line makes the loader import that module and register it.
- Only the `qprogram.vendors` group is scanned.
- A vendor nobody claims fails by name, naming the package to install.

---

## A published profile

```text
qprogram-base-v1   33 tokens, limits {}
qblox-default-v1   31 tokens, limits {'min_wait_duration_ns': 4}
qdac-default-v1    16 tokens, limits {'min_dwell_ns': 100}

op.set_offset            qblox True  qdac False
vendor.qdac.set_offset   qblox False qdac True
waveform.iq              qblox True  qdac False
```

- A profile is a named, versioned bundle of tokens, limits and predicates that a package ships.
- A Qblox sequencer output has an offset register, so it claims the core `op.set_offset`.
- A QDAC channel is a slow chassis write, so it refuses that name and offers its own.

---

## Implementing a platform

| member | what it answers |
|---|---|
| `get_bus_schema()` | which chip this rack is wired to |
| `get_buses()` | the bus names it exposes |
| `get_parameters(bus)`, `get_global_parameters()` | the knobs, per bus and platform wide |
| `capabilities` | what it can and cannot run |
| `execute(program)` | run it and return a `QProgramResult` |

- Six abstract members, and `validate`, `plan` and `explain` arrive written off the descriptor.
- By convention `execute` validates first and raises on an error diagnostic.
- Between `execute` and the arrays the protocol says nothing. Lower, allocate, upload, arm, acquire.
- That work is where a vendor's expertise lives.

---

## Two racks

| | rack A, yours | rack B, next door |
|---|---|---|
| drive line | fast AWG with a sequencer | fast AWG with a sequencer |
| readout line | same box, shared clock | same box, shared clock |
| flux line | the same AWG, a DC-coupled output | a 20-bit DC source over Ethernet |
| bus names | `q0/drive` | `drive_q0` |
| pulse shapes | your calibration | their calibration |

- The flux row is the one that changes how the program runs.
- Your program never said which loop was hardware and which was software.
- The split is a property of the rack, not of the experiment.

---

## The flux line

- Flux noise dephases the qubit, and the frequency tracks the bias directly.
- Heavy filtering keeps the line quiet, and gives it millisecond time constants.
- Rack B puts a 20-bit DC source there, over Ethernet, with no FPGA.
- A loop that steps that voltage runs from the control PC.

---

## Two loops

- One loop steps a DC level onto a slow, filtered flux line, milliseconds per step.
- Everything inside it retunes a source, fires a pulse and reads out, microseconds per step.
- The program never recorded which is which, and the rest of this part settles it.

```text
  average 200:
    for bias in Linspace(start=-0.05, stop=0.15, num=41):
      set_offset q[0].flux bias
      set_frequency q[0].drive 4850000000.0
      play q[0].drive "pi"
      sync q[0].drive q[0].readout
      measure q[0].readout "probe" "weights" name="m0" fields=["state"]
```

---

## Tokens

```text
Average        ['block.average']
Sweep          ['block.sweep', 'sweep.linear', 'sweep.linspace']
SetOffset      ['expr.variable', 'op.set_offset']
SetFrequency   ['op.set_frequency']
Play           ['op.play', 'waveform.alias']
Sync           ['op.sync']
Measure        ['measure.fields.state', 'op.measure', 'waveform.alias', 'waveform.iq']
```

- Every node answers `required_capabilities()` with a set of dotted strings.
- A **token** is set membership, so checking one is a hash lookup.
- The prefix decides where it is checked, on the bus or on the platform.
- The set depends on the node's data, not just on its class.

---

## Three mechanisms

| mechanism | the question it answers | examples |
|---|---|---|
| **token** | is this in the set? | `op.play`, `waveform.iq_drag`, `sweep.logspace` |
| **limit** | is this number small enough? | `max_loop_nesting`, `max_measurements` |
| **predicate** | given the rest of the program, is this legal? | no arbitrary sweep at `Wait.duration` |

- A rack states what it can do in these three forms.
- A token set is small enough for a vendor to publish as a profile.
- The validator checks all three against the tree, with no instrument attached.

---

## Platform capabilities

```python
caps = qp.PlatformCapabilities(
    bus={("q", "drive"): fast, ("q", "readout"): fast, ("q", "flux"): slow},
    platform=base,
    default_bus_profile=fast,
)
```

- `bus` gives one profile per element kind and bus kind slot.
- `platform` holds the bus-less half, where blocks and sweep shapes live.
- `default_bus_profile` covers a raw-string bus and any slot not listed.

---

## rt and host

- Every slot splits into an `rt` half and a `host` half, the two **domains** a node can run in.
- `rt` is the sequencer, `host` is the lab server.
- Either half may be `None`, and a `None` is a statement about the wiring.
- Rack B's flux slot has `rt=None`, so no loop there runs in hardware.

---

## Validation

```text
[warning] forced-host: Block 'Average' falls back to host-side execution:
          contains host-side-only sub-block 'Sweep'.        (at body[0])
```

- `qp.validate(program, caps)` returns a diagnostics list and an execution plan.
- It never raises, so a broken program stays data you can print.
- `execute` turns an error into an exception, so nothing broken reaches a rack.
- Severity is what you act on, and every diagnostic carries a path back to a line.

---

## The execution plan

| label | what it means |
|---|---|
| `[rt]` | real time, inside the sequencer |
| `[host]` | dispatched from the control PC, one round trip per iteration |
| `[rt\|host]` | either one, and the platform picks |
| `[--]` | nothing can run it, and an error above says why |

- The plan is the second half of what `qp.validate` returns.
- Operations come first, then the loops that contain them.
- `qp.explain` draws the same plan as a tree, marking each diagnostic inline, `!!` error, `~` warning, `i` info.

---

## Two domains

![h:430](img/plan.svg)

<p class="cap">Drive and readout sit on the sequencer, flux on the DAC, so the bias loop runs host side.</p>

---

## The cost of a loop

A host loop pays one network round trip per iteration.

| where the loop runs | one execution | the whole scan |
|---|---|---|
| sequencer, passive reset | 2 us readout plus $5T_1$ | **2 s** |
| sequencer, active reset | a few us | **0.2 s** |
| host, one round trip per execution | about 1 ms | **20 s** |

---

## The rewrite

```text
before                            after
average 200:                      for bias in Linspace(...):
  for bias in Linspace(...):        set_offset q[0].flux bias
    set_offset q[0].flux bias       average 200:
    play q[0].drive ...               play q[0].drive ...
    measure q[0].readout ...          measure q[0].readout ...
```

- A block runs where its worst child runs, so the average fell to the host.
- `qp.optimize(program, caps)` hoists the bias write out of the average.
- The host does one DAC write per point, the sequencer runs the rest.
- It is opt-in, because grouping the shots of a point is not interleaving them.

---

## The broadcast

```python
program.sync([drive, readout])   # both buses have a sequencer
program.sync()                   # every bus, including the flux line
```

- A bare `sync()` aligns every bus the program touches.
- The flux bus has no sequencer, so that sync lands host side.
- `optimize` then refuses to hoist across it.
- Naming the two buses keeps the sync real-time, and the rewrite survives.

---

## Limits and predicates

- A limit is a hard wall, because sequencer loops run out of registers.
- The validator reads four numeric limits, from loop nesting to the shortest legal wait.
- A predicate is code, and a lab writes one about its own wiring.
- It yields a `Diagnostic` to refuse, or a `DomainConstraint` to move a loop host-side instead.

---

## The checker

```
$ python -m qprogram.lsp check flux_sweep.qp   (exit 1)
[{"line": 18, "end_line": 18, "severity": "error", "code": "parse-error",
  "message": "Line 19: bus path 'q[0].drve' does not resolve against the
  program schema: 'q' has no bus 'drve'. Available: drive, readout, flux"}]
```

- Point it at any `.qp`. This one is the flux sweep of a few slides back, saved with `qp.save`.
- `check` parses with the production parser and validates against the reference platform.
- Diagnostics come out as JSON and an error exits non-zero, so it fits a pre-commit hook.

---

## Exercise 3.1

> 🧩 Add a vendor measurement field, then prove it is legal on one rack and rejected on another.

- Register the token `measure.fields.counts`, then measure with `fields=("counts", MF.STATE)`.
- Validate against the reference platform, then against a rack without the token.
- Read the counts back and say why they are zero.

---

## Where to go next

- **Docs**: [qilimanjaro-tech.github.io/qprogram](https://qilimanjaro-tech.github.io/qprogram) · **Source**: [github.com/qilimanjaro-tech/qprogram](https://github.com/qilimanjaro-tech/qprogram)
- The Reference section is normative, and `qp.lark` is the machine-readable grammar.
- Read `qprogram-qblox` or `qprogram-qdac` before writing your own extension.
- Write a rule your lab cares about as a predicate.
- Issues and pull requests are welcome.

---

<!-- _class: lead -->
<!-- _footer: '' -->

# Thank you

<p class="sub">Questions, and the notebooks are yours to keep</p>

<p class="meta">vyron@qilimanjaro.tech · flavie.lebars@qilimanjaro.tech · QCE 2026</p>
