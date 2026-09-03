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

## Introduction

- **Vyron Vasileiadis**, Tech Lead at **Qilimanjaro Quantum Tech** · vyron@qilimanjaro.tech
- **Flavie Le Bars**, Quantum Software Engineer at **Qilimanjaro Quantum Tech** · flavie.lebars@qilimanjaro.tech
- **Qilimanjaro** builds quantum computers and the software stack that drives them.
- **QProgram** is the pulse-level layer of that stack, an open-source Python DSL for the pulses, sweeps, and measurements a calibration is made of.

Everything today runs on your laptop. QProgram ships a pure-Python reference platform, so there is no fridge to book, no vendor SDK to install, and no cloud account to create.

---

## Links & QR codes

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

**Two ways to run everything, pick one:**

- **Local**: `pip install "qprogram[viz]" scipy` (Python 3.11 to 3.14), then open the notebooks.
- **Colab**: the first cell of every notebook installs what is missing, pinned to `0.1.0`.

**Right now:** open and run `notebooks/00_setup.ipynb`. Its last cell draws a resonator dip near 7.2 GHz. If you see the dip, you are ready.

> No hardware, no vendor package, no cloud account. The reference platform is part of the wheel.

---

## How we will work

- **Coding first.** These slides are the map. The work is in the notebooks, and the notebooks carry more than we will get through today, on purpose. They are what you take home.
- Each part is a short concept, a live code-along, then one 🧩 exercise on the problem that part exists for.
- Two notebook flavours: `notebooks/` has blank `# TODO` cells, `notebooks/solutions/` has the answers and the outputs.
- Every snippet was run against `qprogram 0.1.0`. What a slide claims, a cell proves.
- Interrupt me. Lab stories are welcome, above all the ones that contradict the slide.

---

## Schedule

| Part | Notebook | Topic | Time |
|---|---|---|---|
| | | opening, the chip, and the language | 25 min |
| 1 | `01_pulse_programs` | The program is data | 20 min |
| 2 | `02_sweeps_and_results` | Sweeps, averaging, and results | 20 min |
| 3 | `03_finding_the_qubit` | Finding and driving the qubit | 25 min |
| 4 | `04_coherence_and_feedback` | Coherence, single shots, feedback | 30 min |
| 5 | `05_one_program_many_machines` | Capabilities, plans, porting | 30 min |
| 6 | `06_extending_and_shipping` | Extending, shipping, capstone | 20 min |
| | | questions and close | 10 min |

Two 90-minute sessions, and the gap between them lands after Part 3. Each part carries **one** 🧩 exercise, on the problem that part exists for. Part 6's capstone is the piece built to come out if we run long, and the notebooks hold more than the clock allows, on purpose.

---

## What you will build

- a **calibrated qubit**: resonator frequency, qubit frequency, and a $\pi$ pulse, all fitted from raw sweeps (Parts 2 and 3);
- a **coherence set**: $T_1$, $T_2^{*}$, and $T_2$ from echo, built out of reusable pulse fragments (Part 4);
- **single-shot readout** with a threshold, and **active reset** that reads the outcome and acts on it (Part 4);
- the **same calibration ported to a second rack**, checked against that rack before it runs (Part 5);
- your **own waveform, sweep source, and vendor operation**, then the whole bring-up as one script (Part 6).

By the end, a directory of `.qp` files and one `.wfl` library that another lab could load.

---

## What you are actually programming

An LC circuit on a silicon chip, cooled to 10 mK. Its energy levels are evenly spaced, so a tone that drives $|0\rangle \to |1\rangle$ drives $|1\rangle \to |2\rangle$ exactly as hard. A harmonic oscillator has no qubit in it.

- Swap the inductor for a **Josephson junction**, two aluminium films with a nanometre of oxide between them. Its current goes as $I_c\sin\varphi$, so its inductance depends on the current already in it.
- $\hat H = 4E_C\hat n^2 - E_J\cos\hat\varphi$. A parabola gives evenly spaced rungs. A cosine well gets shallower as you climb, so the rungs close up.
- $f_{01}$ and $f_{12}$ now differ by the **anharmonicity** $\alpha$, and a pulse whose spectrum is narrower than $|\alpha|$ addresses the bottom two levels alone.

<p class="cap">A transmon is a circuit, not an atom. Everything today follows from that one nonlinear element.</p>

---

## Where the numbers come from

- **One design ratio does most of the work.** $E_J/E_C$ large means the phase sits deep in the cosine well and stray charge stops moving the levels. Charge dispersion falls as $e^{-\sqrt{8E_J/E_C}}$ while the anharmonicity falls only as $-E_C$. Above roughly 50 the charge sensitivity is gone.
- $hf_{01} \approx \sqrt{8E_JE_C} - E_C$ and $\alpha \approx -E_C$, so one pair of energies fixes both. $E_C/h = 300$ MHz with $E_J/h = 11$ GHz gives **$f_{01} = 4.85$ GHz** and **$\alpha = -300$ MHz**, a ratio of 37. Labs run 30 to 100, trading charge dispersion against how fast a gate can be.
- **4 to 6 GHz is not a coincidence.** At 4.85 GHz, $hf/k_B = 233$ mK, so a 10 mK stage sits twenty-three times below the qubit's own energy scale. It is also the band where coax, circulators, and generators are things you can buy.
- Equilibrium there would leave $10^{-10}$ excited population. Real devices come in at an **effective 40 to 60 mK**, so half a percent to two percent, and Part 4 resets it rather than waiting.

---

## Two circuit elements, and the ladder that falls out

![h:450](img/transmon.svg)

<p class="cap">A capacitor across a Josephson junction, and the cosine well the junction gives it. The rungs crowd as you climb, which is the only reason the bottom two can be addressed on their own.</p>

---

## From a gate to a voltage and back

![h:470](img/rack.svg)

<p class="cap">Three lines down, one line back. Attenuators on the way in because the chip needs attowatts, not microwatts; amplifiers on the way out because a few tens of photons have to survive the trip to an ADC.</p>

---

## Why the input lines are mostly attenuator

<!-- The one slide that says why a fridge is not just a cold box. -->

- A 50 ohm resistor at 300 K radiates into every mode it touches. At 4.85 GHz that is $k_BT/hf \approx 1300$ photons per mode, and the qubit lives on one of them. Deliver those and the qubit is at room temperature whatever the plate under it says.
- So you attenuate on the way down and let each stage's attenuator set the noise floor at its own temperature. 60 dB on the drive line in the diagram, 50 dB on the readout input. A cold attenuator at 10 mK re-emits $10^{-10}$ photons in place of 1300.
- The signal pays the same attenuation and can afford to. **Microwatts at the generator, attowatts at the chip**, about 120 dB, almost all of it deliberate.
- Coming back up there is nothing to spare. A few tens of photons at 7.2 GHz is around $10^{-19}$ J. A travelling-wave parametric amplifier at 10 mK adds half a photon of vacuum noise because it may not add less; a HEMT at 4 K adds ten or twenty. **Amplify at the coldest point or the number is gone.**

---

## The fridge, stage by stage

![h:460](img/fridge.svg)

<p class="cap">Attenuators on the way down, each one re-thermalizing the noise it passes to its own stage. Amplifiers on the way up, the coldest one first, because the first amplifier sets the noise figure of everything after it.</p>

---

## Three lines, three jobs

| line | what runs on it | what it does |
|---|---|---|
| **drive** | a microwave tone near $f_{01}$ = 4.85 GHz | rotates the state |
| **readout** | a microwave tone near $f_r$ = 7.20 GHz | interrogates a resonator coupled to the qubit |
| **flux** | a slow, near-DC voltage through a coil | moves $f_{01}$ |

They share nothing but the chip. The drive line is a pair of DACs feeding an IQ mixer, gigahertz of bandwidth, and it has **no ADC on it**, so nothing you send down it ever comes back. The readout line is one cable carrying eight resonators at eight frequencies, and it is the only path with a digitizer at the end. The flux line is filtered to millisecond time constants on purpose, because its job is to hold a voltage still while the qubit frequency tracks it.

**Every operation today puts a voltage on one of those three, or records what comes back up the readout return.**

---

## The frame you do arithmetic in

The Bloch vector precesses about $z$ at $f_{01}$, so 4.85 turns every nanosecond. A 40 ns pulse spans 194 carrier cycles. Nobody does trigonometry at that rate.

- Change to a frame spinning about $z$ at the drive frequency. On resonance the precession stops and the Bloch vector holds still until you push it.
- A drive $\Omega(t)\cos(2\pi f_d t + \phi)$ becomes, in that frame and after dropping the term counter-rotating at $2f_d$, a **static field in the equatorial plane** of magnitude $\Omega(t)/2$ pointing at azimuth $\phi$.
- The instrument lives in the same frame. Every output has a numerically controlled oscillator holding one running phase, and every carrier it emits is referenced to that phase.

> Two claims follow from the second bullet, and between them they are every single-qubit gate.

---

## Area is the angle, phase is the axis

$$\theta = \int_0^{\tau}\Omega(t)\,\mathrm{d}t$$

The rotation angle is the integrated Rabi frequency and $\Omega(t)$ is proportional to the envelope, so the **area** under the envelope is the only property of it the angle depends on.

- A 40 ns Gaussian with $\sigma = 10$ ns has area $\sigma\sqrt{2\pi} = 25$ ns, so a $\pi$ rotation needs a peak Rabi rate near $\pi/25$ ns, or **20 MHz**.
- Half the amplitude is half the area, so `X/2` is the same envelope at half the height. On this chip $a_\pi = 0.62$ in DAC units and $a_{\pi/2} = 0.31$.
- The carrier phase $\phi$ sets the azimuth of the axis, so `Y` is `X` with $\phi$ advanced by 90 degrees. Same envelope, same duration, same calibration.

<p class="center"><strong>One envelope, two knobs, every single-qubit rotation.</strong></p>

---

## The two knobs, drawn

![h:450](img/rotation.svg)

<p class="cap">The carrier phase picks the axis in the equatorial plane; the area under the envelope picks how far around it the state goes. Same shape at half the height is half the angle.</p>

---

## Why the envelope is not square

A transmon is a ladder, not a two-level system. $|1\rangle \to |2\rangle$ sits $|\alpha| = 300$ MHz below the transition you are aiming at, with a matrix element $\sqrt{2}$ larger.

- Drive the lower transition at Rabi rate $\Omega$ and the upper one is driven too, off resonance by $\alpha$, putting population in $|2\rangle$ at order $(\Omega/\alpha)^2$. Most comes back at the end. What stays is **leakage**, and no later correction recovers it.
- 20 MHz against 300 MHz is $4\times10^{-3}$. Shorten the pulse to 10 ns, the peak rate goes to 80 MHz and the ratio to 7 percent. **Fast gates are why any of this matters.**
- A square edge is broadband and puts power straight onto the transition you are avoiding. A Gaussian of width $\sigma$ has a spectrum $1/(2\pi\sigma)$ wide, so $\sigma = 10$ ns holds the drive inside 16 MHz.
- **DRAG** adds a quadrature term $Q(t) = \beta\,\dot{I}(t)$, cancelling the leading transfer to $|2\rangle$ and the phase error it leaves on $|1\rangle$. First order says $\beta \approx 1/|\alpha|$, and nobody uses that value. $\beta$ is calibrated per qubit.

---

## The gate that plays nothing

A rotation about $z$ is a rotation of the reference frame, and the instrument already keeps that frame in a phase register.

- To apply $Z(\theta)$, advance the phase of **every later pulse on that line** by $-\theta$ and stop. No waveform, no samples, no time on the clock.
- **Zero duration and zero error.** The only thing that can go wrong is bookkeeping, and bookkeeping is exact.
- Compilers push every $Z$ they can into that register, so a hardware gate set is often just $X/2$ and $Z(\theta)$. Any single-qubit unitary is two $X/2$ pulses with three phase advances around them, and only the two pulses cost time.
- On the instrument it is one write to an oscillator's phase. In a pulse program it is one node with no duration.

---

## Two qubits, one gate

Nothing done on a single line entangles anything. Two qubits interact because they are coupled, through a bus resonator or a direct capacitance, and a gate is an interval during which you let that coupling act.

- **Flux route.** Push one qubit with a flux pulse until $|11\rangle$ and $|02\rangle$ are degenerate, hold, come back. The pair picks up a conditional phase. 40 to 100 ns, and it drags the qubit off its sweet spot for the duration.
- **All-microwave route.** Drive qubit A at qubit B's frequency and the coupling turns that into a rotation on B conditioned on A. 200 to 500 ns, and neither qubit moves.
- Calibrated **per pair**, by a two-dimensional scan rather than a formula. Amplitude against duration, hunting for where the population comes all the way back. Part 6 scans one.
- A 200 ns gate spends five times as long exposed to decoherence as a 40 ns pulse. Two-qubit error runs five to ten times single-qubit error, so a circuit's error budget is mostly a count of two-qubit gates.

---

## You never measure the qubit

The drive line has no ADC, and nothing at 7.2 GHz couples to something at 4.85 GHz. The qubit is observed only through a **resonator** beside it, and only because of one term in the Hamiltonian.

- Coupled at rate $g$, detuned by $\Delta = f_{01} - f_r = -2.35$ GHz. With $g \ll |\Delta|$ they can no longer exchange energy, so they shift each other instead.
- The resonator lands at $f_r \pm \chi$ depending on the qubit's state, and that shift is the whole measurement. Everything else in the chain is plumbing.
- The approximation has a ceiling, and the ceiling is a photon number. Above $n_{\text{crit}} = \Delta^2/4g^2 \approx 37$ photons the pull washes out and the resonator falls back to bare $f_r$. Part 2 maps that crossover and picks a readout power from it.

$$\chi = \frac{g^2}{\Delta}\cdot\frac{\alpha}{\Delta+\alpha} = -1.8\ \text{MHz}, \qquad 2\chi = 3.6\ \text{MHz}$$

---

## From a tone to one complex number

Send a 2 microsecond tone down the feedline. What comes back is the same tone with a state-dependent amplitude and phase on it, and six things happen before any of it is a bit.

1. The resonator fills, and the returned field picks up $\pm\arctan(2\chi/\kappa)$ of phase.
2. A parametric amplifier at 10 mK, a HEMT at 4 K, ordinary amplifiers at room temperature.
3. Down-conversion to an intermediate frequency, then an ADC sampling at 1 GSa/s.
4. Digital demodulation against $e^{-i2\pi f_{\text{IF}}t}$, then multiplication by **integration weights** $w(t)$.
5. Sum over the window. **One complex number per shot.**
6. Many shots, two clouds in the IQ plane, and a threshold between them.

The weights are their own calibration. The optimal choice is the difference between the mean $|0\rangle$ and $|1\rangle$ responses, sample by sample, so the window is weighted towards the part where the two states have actually separated.

---

## The measurement chain, end to end

![h:450](img/dispersive.svg)

<p class="cap">Two dips 3.6 MHz apart, a tone parked on one of them, and everything after the chip working to keep a few tens of photons alive. It ends as two clouds and a threshold.</p>

---

## What sets the 2 microseconds and the 1 percent

- The cavity has to fill before it says anything. $\kappa = 1.5$ MHz gives $1/\kappa = 106$ ns, so a 100 ns tone is mostly transient. **2 us is nineteen fill times.**
- Integrating longer beats the amplifier noise down as $\sqrt{t}$, so the clouds separate the longer you look. The ceiling is $T_1$, because a qubit that decays mid-window is misclassified. 2 us against 18 us spends about a ninth of that budget.
- The separation $d$ grows with photon number and with $2\chi/\kappa$, and the optimum is $2\chi/\kappa \approx 1$. Below it the two resonances overlap; above it a tone parked on one is simply off the other. This chip sits at **2.4**, past the peak.

Everything else is $d$ against the cloud width $\sigma$, and the fall-off is steep enough that every factor of two feels like a different chip.

$$\varepsilon = \tfrac{1}{2}\,\mathrm{erfc}\!\left(\frac{d}{2\sqrt{2}\,\sigma}\right) \qquad 4\sigma \to 2\% \qquad 6\sigma \to 0.1\%$$

---

## Three timescales and one inequality

| | this chip | what it measures |
|---|---|---|
| $T_1$ | 18 us | energy leaving the qubit and not coming back |
| $T_2^{*}$ | 9 us | plus every source of frequency wander, unfiltered |
| $T_2$ echo | 16 us | plus a $\pi$ pulse in the middle, refocusing anything slower than the sequence |

$$\frac{1}{T_2} = \frac{1}{2T_1} + \frac{1}{T_\varphi}$$

Relaxation contributes half its rate to dephasing, so $T_2 \le 2T_1$ is arithmetic rather than convention, and nothing on this chip can show a $T_2$ past 36 us.

The gap between the last two rows is itself a measurement of the noise. $T_\varphi^{*} = 12$ us against $T_\varphi = 29$ us means the echo removed about 60 percent of the dephasing rate, so most of what causes it is slow compared to the sequence, below roughly 50 kHz.

---

## Where the noise comes from

- **Two-level defects** in the amorphous oxide at the junction and at every metal interface. They absorb at whatever frequency they sit at, they move, and a qubit measured hourly for a day shows $T_1$ wandering by a factor of two. A single $T_1$ is a snapshot; the honest form is a histogram.
- **Quasiparticles**, broken Cooper pairs raised by stray infrared and by cosmic rays. Fought with shielding and filtering rather than with design.
- **$1/f$ flux noise**, the reason a tunable qubit has a sweet spot and the reason every coherence number here was measured at it. At the flat top of the flux arc $\mathrm{d}f_{01}/\mathrm{d}\Phi = 0$ and first-order flux noise does nothing.
- **Purcell decay** down the readout line, at rate $\kappa(g/\Delta)^2$. Couple hard enough to read out fast and you have built the qubit an exit.

All four drift, on timescales from minutes to months. Here is the chip they add up to, and after it, what having to measure all of this every morning costs you.

---

## The device we are calibrating

One simulated transmon, and every number in it is a number you will recover from a fit today.

| | | |
|---|---|---|
| $f_{01}$ = 4.85 GHz | $f_r$ = 7.20 GHz | $\Delta$ = $-2.35$ GHz |
| $\kappa$ = 1.5 MHz ($Q_L$ = 4800) | $\chi$ = $-1.8$ MHz | $2\chi/\kappa$ = 2.4 |
| $T_1$ = 18 us | $T_2^{*}$ = 9 us | $T_2$ = 16 us |

Photograph this one. Every constraint between these numbers was argued a few slides back, and from here on they are just the truth values your fits have to land on.

> Every fit you run today prints its answer next to the truth, so you can grade yourself.

---

## A chip arrives with no numbers on it

A circuit says `X(q0)`. Before an instrument can emit it, somebody has to supply all of this.

```text
40 ns DRAG envelope,  IQ pair,  carrier 4.8501 GHz,  amplitude 0.6176,  sigma 10 ns,  beta 0.1
```

Six numbers, and **every one of them was measured**, on this chip, this week, by a scan with no gate-level spelling. A dozen of those scans have to succeed in order, because each one consumes the answer from the last.

<p class="big">resonator → qubit → π pulse → coherence → readout → reset</p>

You cannot find the qubit before you can read it out, and you cannot fit a $\pi$ amplitude before you know where the qubit is. Then the numbers move. A resonator shifts when the fridge warms by a millikelvin, and $a_\pi$ is a $\pi$ amplitude until the attenuator chain drifts. Tomorrow the whole sequence runs again.

---

## What a control script has to express

- **Timed waveforms on named lines.** Not "apply X to q0" but "play this 40 ns envelope on this signal path, at this carrier, at this amplitude".
- **A clock per line.** Three lines advance independently, and a barrier between them is an explicit instruction rather than a property of the notation.
- **Parameter sweeps.** 81 carrier frequencies, 41 amplitudes, 41 delays. Nested or stepped in lockstep, and the nesting has to survive into the shape of the result.
- **Shot averaging.** 200 repetitions that collapse into one number instead of adding an axis.
- **Acquisition with weights.** A window, a weight vector, and a choice of what to keep, raw samples or an integrated point or a classified bit.
- **A branch on a measurement, inside the shot.** Read, then fire a $\pi$ pulse only if the answer was 1, in the few microseconds before the qubit forgets.

> None of that has a gate-level spelling, and the last one breaks every abstraction above it.

---

## Why a language, and not a script per rack

Physics moves between labs. You read a paper, you reproduce the measurement, nobody ships you a machine. Control code has never moved at all.

- Every vendor ships its own sequencer dialect, all assembly-shaped for a good reason. An FPGA has to hit a 4 ns clock edge without asking permission, so loops come out of registers, branches are counted in cycles, and waveform memory is addressed by hand.
- Correct, fast, welded to one box. A second rack means rewriting experiments that were already correct, then spending a month re-earning trust in them.
- One decision gets hard-coded on line one of every script. **Which loops run in the sequencer and which run on the control PC.** A 101-point sweep at 200 shots is 20,200 executions, 0.2 seconds in a sequencer with active reset and 20 seconds at one host round trip per point.
- A factor of a hundred, decided by a fact about the rack rather than a fact about the experiment. It is the first thing that does not belong in the file.

---

## What QProgram is, and what it leaves alone

A Python builder that produces an **AST**. `program.play(...)` appends a typed `Play` node and sends nothing to an instrument. Everything else in the library reads that one tree: `qp.dumps` writes it out, `qp.validate` classifies it against a machine, `qp.optimize` rewrites it, and a platform's `execute` interprets it.

- A **text format**. `.qp` round-trips the tree exactly, so an experiment is a file you can diff, review, and rerun next year. Part 1 asserts `qp.loads(qp.dumps(p)).body == p.body` on the first program it builds.
- A **capability protocol**. A platform declares what it supports per bus and per execution domain, and a program is checked against that declaration before anything reaches a sequencer.
- A **reference platform** that walks the tree in pure Python. It is the oracle a vendor compiler gets tested against.

Not a compiler, not a scheduler, not a physics model. Those stay with the vendor, behind `PlatformProtocol`, an interface six abstract methods wide.

---

## The architecture

![h:480](img/stack.svg)

<p class="cap">Your script builds a tree. Validation decides what runs where. The platform compiles and runs it. The <code>.qp</code> and <code>.wfl</code> files fall out as artifacts.</p>

---

## A bus is one signal path

![h:470](img/buses.svg)

<p class="cap">One qubit owns three lines that share nothing, and one feedline carries every readout at once. So an operation names the <em>line</em>, never the qubit.</p>

---

## Five words, and why each one is its own idea

- **Bus**, `q[0].drive`. A name that also carries its channel count and whether it can acquire. The schema writes that down as `readout info=IQ+acquires`, so a single-channel `Square` on an IQ line and a `measure` on a line with no ADC both raise on the line that wrote them.
- **Waveform**, `Gaussian(amplitude=0.3, duration=40, sigma=10)`. An envelope as data. Two of them compare with `==`, and each has a written form the parser reads back, so a pulse can be diffed rather than described.
- **Sweep source**, what a loop iterates over. It declares a `KIND` instead of handing over a list, and that one word decides whether a sequencer can run the loop or the control PC has to.
- **Average**, the shot loop. The only block that takes a dimension away rather than adding one.
- **Measurement handle**, what `measure()` returns. The one build-time value a run-time branch can read, so `handle.state == 1` becomes a condition the program itself carries.

---

## Capability, in three mechanisms

| mechanism | the question it answers | examples |
|---|---|---|
| **token** | is this in the set? | `op.play`, `waveform.iq_drag`, `sweep.logspace` |
| **limit** | is this number small enough? | `max_loop_nesting`, `max_measurements`, `min_wait_duration_ns` |
| **predicate** | given the rest of the program, is this legal? | no arbitrary sweep at `Wait.duration` |

There are 67 core tokens, and a set of them is cheap enough to serialize into a profile a vendor publishes. A limit is a hard wall rather than a preference, because a sequencer runs its loops out of registers and there is no spilling to memory. A predicate has to be code, since "this `wait` takes a variable, so what kind of sweep binds it?" asks about two nodes at once and no flat token answers that.

Every slot splits into an `rt` half and a `host` half, and either may be `None`. A flux DAC with no sequencer in it is `rt=None`, and that one field carries the whole of Part 5.

---

## Validation answers, and never raises

```text
[error] missing-capability: 'SetOffset' requires capability 'op.set_offset'
        which is not supported by 'dc-source' (host)      (at body[0][0][0])
```

`qp.validate(program, caps)` returns a `(diagnostics, plan)` pair. Ten codes exist, and the severity is the part you act on: an `error` cannot run, a `warning` runs degraded, an `info` names a rewrite you may want. `execute` turns an error into an exception, and a broken program is data you can print until then. Every node-bearing diagnostic carries a structural path, and `loads()` maps it to a line number.

The other half of the pair is an **execution plan**, one label per node.

| label | what it means |
|---|---|
| `[rt]` | real time, inside the sequencer |
| `[host]` | dispatched from the control PC, one round trip per iteration |
| `[rt\|host]` | either one, and the compiler picks |
| `[--]` | nothing can run it, and an error above says why |

---

## The simulator, honestly

`qp.simulate(program, model=...)` walks the tree in Python. Loops bind variables, measurements write records, and a conditional reads the handle the measurement just wrote. It models the **shape** of an experiment. Nesting, averaging, one record per `measure`, and `NaN` where an arm never ran.

It models **no timing and no waveform physics**. `wait` and `sync` change nothing in the numbers, and a $T_1$ curve decays because your model function read `env["delay"]`, not because a qubit relaxed.

The omission is a choice about what is under test. A tutorial with a Lindblad solver behind it teaches you to trust a simulation. This one puts the two things you actually carry to a fridge under test instead. The **program** has to say the right thing to a machine, and the **analysis** has to get the right number out of noisy data. Both are byte-identical here and on hardware.

---

<!-- _class: divider -->

<p class="kicker">Part 1 · notebooks/01_pulse_programs.ipynb</p>

# The program is data

### A readout pulse, a drive pulse, and the tree they build

---

## Part 1: twenty lines, and every one of them is a node

```text
body:
  block:
    set_frequency q[0].drive 4850000000.0
    set_gain q[0].drive 1.0
    reset_phase q[0].drive
    play q[0].drive IQDrag(amplitude=0.62, duration=40, sigma=10, beta=0.15)
    wait q[0].drive 4
  sync q[0].drive q[0].readout
  measure q[0].readout "readout" "weights" name="q0/readout/m0" fields=["state", "iq"]
```

Those nine lines are the whole of a prepare-and-read sequence, 20 on disk with its header and schema. `set_frequency` through `measure` each append exactly one node, and `body.walk()` hands them back in pre-order. Nothing has run yet.

Two things are already true of the text. The round trip is exact, so `qp.loads(qp.dumps(p)).body` compares equal to the body you built. And the schema types it against the chip, so a `measure` on `q[1].drive` raises `does not support acquisition` at the call that made the mistake.

---

## Part 1: every bus keeps its own clock

![h:430](img/timing.svg)

<p class="cap">A circuit has one global clock. A pulse program does not. The 40 ns pulse and the 4 ns wait book 44 ns on the drive bus and nothing at all on the readout bus, so <code>sync</code> is the barrier that moves the readout cursor to 44 ns.</p>

---

## Part 1: a waveform is data, not a call

```
same shape:        True     # Gaussian(0.5, 40, 8) == Gaussian(0.5, 40, 8)
one sigma apart:   False
the pi pulse:      True
distinct in a set: 2        # so a program can be asked how many pulses it really uses
```

`Gaussian`, `Square`, `FlatTop`, `Ramp`, `SuddenNetZero`, `IQDrag`, and an `Arbitrary` that takes a numpy array. Comparable, hashable, and each with a written form the parser reads back, so a pulse is diffed rather than described, and `body.waveforms()` reports three distinct envelopes in a program that plays five.

The DRAG correction from the opening is now a number you can read off the object. On the 0.62 amplitude $\pi$ pulse, `get_I()` peaks at 0.6192 and `get_Q()` at 0.0056, a hundred times smaller than the pulse it corrects. `beta` is a constructor argument, so retuning it makes a new object rather than editing a call site.

---

## Part 1: a number in the file is a claim the file cannot keep

```text
  play q[0].drive "pi"
  measure q[0].readout "readout" "weights" name="q0/readout/m0" fields=["state", "iq"]
```

`play(q[0].drive, "pi")` is a string alias that a `WaveformLibrary` resolves per bus when you bind one. A script with `amplitude=0.6176` written into it claims a calibration it cannot carry: six months on, the number is still there and the chip has moved. An alias claims nothing, because it holds nothing.

The claim moves into a file with its own history while the program text holds still, which also makes the `.qp` file a diff target. One changed pulse localises to `body[0][3]`, one node, not one file.

```diff
-    play q[0].drive IQDrag(amplitude=0.62, duration=40, sigma=10, beta=0.15)
+    play q[0].drive IQDrag(amplitude=0.31, duration=40, sigma=10, beta=0.15)
```

> 🧩 Build a two-qubit prepare-and-read sequence, then let the schema catch a `measure` on a drive line.

---

<!-- _class: divider -->

<p class="kicker">Part 2 · notebooks/02_sweeps_and_results.ipynb</p>

# Sweeps, averaging, and what comes back

### Resonator spectroscopy, then a punchout map

---

## Anatomy of a Rabi program

![h:430](img/anatomy.svg)

<p class="cap">Every node contributes something to the answer: <code>sweep</code> creates an axis, <code>average</code> collapses one, <code>measure</code> creates a record, and <code>play</code> carries the variable down into the waveform.</p>

---

## Part 2: a variable is a hole in the program

```python
freq = program.variable("ro_freq", label="Readout frequency", units="Hz")
with program.average(shots=200):
    with program.sweep(freq, qp.Range(7.19e9, 7.21e9, 0.2e6)):   # 101 points
        program.set_frequency(q[0].readout, freq)
        m0 = program.measure(q[0].readout, "readout", "weights")
```

You need the hole because a resonator's frequency depends on the kinetic inductance of whatever film got sputtered that day, and the fab does not know it better than a percent. One percent of 7.2 GHz is 72 MHz against a 1.5 MHz linewidth, so 200 kHz steps put seven or eight points across the dip and a 2 MHz grid steps straight over it. The fit then recovers $\kappa$ as 1.509 MHz against a true 1.500.

`average` is the block that takes a dimension away instead of adding one. Sixty-four sweep points go in and sixty-four come back, with `std(I)` falling from 0.5473 at one shot to 0.0305 at 256. That is $1/\sqrt{N}$, so halving the noise costs four times the measurement time.

---

## Part 2: what a sweep costs, three ways

101 points x 200 shots is the 20,200 executions the opening priced. Here is the whole table.

| where the loop runs | one execution | the whole scan |
|---|---|---|
| sequencer, passive reset | 2 us readout + $5T_1$ = 100 us | **2 s** |
| sequencer, active reset (Part 4) | a few us | **0.2 s** |
| host, one round trip per point | about 1 ms through driver and Python | **20 s** |

A factor of a hundred, decided by nothing in the physics. A sweep source therefore declares a `KIND` rather than handing over its numbers, and the platform reads it before it plans anything:

```
Range(start=7190000000.0, stop=7210000000.0, step=200000.0)  linear     101 points
Linspace(start=0.0, stop=1.0, num=21)                        linear      21 points
Values(points=array([0.  , 0.05, 0.1 , 0.15]))               arbitrary    4 points
Logspace(start=0.01, stop=1.0, num=21)                       arbitrary   21 points
```

A sequencer generates a `linear` source from a register. `Values` stays `arbitrary` even when its numbers are evenly spaced, because a list of floats proves nothing about its own regularity.

---

## Part 2: punchout, and the 37 photons

Dispersive readout works because qubit and resonator are coupled but far apart, so they shift each other without exchanging energy. That approximation has a validity limit, and the limit is a photon number:

$$n_{\text{crit}} = \frac{\Delta^2}{4g^2} \approx 37 \ \text{photons on this chip}$$

Below it the resonator sits at $f_r + \chi$. Above it the pull washes out and the resonator lands on bare $f_r$. A 25 x 41 grid at 50 shots, 51,250 samples, watches it happen:

```
amplitude 0.02 V  ->  dip at 7.198125 GHz      target f_r + chi = 7.198200 GHz
amplitude 1.00 V  ->  dip at 7.199875 GHz      target bare f_r  = 7.200000 GHz
frequency step 175 kHz, which is all the accuracy an argmin can have
```

The map is how you pick a readout power. Take as many photons as you can get for SNR, and few enough that there are still two states to tell apart. Park a few decibels below the crossover.

---

## Part 2: what comes back has your names on it

```
nested:   dims ('ro_amp', 'ro_freq', 'IQ')   shape (25, 41, 2)   outermost sweep first
lockstep: dims ('ro_amp|ro_freq', 'IQ')      shape (25, 2)       one axis, two coordinates
```

`result.get(m0)` is labeled `xarray`, and the dimension names are the variable ids you chose. Nested `with` statements are nested loops, so a two-deep nest is a grid of 1025 points. `sweep(a) | sweep(b)` advances both on the same tick and yields **one** dimension carrying two coordinate arrays, a diagonal cut rather than a grid. 25 measurements, not 1025.

Every figure in these notebooks is drawn by the library. `result.plot(m0)` finds the array the way `result.get(m0)` does, picks a line or a heatmap from its shape, and labels the axes from the `label=` and `units=` you put on the variable, so declare them on every one you sweep. It hands back the matplotlib `Axes`, so a fit is one more call on it, and `waveform.plot()` does the same for an envelope.

> 🧩 Scan both readout resonators in one lockstep sweep, and explain the single 41-long dimension that comes back.

---

<!-- _class: divider -->

<p class="kicker">Part 3 · notebooks/03_finding_the_qubit.ipynb</p>

# Finding and driving the qubit

### Two-tone spectroscopy, Rabi, and the flux arc

---

## Part 3: two tones, and a ceiling at 0.5

The drive line has no ADC, so the qubit shows up only as a shift in the resonator. Two tones, then. Park the readout in the dip and sweep a second one past $f_{01}$.

```text
    for drive_freq in Linspace(start=4840000000.0, stop=4860000000.0, num=81):
      set_frequency q[0].readout 7200000000.0   # park the readout in the dip
      set_frequency q[0].drive drive_freq       # and sweep the second tone past f01
      play q[0].drive IQPair(I=Square(amplitude=0.02, duration=4000), ...)
      sync
      measure q[0].readout "readout" "weights" name="q0/readout/m0" fields=["state"]
```

When the drive hits $f_{01}$ the resonator moves by $2\chi = 3.6$ MHz against a 1.5 MHz linewidth, and the tone that sat in the dip is suddenly off it. Read backwards, that chain is why Part 2 came first.

**A saturated transition tops out at 0.5.** The model gives 0.45 on resonance and 0.0011 twenty megahertz off. A two-tone peak above 0.5 means your classifier is wrong, not your qubit.

---

## Part 3: Rabi, and the number the rest of the day depends on

Fix the shape, sweep the amplitude. The rotation angle is proportional to the envelope area, so the population traces $\sin^2$ and the first maximum is the $\pi$ pulse. Ceiling of 1 this time, because a coherent rotation is not a pumped steady state.

$$P(a) = P_0 + C \sin^2\!\left(\frac{\pi a}{2 a_\pi}\right)$$

```
a_pi fitted : 0.6176 +/- 0.0022     contrast: 0.998   floor: 0.006
a_pi true   : 0.6200                error:    -0.39%
```

Fit for the parameter you want rather than a generic sinusoid, and `curve_fit` hands you the error bar on the number you care about. Contrast and floor come free and make a weekly health check: a floor that creeps up means a warm qubit or a drifting classifier.

The variable lives **inside** the waveform, `IQDrag(amplitude=amp, duration=40, sigma=10, beta=0.1)`, so the file records one parametric pulse rather than 41 literal ones.

---

## Part 3: the calibration leaves the program

```text
#!WaveformLibrary 1.0
"pi"  q[0].drive = IQDrag(amplitude=0.6176, duration=40, sigma=10, beta=0.1)
"x90" q[0].drive = IQDrag(amplitude=0.3088, duration=40, sigma=10, beta=0.1)
"readout" q[*].readout = IQPair(I=Square(amplitude=0.2, duration=2000), Q=Square(...))
"weights" = IQPair(I=Square(amplitude=1.0, duration=2000), Q=Square(...))
```

Three tiers, most specific first. `q[0].drive` is exact, because two qubits never share a $\pi$ amplitude. `q[*].readout` is a family, because one readout tone usually serves the row. `"weights"` is global, because integration weights belong to the measurement and not to a qubit.

`program.with_waveforms(library)` resolves the aliases and returns a new program. Bind last week's library and the same file plays `amplitude=0.5`; bind today's and it plays `0.6176`. The file on disk still says `play q[0].drive "pi"`, and that line stays true in both weeks.

---

## Part 3: the flux arc, and a loop you never classified

$$f_{01}(V) = f_{\max}\sqrt{\left|\cos\frac{\pi(V - V_0)}{V_\Phi}\right|}$$

```
f_max  fitted 4.852144 GHz +/- 0.912 MHz     true 4.850000 GHz
offset fitted +0.0498 V    +/- 0.0002 V      true +0.0500 V
period fitted  0.9978 V    +/- 0.0018 V      true  1.0000 V
```

The flat top is the **sweet spot** the opening named, and this scan locates it at $+0.0498$ V, to a fifth of a millivolt, off a grid whose own step is 16.7 mV. Now look at the program.

```text
    for bias in Linspace(start=-0.15, stop=0.25, num=25):    # a DC write into a filtered line, ms
      set_offset q[0].flux bias
      for arc_freq in Linspace(4300000000.0, 4900000000.0, 61):  # retune and fire, us
```

Two `for` loops written identically, on two boxes that share nothing. This way it is 25 host round trips; the other way, 76,000. **You never wrote down which was which**, and Part 5 settles it.

> 🧩 Fit the $\pi/2$ amplitude from the rising branch of the Rabi curve, instead of halving the $\pi$ amplitude.

---

<!-- _class: divider -->

<p class="kicker">Part 4 · notebooks/04_coherence_and_feedback.ipynb</p>

# Coherence, single shots, and feedback

### T1, Ramsey, echo, and a reset that reads the outcome

---

## Part 4: one sequence shape, three middles

Prepare, wait, read out. Only the middle changes, so write the pulse once. A `@fragment` is a named, parameterized sub-program; `program.call(x180, q[0].drive, 0.62)` appends one node and `expand()` substitutes it. Fragments round-trip into `.qp` as their own sections, so a pulse library is text too.

```text
fragment x180(drive, amp):
  play drive IQDrag(amplitude=amp, duration=40, sigma=10, beta=0.1)

body:
  x180(q[0].drive, 0.62)
```

| | fitted | true | the sweep behind it |
|---|---|---|---|
| $T_1$ | 18.00 us | 18.00 us | 41 delays out to 60 us, 400 shots |
| $T_2^{*}$ | 9.03 us | 9.00 us | 161 delays, drive parked 400 kHz off |
| $T_2$ echo | 15.65 us | 16.00 us | 51 delays, one $\pi$ pulse in the middle |

The three rows from the opening, now measured, with the same sequence shape all three times.

---

## Part 4: Ramsey measures two things at once

Park the drive 400 kHz off resonance on purpose, and one fit reads the coherence envelope and the frequency error out of the same fringes.

$$P_1(t) = \tfrac{1}{2}\left(1 + \cos(2\pi \delta t)\right) e^{-t/T_2^*}$$

```
fitted T2*      = 9.03 us     true = 9.00 us
fitted detuning = 399.8 kHz   true = 400.0 kHz
drive was at 4.850400 GHz  ->  corrected to 4.850000 GHz  (residual +0.2 kHz)
```

Two or three rounds and the drive is inside a kilohertz of $f_{01}$. It is the tune-up every lab runs each morning, and it is one program with one variable in it.

The echo row pays differently. 9.03 against 15.65 is the noise measurement the opening promised, now with error bars on it rather than a claim.

---

## Part 4: single shots, and an error that falls off a cliff

Stop averaging. Put the shot index in an explicit `sweep` and every shot lands in the array, because `average` was the only thing collapsing them. Two clouds appear, since the resonator sits at $f_r \pm \chi$ and each integrated point lands near one of two places.

$$\varepsilon = \tfrac{1}{2}\,\mathrm{erfc}\!\left(\frac{d}{2\sqrt{2}\sigma}\right) \qquad 4\sigma \to 2\% \qquad 6\sigma \to 0.1\%$$

```
blob separation  = 3.8 sigma
threshold        = +1.101
measured error   = 5.3%   (readout plus preparation)
assignment error = 3.1%   (readout alone)
```

$d$ grows with photon number and with $2\chi/\kappa$; $\sigma$ is amplifier noise over $\sqrt{t}$. Those two quantities are the whole of readout engineering, and the steepness of the `erfc` is why every factor of two in separation feels like a different chip.

---

## Part 4: read the outcome, act on it

```text
  for shot in Range(start=0.0, stop=399.0, step=1.0):
    measure q[0].readout "readout" "weights" name="check" fields=["state"]
    if check.state == 1:
      x180(q[0].drive, 0.62)
      sync
      measure q[0].readout "readout" "weights" name="verify" fields=["state"]
    else:
      wait q[0].drive 40
```

Passive reset costs $5T_1 = 90$ us per shot against a 2 us measurement, so more than 97 percent of fridge time is spent waiting. Reading the outcome and fixing it turns an afternoon into twenty minutes.

```
reset fired on 74 of 400 shots
population before reset = 18.5%     population after reset = 1.0%
```

The arm that did not run holds `NaN`, not zero, because a zero would read as a cold measurement. And a `measure` whose `fields=` omits `state` gets `missing-classification` before a shot is taken.

> 🧩 Build active reset on 400 single shots and report the excited population before and after.

---

<!-- _class: divider -->

<p class="kicker">Part 5 · notebooks/05_one_program_many_machines.ipynb</p>

# One program, many machines

### The same calibration, a different rack

---

## Part 5: why the flux line is a different instrument

Rack B puts a 20-bit DC source on the flux line instead of an AWG output, and that is not taste. Flux noise is the main thing dephasing this qubit and the frequency tracks the bias directly, so the flux line is the one path where broadband noise turns straight into decoherence.

**The filtering that keeps the line quiet is the filtering that keeps it slow.** Millisecond time constants, Ethernet, no FPGA. The two published profiles say so in numbers:

```
qblox-default-v1   31 tokens   limits {'min_wait_duration_ns': 4}
qdac-default-v1    16 tokens   limits {'min_dwell_ns': 100}
op.set_offset on a qblox sequencer: True     on a qdac channel: False
```

So three questions have to be answered before the program reaches an instrument. Does the rack implement every operation, waveform, and sweep shape used? Does it stay inside the numeric limits? And which loops run in the sequencer? `qp.validate(program, caps)` answers all three from the AST alone, with no instrument connected.

---

## Part 5: read the plan, then let optimize fix it

```text
body
└─ average 200:                                [host]     ~ forced-host  i reorderable-averaging
   └─ for bias in Linspace(-0.05, 0.15, 101):  [host]
      ├─ set_offset q[0].flux bias             [host]
      ├─ play q[0].drive "saturation"          [rt|host]
      ├─ sync q[0].drive q[0].readout          [rt|host]
      └─ measure q[0].readout "readout" ...    [rt|host]
```

The `average` fell to `[host]` because it *encloses* a host-side sweep. A warning, not an error, and it costs a factor of a hundred: all 20,200 executions become network round trips, twenty seconds instead of a fraction of one.

`reorderable-averaging` names the fix. `qp.optimize(program, caps)` rewrites `average { sweep { ... } }` into `sweep { setup; average { ... } }`, so the host does 101 DAC writes and the sequencer runs 20,200 iterations by itself. Zero warnings on the way out.

One habit blocks it. A bare `program.sync()` broadcasts over every bus, picks up the flux line, and the rewrite refuses to hoist across it. Name the two buses you mean.

---

## One program, two domains

![h:430](img/plan.svg)

<p class="cap">The drive and readout lines sit on a fast sequencer, the flux line on a slow DAC. The bias loop lands host-side, the shot loop stays in hardware, and <code>optimize()</code> is what gets them into that order.</p>

---

## Part 5: a warning on one rack, an error on the next

```text
└─ average 200:                                 [rt|host]  i reorderable-averaging
   └─ for bias in Linspace(-0.05, 0.15, 101):   [--]       !! mixed-domain
      ├─ qdac.set_offset q[0].flux bias         [host]
      ├─ set_frequency q[0].drive 4850000000.0  [rt]
      ├─ play q[0].drive "saturation"           [rt]
      └─ measure q[0].readout "readout" ...     [rt]
```

`qprogram-qdac` and `qprogram-qblox` register `qdac-default-v1` and `qblox-default-v1`, and neither talks to an instrument. A published profile lists what the box implements rather than what the language knows, so `qdac-default-v1` **refuses** `op.set_offset`. The flux line is spelled `program.qdac.set_offset`, and the file grows a `require qdac 0.1` line.

Hand-built rack B filled both halves of every fast slot, so the mixed loop was a `forced-host` warning. The real profiles fill one half each, and the same loop is a `mixed-domain` **error**, which makes `qp.optimize` the step that turns an illegal program into a legal one rather than a faster one.

---

## Part 5: rebind, and the file the calibration lives in

```
original: ['q0/drive', 'q0/flux', 'q0/readout']
renamed:  ['drive_q0', 'flux_q0', 'readout_q0']
moved:    ['q1/drive', 'q1/flux', 'q1/readout']
```

`program.rebind(naming=BusNaming("{kind}_{element}{index}"))` renames every bus **structurally**, so the refs stay typed and the channel checks survive. Find-and-replace gives you strings that look right and carry no metadata. `rebind(elements=...)` moves the experiment to another qubit and `rebind(schema=...)` to another chip layout, and the handle follows, `q0/readout/m0` to `readout_q0/m0`.

The waveform library lives outside the `.qp` file, in its own `.wfl`. The program is the experiment and changes when the experiment changes; the library is the calibration and changes every morning. Merge them and neither diff means anything, because a recalibration and a redesign then look identical.

> 🧩 Port the two-dimensional flux arc to a rack that names its buses `drive_q0` style, and check the diagnostics still match.

---

<!-- _class: divider -->

<p class="kicker">Part 6 · notebooks/06_extending_and_shipping.ipynb</p>

# Extending the language and shipping the work

### Your own waveform, your own vendor, and the bring-up in one script

---

## Part 6: a DSL that cannot be extended gets forked

And a forked DSL is not a portable format any more. It is three dialects sharing a file extension. So the extension points are what keep Part 5 true, and there are three of them.

| you want | you write | you get for free |
|---|---|---|
| a pulse shape the DSL lacks | a `Waveform` subclass, `@qp.register_waveform` | `.qp` serialization off the constructor signature, structural equality, validation |
| a sweep axis the DSL lacks | a `SweepSource` subclass, `@qp.register_sweep_source` | serialization, a capability token, lockstep length checks, xarray coordinates |
| an operation the DSL will never have | an `Operation` plus a `VendorNamespace`, four registration calls | `program.<vendor>.<op>(...)`, a `require` line, a `vendor.<name>.<op>` token |

Serialization is read off your constructor signature, so the constructor arguments have to **be** the state. And a sweep source **may not wrap a callable**: a callable cannot report its length before it runs, cannot honestly declare a kind, and cannot serialize. Three load-bearing properties, all gone at once. That one restriction is the whole design of the seam.

---

## Part 6: all three in one file, and the file still travels

```text
#!QProgram 1.0
require fridge 0.1

body:
  var flux_amp label="Flux amplitude" units="V"
  fridge.set_attenuation q[0].drive 20.0
  average 200:
    for flux_amp in Chevron(center=0.42, span=0.2, num=21):
      play q[0].flux HalfSine(amplitude=flux_amp, duration=40)
      sync
      measure q[0].readout "readout" "weights" name="q0/readout/m0" fields=["state"]
```

A vendor operation, a vendor waveform, and a vendor sweep source, written in three notebook cells with no patch to the core. The source reports `length: 21`, `kind: arbitrary`, and asks a platform for `['sweep.arbitrary', 'sweep.chevron']`, so it is checked like everything else.

A rack without the token marks that node `[--]` and says `missing-capability: 'SetAttenuation' requires 'vendor.fridge.set_attenuation'`. A fork would have given you a working program on your own rack and a syntax error on everybody else's.

---

## Part 6: a file that outlives its author

```
[project.entry-points."qprogram.vendors"]
qblox = "qprogram_qblox"
```

```
vendor namespaces registered before the load: ['fridge']
vendor namespaces registered after the load:  ['fridge', 'qblox']
```

A `require qblox 0.1` line at the top of a file makes the parser find that entry point and import the extension on the spot. So a six-month-old `.qp` file loads in a fresh environment without the reader knowing what the author happened to have installed. A vendor nobody claims fails by name, and the message says which package to go and install:

```
Line 3: file requires vendor 'acme_rack' 0.1 but no matching extension is
registered in this environment ... the 'qprogram.vendors' entry point ...
```

---

## Part 6: the diff, and the checker

```diff
-  set_frequency q[0].readout 7200000000.0
+  set_frequency q[0].readout 7200400000.0
-  average 200:
+  average 400:
-    for amp in Linspace(start=0.0, stop=1.0, num=41):
+    for amp in Linspace(start=0.0, stop=0.8, num=41):
```

Monday against Friday, on somebody else's chip. The resonator moved 400 kHz, the shot count doubled, and the amplitude range came down because the $\pi$ pulse landed lower than expected. You can reconstruct a week from a text diff, and none of it was ever in a plot.

```
$ python -m qprogram.lsp check rabi_broken.qp        (exit 1)
  line 18: [error] parse-error: Line 18: bus path 'q[0].drve' does not resolve
  against the program schema: 'q' has no bus 'drve'. Available: drive, readout, flux
```

JSON diagnostics and a non-zero exit, so it is a CI job on the day you write it. `explain` prints the plan tree the same way. Neither needs an extra dependency.

> 🧩 Add a vendor measurement field, then prove it is legal on one rack and rejected on another.

---

## The bring-up, end to end

```
quantity              measured        true    error
f_r (GHz)               7.2000      7.2000     0.0%
f_01 (GHz)              4.8500      4.8500     0.0%
a_pi (DAC)              0.6191      0.6200     0.2%
T1 (us)                17.8634     18.0000     0.8%
T2* (us)                8.9410      9.0000     0.7%
T2 echo (us)           15.8509     16.0000     0.9%
```

Seven steps in order, each consuming the answer from the last, and the capstone writes a `.qp` per step plus one `calibration.wfl`. One set of primitives underneath all of it: `BusSchema`, `Waveform`, `Variable`, `SweepSource`, `Fragment`, `MeasurementField`, assembled into an **AST**, checked against **capabilities**, run by a swappable **platform**.

Here that takes seconds. On hardware with passive reset it is about ten minutes, and the reason to automate it is the fifty qubits after this one, not those ten.

> Two vendor packages, imported for what they declare rather than for what they drive. Nothing today talked to an instrument, and nothing today was written twice.

---

## Where to go next

- **Docs**: [qilimanjaro-tech.github.io/qprogram](https://qilimanjaro-tech.github.io/qprogram) · **Source**: [github.com/qilimanjaro-tech/qprogram](https://github.com/qilimanjaro-tech/qprogram)
- The published Reference section is the normative material. `docs/reference/qp-format.md` covers the text format, and `src/qprogram/grammar/qp.lark` is the machine-readable grammar.
- `qprogram-qblox` and `qprogram-qdac` are worked vendor extensions, and Part 5 built a rack out of their profiles. Read one before you write your own.
- Bring a rule your lab cares about and write it as a predicate. It is the cheapest way to find out whether the protocol fits your rack.
- Issues and pull requests are welcome. The extension points are the API.

---

<!-- _class: lead -->
<!-- _footer: '' -->

# Thank you

<p class="sub">Questions, and the notebooks are yours to keep</p>

<p class="meta">vyron@qilimanjaro.tech · flavie.lebars@qilimanjaro.tech · QCE 2026</p>
