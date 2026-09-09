---
marp: true
size: 16:9
paginate: true
math: katex
title: Pulse-level Programming with QProgram
footer: 'Pulse-level Programming with QProgram · QCE 2026'

---

<style>
@font-face {
  font-family: "Plus Jakarta Sans";
  src: url("fonts/PlusJakartaSans-Regular.ttf") format("truetype");
  font-weight: 400; font-style: normal;
}
@font-face {
  font-family: "Plus Jakarta Sans";
  src: url("fonts/PlusJakartaSans-SemiBold.ttf") format("truetype");
  font-weight: 600; font-style: normal;
}
@font-face {
  font-family: "Plus Jakarta Sans";
  src: url("fonts/PlusJakartaSans-Bold.ttf") format("truetype");
  font-weight: 700; font-style: normal;
}

:root {
  --accent: #3d1a94;
  --accent-soft: #ece7fa;
  --accent2: #c6093f;
  --accent2-soft: #fbe7ec;
  --ink: #1c1c2e;
}
section {
  font-family: "Plus Jakarta Sans", -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
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
  background: var(--accent-soft); color: var(--accent);
  padding: 2px 7px; border-radius: 5px; font-size: 0.86em;
}
pre { font-size: 0.72em; line-height: 1.35; }
pre code { background: none; padding: 0; }
table { font-size: 0.76em; margin-left: 40px; }
th { background: var(--accent-soft); color: var(--accent); border-bottom: 2px solid var(--accent2); }
blockquote { font-size: 0.86em; color: #4a4a62; border-left: 4px solid var(--accent2); padding-left: 16px; }
footer { color: #9a9ab0; font-size: 0.5em; }
section::after { color: #b6b6c8; font-weight: 600; }

section.lead {
  display: flex; flex-direction: column;
  background: #05040c url("img/dark-gradient-bg.png") no-repeat center / cover;
  color: #fff; text-align: left;
  justify-content: center; align-items: flex-start;
}
section.lead h1 { font-size: 2.1em; margin: 0 0 0.2em; color: #fff; font-weight: 400; }
section.lead .sub { font-size: 1.15em; color: rgba(255,255,255,.85); }
section.lead .meta { font-size: 0.8em; color: rgba(255,255,255,.6); margin-top: 1.2em; }
section.lead .logo { width: 260px; margin: 0; }
section.lead .lead-text { width: 100%; margin-top: 50px; }

section.lead.center { justify-content: center; align-items: center; text-align: center; }
section.lead.center h1 { font-size: 2.3em; margin: 0 0 0.15em; }
section.lead.center .sub { margin: 0.2em 0; }
section.lead.center .logo { width: 460px; margin: 0 0 32px; }

section.divider {
  display: flex; flex-direction: column;
  background: linear-gradient(135deg, #c6093f 0%, #7f1997 45%, #2f2eff 100%);
  color: #fff; justify-content: center;
}
section.divider h1, section.divider h2, section.divider h3 { color: #fff; }
section.divider strong { color: #ffd866; }
section.divider .kicker { font-size: 0.8em; letter-spacing: .18em; text-transform: uppercase; color: #fff; opacity: .85; }
section.divider code { background: rgba(255,255,255,.18); color: #fff; }

section img { display: block; margin: 0 auto; }
.cap { font-size: 0.72em; color: #6a6a82; text-align: center; margin-top: 6px; }
.center { text-align: center; }
.small { font-size: 0.82em; }
.big {
  font-size: 1.5em; color: var(--accent); font-weight: 700; text-align: center;
  margin: 0.5em auto; padding: 0.4em 0.9em; max-width: fit-content;
  background: var(--accent-soft); border-radius: 12px;
}
.hl { color: var(--accent2); font-weight: 700; }
.callout {
  border-left: 4px solid var(--accent2); background: var(--accent2-soft);
  padding: 10px 18px; border-radius: 0 8px 8px 0; margin: 0.6em 0;
}

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

<img class="logo" src="img/qilimanjaro-logo-white.png" alt="Qilimanjaro Quantum Tech" />

<div class="lead-text">

# Pulse-level Programming with QProgram

<p class="meta">IEEE Quantum Week · QCE 2026</p>

</div>

---

## The presenters

- **Vyron Vasileiadis**, Tech Lead at **Qilimanjaro Quantum Tech** · vyron@qilimanjaro.tech
- **Flavie Le Bars**, Quantum Software Engineer at **Qilimanjaro Quantum Tech** · flavie.lebars@qilimanjaro.tech

---

## Qilimanjaro

- **Qilimanjaro Quantum Tech** builds analog quantum processors on superconducting fluxonium qubits, plus the software stack that drives them.
- Full-stack: hardware, control electronics, software, and cloud access, under one roof.
- Founded in 2019, based in Barcelona.

---

## QProgram

- **QProgram** is the pulse-level layer of that stack, an open-source Python DSL.
- Hardware-agnostic: the same program targets a Qblox cluster, a QDevil QDAC, or the reference simulator.
- Modality- and paradigm-agnostic too, since a transmon and a fluxonium, or a gate model and an annealer, all come down to pulse-level programming.

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

- Follow the **README** linked by the QR code above for installation instructions, troubleshooting, and the `uv` setup option.
- The examples run locally using the reference platform included in the package. You do not need hardware or a cloud account.
- Open `notebooks/01_introduction.ipynb` and run the first two cells to check your environment.

---

## How we work

- Each section starts with slides that introduce the main ideas, followed by notebook examples and an exercise.
- Complete the `# TODO` cells in `notebooks/`. Solutions are available in `notebooks/solutions/`.

| Topic | Notebook | Time |
|---|---|---|
| Background: superconducting qubits, control hardware, and pulse programming | | 40 min |
| Operations, schemas, waveforms, and `.qp` files | `01_introduction` | 25 min |
| Variables, sweeps, and results | `02_basics` | 25 min |
| **Break** | | |
| Fragments, feedback, extensions, and platforms | `03_advanced` | 75 min |
| Questions and closing discussion | | 10 min |

---

## What you will build

- A **pulse program** you can inspect, save, reload, and compare across versions (`01_introduction`).
- A **resonator frequency scan**, a **two-dimensional parameter map**, and a **sweep that changes two parameters together** (`02_basics`).
- An **active reset sequence** that uses a measurement result to decide whether to apply a correction pulse (`03_advanced`).
- A custom **waveform**, **sweep source**, and **vendor operation** (`03_advanced`).
- A simple **platform implementation**, with an **execution plan** that describes how the program would run (`03_advanced`).

---

## Acronyms

| Acronym | Meaning |
|---|---|
| **ADC** | Analog-to-digital converter |
| **AST** | Abstract syntax tree |
| **DAC** | Digital-to-analog converter |
| **DRAG** | Derivative removal by adiabatic gate |
| **DSL** | Domain-specific language |
| **FPGA** | Field-programmable gate array |
| **IQ** | In-phase and quadrature |
| **LC** | Inductor-capacitor circuit |
| **LO** | Local oscillator |

---

<!-- _class: divider -->

<p class="kicker">Lecture introduction</p>

# The chip and the control hardware

### How electrical signals control and measure a superconducting qubit

---

## The LC oscillator

- An LC circuit contains a capacitor and an inductor. Energy oscillates between the capacitor's electric field and the inductor's magnetic field.
- In the quantum description, an ideal LC oscillator has **equally spaced energy levels**.
- The transitions $|0\rangle \to |1\rangle$ and $|1\rangle \to |2\rangle$ therefore have the same frequency.
- To address the lowest two levels selectively, we need a circuit with **unequal level spacings**.

<!-- Reference: Krantz et al., A quantum engineer's guide to superconducting qubits (2019), https://arxiv.org/abs/1904.06560. -->

---

## The Josephson junction

- A Josephson junction consists of two superconductors separated by a thin insulating barrier.
- It acts as a **nonlinear inductor**, replacing the linear inductor in our oscillator.
- The supercurrent follows $I = I_c\sin\varphi$, where $I_c$ is the critical current and $\varphi$ is the superconducting phase difference across the junction.
- This nonlinearity makes the energy levels unequally spaced, allowing us to distinguish the qubit transition from higher transitions.

---

## Anharmonicity

Ignoring offset charge, the circuit Hamiltonian is

$$\hat H = 4E_C\hat n^2 - E_J\cos\hat\varphi.$$

- $E_C$ is the charging energy and $E_J$ the Josephson energy; $\hat n$ and $\hat\varphi$ describe the Cooper-pair number and phase difference.
- The cosine potential gives smaller level spacings at higher energies.
- The **anharmonicity** is $\alpha = f_{12} - f_{01}$. For example, $\alpha = -300\ \text{MHz}$ places the second transition 300 MHz below the qubit transition.
- Keeping the pulse bandwidth well below $|\alpha|$ helps avoid exciting $|2\rangle$.

<!-- Reference: Koch et al., Charge-insensitive qubit design derived from the Cooper pair box (2007), https://arxiv.org/abs/cond-mat/0703002. -->

---

## The transmon

![h:440](img/transmon.svg)

<p class="cap">A transmon combines a Josephson junction with a large shunt capacitor. The capacitor reduces sensitivity to charge noise, while the junction provides the unequal level spacings needed to address the qubit transition.</p>

---

## Tuning with flux

- Replacing the single junction with two junctions in a superconducting loop makes the effective Josephson energy tunable.
- Current in a nearby flux line changes the magnetic flux through the loop, shifting $f_{01}$.
- For a symmetric junction pair, an approximate tuning curve is

$$f_{01}(V) \approx f_{\max}\sqrt{\left|\cos\frac{\pi(V - V_0)}{V_\Phi}\right|}.$$

- $V_0$ is a bias at the maximum frequency; $V_\Phi$ is the voltage period.
- At a **sweet spot**, the slope is zero, reducing sensitivity to small flux fluctuations. Higher-order sensitivity remains.

<!-- This approximation neglects the charging-energy correction and breaks down near the frequency minima. Reference: Koch et al. (2007), https://arxiv.org/abs/cond-mat/0703002. -->

---

## The control rack

![h:470](img/rack.svg)

<p class="cap">The control electronics generate microwave and flux signals for the chip. The readout electronics digitise the returning signal after amplification.</p>

---

## The dilution refrigerator

![h:480](img/fridge.svg)

<p class="cap">The refrigerator cools the chip to millikelvin temperatures. Attenuators and filters reduce incoming noise; low-noise amplifiers strengthen the weak readout signal on its way out.</p>

---

## Control and readout lines

| Line | Example signal | Purpose |
|---|---|---|
| **Drive** | A microwave pulse near $f_{01} = 4.85\ \text{GHz}$ | Rotate the qubit state |
| **Readout** | A microwave pulse near $f_r = 7.20\ \text{GHz}$ | Probe a resonator coupled to the qubit |
| **Flux** | A DC bias or a timed flux pulse | Adjust the qubit frequency |

- These frequencies are illustrative; actual values come from device calibration.
- In the notebooks, **buses** identify the signal paths used for control and acquisition.

---

## The rotating frame

- In the laboratory frame, the qubit's relative phase evolves at its transition frequency.
- We describe the state in a frame rotating at the drive frequency, so the remaining free precession depends on the **detuning**.
- On resonance, this free precession vanishes. An applied drive still rotates the state.
- The control electronics track a phase reference so that successive pulses have the intended relative phases.

---

## Pulse area and phase

For an ideal resonant pulse with a fixed phase,

$$\theta = \int_0^{\tau}\Omega(t)\,\mathrm{d}t,$$

where $\Omega(t)$ is the angular Rabi frequency, in radians per second.

- The **pulse area** determines the rotation angle. In the linear response regime, halving the amplitude halves the angle.
- The **drive phase** determines the rotation axis in the equatorial plane. A 90-degree phase shift changes an $X$ rotation into a $Y$ rotation under the chosen phase convention.
- On hardware, pulse amplitudes and phases are calibrated to implement the desired gates.

---

## Axis and angle

![h:480](img/rotation.svg)

<p class="cap">For an ideal resonant pulse with fixed phase, the drive phase sets the rotation axis in the equatorial plane, and the envelope area sets the rotation angle.</p>

---

## Leakage

- A transmon has more than two energy levels. We use $|0\rangle$ and $|1\rangle$ as the computational states.
- Its $|1\rangle \to |2\rangle$ transition lies $|\alpha|$ below the qubit transition.
- Short or abruptly switched pulses have broad spectra and can excite this unwanted transition.
- Population left outside the computational states at the end of a gate is called **leakage**.
- Smooth envelopes and pulse corrections help reduce leakage while keeping gates short.

---

## DRAG

$$Q(t) = \beta\,\frac{\mathrm{d}I(t)}{\mathrm{d}t}$$

- **DRAG** adds a correction in the quadrature channel, 90 degrees from the in-phase drive.
- The correction follows the time derivative of the in-phase envelope $I(t)$.
- This helps suppress unwanted excitation of $|2\rangle$. Detuning or phase corrections can address the associated phase error.
- The coefficient $\beta$ sets the correction's scale and sign. Its value depends on the qubit and waveform convention and is calibrated experimentally.

<!-- Reference: Motzoi et al., Simple Pulses for Elimination of Leakage in Weakly Nonlinear Qubits (2009), https://doi.org/10.1103/PhysRevLett.103.110501. The coefficient in this continuous-time equation need not use the same normalisation as a waveform API's beta parameter. -->

---

## The IQ mixer

![h:470](img/mixer.svg)

<p class="cap">Two DAC outputs supply the I and Q envelopes. The mixer combines them with local-oscillator signals 90 degrees apart to control the amplitude and phase of the microwave output.</p>

---

## Virtual Z gates

- A **virtual Z gate** is implemented by updating the phase reference for subsequent control pulses.
- The phase update represents a rotation about $Z$ and requires no additional physical pulse duration.
- Later pulses use the updated reference so that their rotation axes remain consistent.
- Any single-qubit unitary can be composed from two $X_{\pi/2}$ pulses and virtual Z rotations, up to a global phase.

<!-- Reference: McKay et al., Efficient Z Gates for Quantum Processors (2017), https://doi.org/10.1103/PhysRevA.96.022330. -->

---

## Two-qubit gates

Two-qubit gates use the coupling between qubits to make their evolution depend on their joint state.

| Approach | Control mechanism | Example |
|---|---|---|
| **Flux tuning** | Tune a qubit near the avoided crossing between $\|11\rangle$ and $\|02\rangle$ to accumulate a conditional phase | Controlled-Z gate |
| **Microwave driving** | Drive one qubit near its neighbour's frequency to produce a state-dependent rotation | Cross-resonance gate |

- Flux tuning can move a qubit away from a sweet spot and increase its sensitivity to flux noise.
- Cross-resonance control can keep the qubit frequencies fixed.
- Pulse amplitude, duration, and phase corrections are calibrated for each pair. Gate speed and error depend on the device and implementation.

---

## Dispersive readout

- We measure the qubit by probing a **coupled resonator** with a microwave pulse.
- The detuning $\Delta = f_{01} - f_r$ is large compared with the coupling strength $g$; the resonator must also remain far from higher qubit transitions.
- In this **dispersive regime**, direct energy exchange is suppressed, but the qubit state shifts the resonator's response.
- Measuring that response lets us infer the qubit state.

<!-- Dispersive theory assumes sufficiently weak coupling relative to the relevant detunings and readout power below the breakdown of the approximation. Reference: Koch et al. (2007), https://arxiv.org/abs/cond-mat/0703002. -->

---

## The dispersive shift

- The resonator frequencies associated with $|0\rangle$ and $|1\rangle$ are separated by $2|\chi|$.
- A probe near these frequencies produces different amplitudes and phases for the two states.
- For a transmon, the leading dispersive approximation is

$$\chi \approx \frac{g^2\alpha}{\Delta(\Delta+\alpha)},$$

with $g$, $\Delta$, and $\alpha$ expressed in the same frequency units.

For example, $\chi = -1.8\ \text{MHz}$ gives a separation of $2|\chi| = 3.6\ \text{MHz}$.

<!-- Reference: Koch et al. (2007), Eq. (3.9), https://arxiv.org/abs/cond-mat/0703002. The numerical shift is illustrative; no numerical coupling g has been specified. -->

---

## The readout chain

![h:470](img/dispersive.svg)

<p class="cap">The readout signal is amplified, digitised, and processed into I and Q values. Repeated measurements form two distributions, and a decision threshold assigns each result to a qubit state.</p>

---

## Integration weights

- Integration weights determine how each sample contributes to the final I and Q values.
- To calibrate them, prepare $|0\rangle$ and $|1\rangle$ and measure the mean readout trace for each state.
- A common choice uses the difference between those traces, giving more weight to times when the responses are easier to distinguish.
- This matched-filter choice is optimal for additive white Gaussian noise with equal variance. Correlated or time-dependent noise can require different weights.

<!-- Reference: Khan et al., Practical Trainable Temporal Postprocessor for Multistate Quantum Measurement (2024), https://doi.org/10.1103/PRXQuantum.5.020364. -->

---

<!-- _class: divider -->

<p class="kicker">Lecture introduction</p>

# A language for pulse programs

### Expressing experiments across control platforms

---

## What a pulse program needs to express

- **Waveforms and timing:** play pulses on named buses at the intended times.
- **Synchronisation:** track each bus's timeline and align buses when required.
- **Parameter sweeps:** vary parameters in nested loops or step several parameters together.
- **Averaging:** repeat measurements and combine the results.
- **Acquisition:** specify integration weights and request raw traces, integrated IQ, or classified states.
- **Feedback:** use a measurement result to choose the next operation, as in active reset.

---

## Vendor control interfaces

- Control platforms differ in their instruction sets, timing constraints, and supported operations.
- Low-level sequencer code may expose registers, waveform memory, and hardware-specific loop instructions.
- When these details are embedded in an experiment script, moving to another platform requires changes to the script.
- A common program representation lets us describe the experiment separately from the platform-specific code that executes it.

---

## Where loops execute

- A loop can run on an instrument's sequencer when the hardware supports its operations and parameter updates.
- Other loops may need to run on the host computer, for example when they control an external instrument.
- Host execution can add communication and setup overhead at each step.
- The execution plan uses the program's requirements and the platform's capabilities to determine where loops can run.

---

## QProgram as a Python DSL

- QProgram uses Python to build a structured description of an experiment: an **abstract syntax tree**.
- Calling `program.play(...)` adds a typed `Play` node to that tree. Building the program does not send a pulse to hardware.
- The same structure supports inspection, validation, and serialisation.
- A platform implementing `PlatformProtocol` handles execution, including any compilation and scheduling required by its hardware.

---

## The architecture

![h:480](img/stack.svg)

<p class="cap">Python code builds a QProgram. Serialisation saves its structure, and a platform executes it and returns measurement results.</p>

---

<!-- _class: divider -->

<p class="kicker">Part 1 · notebooks/01_introduction.ipynb</p>

# QProgram fundamentals

### Operations, buses, waveforms, and saved programs

---

## Building a program

- Each operation adds a node to the program structure.
- Building a program does not execute it.
- You can inspect the operations, modify the program, and save it before running it.
- Validation checks the program against a platform's declared capabilities.

---

## Buses and signal paths

![h:300](img/buses.svg)

- A bus identifies the signal path targeted by an operation.
- The transmon schemas provide drive and readout buses. A flux-tunable transmon also has a flux bus.
- Bus names separate the program's operations from their physical instrument connections.

---

## Core operations

| Purpose | Methods |
|---|---|
| Play, measure, or wait | `play`, `measure`, `wait` |
| Synchronise buses | `sync` |
| Set signal properties | `set_frequency`, `set_phase`, `reset_phase`, `set_gain`, `set_offset` |
| Access platform configuration | `set_parameter`, `get_parameter` |
| Call a reusable sequence | `call` |

- Units: nanoseconds for duration, hertz for frequency, and radians for phase. Gain and offset are dimensionless.
- `measure` returns a handle and `get_parameter` returns a variable. The other operations return `None`.

---

## Timing and synchronisation

![h:350](img/timing.svg)

- Each bus has its own timeline.
- `sync(buses)` aligns the selected buses at the latest of their current times.
- `sync()` includes every bus. Pass an explicit list when only some buses need to wait.

---

## Measurement outputs

| Field | Output |
|---|---|
| `MeasurementField.IQ` | Integrated I and Q values |
| `MeasurementField.STATE` | Classified state |
| `MeasurementField.RAW` | Raw acquisition trace |

- `measure` plays the readout waveform and acquires the response. Its `weights` argument supplies the integration weights.
- Keep the returned handle to retrieve the measurement with `result.get(handle, field=...)`.
- Requesting a field that the measurement did not include raises `KeyError`.

---

## Bus schemas and validation

```python
program.measure(q[0].drive, "readout", "weights")
# ValidationError: this drive bus does not support acquisition.
```

- `BusSchema` provides structured references such as `q[0].drive`.
- A `BusRef` carries the channel type and acquisition capability.
- QProgram checks waveform compatibility and acquisition support when you add operations.
- Plain string names do not provide this metadata.

---

## Waveforms and aliases

- Waveforms describe pulse envelopes independently of programs and hardware.
- `envelope()` returns samples and `get_duration()` returns the duration. IQ waveforms expose I and Q components.
- Matching waveform types and parameters compare equal. `plot()` displays their shapes.
- String aliases let you supply waveform definitions later with `with_waveforms`.

---

## Saving and loading programs

```diff
- play "q0/drive" IQDrag(amplitude=0.62, duration=40, sigma=10, beta=0.15)
+ play "q0/drive" IQDrag(amplitude=0.31, duration=40, sigma=10, beta=0.15)
```

- `qp.save` and `qp.load` write and read `.qp` files.
- `qp.dumps` and `qp.loads` work with text directly.
- Compare `loaded.body == original.body` to check the restored structure.
- The text format makes changes to operations and waveform parameters easy to review.

---

## Reference simulation

- `qp.simulate(program, model=...)` executes the program on the Python reference platform.
- It follows the program's blocks and repetitions and collects measurement records.
- The measurement model supplies the values returned at each shot.
- It does not simulate pulse dynamics or hardware timing. Use it to explore program structure and result analysis.

---

## Exercise 1.1: a complete sequence

- Set a flux offset, play a drive pulse, and synchronise the drive and readout buses.
- Measure both I/Q and the classified state.
- Save and load the program, then compare its body with the original.
- Attempt a measurement on the flux bus and inspect the schema validation error.

---

<!-- _class: divider -->

<p class="kicker">Part 2 · notebooks/02_basics.ipynb</p>

# Variables, sweeps, and results

### Parameter sweeps, averaging, and labelled measurement data

---

## Variables and expressions

- A variable represents a value that can change between iterations.
- A sweep assigns successive values to the variable.
- Arithmetic creates symbolic expressions that use the variable's current value when evaluated.
- Variables can parameterise operations or waveform constructors. Their labels and units provide plot metadata.

---

## Result dimensions

![h:470](img/anatomy.svg)

<p class="cap">Nested sweeps define result dimensions. Averaging combines shots without adding a dimension. Each measurement creates a record, and a waveform can use the current value of a swept variable.</p>

---

## Sweep sources

| Kind | Examples | Meaning |
|---|---|---|
| `linear` | `Range`, `Linspace` | Values follow `start + step * i` |
| `arbitrary` | `Values`, `Logspace`, `File` | The source supplies the individual values |

- Pass a source object or use a `from_*` builder method. Wrap a plain list in `qp.Values`.
- `Values` remains arbitrary even when its values are evenly spaced.
- Sources report their length and required capabilities. `Repeat`, `Rotate`, and `Concat` combine existing sources.

---

## Averaging over shots

- `average(shots)` repeats a block and averages its measurements.
- Averaging adds no shot dimension to the result.
- I/Q values and raw traces become means. Classified states become estimates of the probability of state 1.
- For independent noise, the standard deviation of the mean decreases approximately as $1/\sqrt{N}$.

---

## Mock measurement models

- The reference platform requests a sample for each measurement, shot, and sweep point.
- `env` contains currently assigned variables and platform parameters.
- Model constants describe the assumed device response. Define them beside the model that uses them.
- Use `MockMeasurementModel` for configurable responses or implement `sample(bus, env)` for a custom model.

---

## Resonator spectroscopy

```python
F_READOUT = 7.20e9  # Hz: assumed true resonance frequency
KAPPA = 1.5e6       # Hz: model linewidth parameter
```

- Sweep `ro_freq` from 7.19 to 7.21 GHz in 200 kHz steps.
- Combine I and Q to calculate the response magnitude, then locate its sampled minimum.
- Compare the estimated frequency with `F_READOUT`.
- The grid and measurement noise affect the estimate. A finer scan or a fit can improve it.

---

## Nested amplitude and frequency sweeps

- The amplitude variable enters the waveform constructor. The frequency variable enters `set_frequency`.
- Two nested sweeps measure every combination and produce a result with dimensions `(drive_amp, drive_freq)`.
- The mock model uses `F_01` for the resonance frequency and `RABI_RATE` to relate amplitude to response width.
- In this illustrative model, the peak population is 0.5 and the response broadens with amplitude. `result.plot` displays the map as a heatmap.

---

## Nested and paired sweeps

```python
with program.sweep(amp, ...):       # Every combination
    with program.sweep(freq, ...):
        ...

with program.sweep(amp, ...) | program.sweep(freq, ...):
    ...                            # Corresponding pairs
```

- Nested sweeps produce separate dimensions. Paired sweeps share one dimension with multiple coordinates.
- Paired sources must have equal lengths.
- The notebook's full map has 861 points. Pairing each amplitude with its selected peak frequency uses 21 points.

---

## Exercise 2.1: estimating a pi-pulse amplitude

$$P_1(a) = \sin^2\left(\frac{\pi a}{2A_\pi}\right)$$

- Sweep the drive amplitude at a fixed frequency and average classified states.
- `A_PI = 0.62` sets the first maximum of the mock response.
- On the rising branch, find the amplitude whose population is closest to 0.5. Double it to estimate the pi-pulse amplitude.
- Compare with `A_PI` and mark the estimate on the plot. Noise and sweep spacing affect the result.

---

<!-- _class: divider -->

<p class="kicker">Session 2 · Part 3 · notebooks/03_advanced.ipynb</p>

# Reusable sequences and platform support

### Fragments, feedback, language extensions, and execution plans

---

## Fragments

```text
fragment x_pulse(drive, amp):
  play drive IQDrag(amplitude=amp, duration=40, sigma=10, beta=0.1)

body:
  x_pulse("q0/drive", 0.5)
  x_pulse("q0/drive", 0.25)
```

- `@qp.fragment` defines a reusable sequence with parameters.
- The Python function runs once to build the definition. Each call supplies its own arguments.
- `expand()` substitutes calls with their operations. Expand before binding aliases inside fragments.
- Measurements declared in the calling program keep their handles directly accessible.

---

## Conditionals and active reset

```python
with program.if_(measurement.state == 1):
    program.play("q0/drive", "pi")
```

- Request `MeasurementField.STATE` before using a measurement in a condition.
- Conditions support one equality or inequality comparison with an integer or another classified state.
- Active reset applies a correction when the first measurement reports state 1.
- In the mock example, 30% initial excitation and 90% reset success give an expected population of 3% after reset.

---

## Extending QProgram

| Extension | Implementation | Registration |
|---|---|---|
| Waveform | `envelope()` and `get_duration()` | Waveform class and capability token |
| Sweep source | `KIND`, `TOKEN`, `length()`, `values()` | Sweep-source class |
| Vendor operation | `Operation` and `VendorNamespace` subclasses | Namespace, syntax, tokens, and version |

- Resolve `qp.Expression` parameters when the implementation needs numeric values.
- Registration connects custom types to serialisation and capability checks.
- Capability tokens let a platform declare support for each extension.

---

## Vendor requirements in a program file

```text
#!QProgram 0.2

require qblox 0.2

body:
  qblox.set_markers "q0/drive" "0001"
```

- A `require` line identifies a vendor extension and its format version.
- The loader discovers installed extensions through `qprogram.vendors` entry points.
- Missing extensions and unsupported versions produce load errors.
- Custom waveform and source classes also need their Python implementations and registration.

---

## Vendor-specific offset operations

| Capability | Qblox profile | QDAC profile |
|---|---|---|
| `op.set_offset` | Supported | Not supported |
| `vendor.qdac.set_offset` | Not supported | Supported |

- The Qblox profile supports core offset changes within a sequence.
- The QDAC profile provides a separate operation for updates through the host.
- Distinct tokens describe the different execution requirements.

---

## The platform interface

| Member | Purpose |
|---|---|
| `get_bus_schema()` | Return the bus schema |
| `get_buses()` | List available buses |
| `get_parameters(bus)` | List parameters for a bus |
| `get_global_parameters()` | List parameters without a bus |
| `capabilities` | Describe supported features |
| `execute(program)` | Run the program and return results |

- The base class provides `validate`, `plan`, and `explain`.
- Hardware implementations handle compilation, instrument communication, and result construction.

---

## Two platform configurations

| Feature | Configuration A | Configuration B |
|---|---|---|
| Drive and readout | Real-time execution | Real-time execution |
| Flux updates | Real-time execution | Host execution |
| Example bus name | `q0/drive` | `drive_q0` |

- Bus naming and execution support are separate concerns.
- `rebind` resolves structural bus references using another schema's naming pattern.
- The capability descriptor determines whether the program can run and in which domains.

---

## Averaging around a bias sweep

```text
average 200:
  for bias in Linspace(start=-0.05, stop=0.15, num=41):
    set_offset q[0].flux bias
    set_frequency q[0].drive 4850000000.0
    play q[0].drive "pi"
    sync q[0].drive q[0].readout
    measure q[0].readout "probe" "weights" name="m0" fields=["state"]
```

- The outer averaging block makes 200 passes over the 41-point sweep.
- Each point updates the bias and performs the measurement sequence.
- The platform descriptor determines where these operations execute.

---

## Host updates and measurement order

| Operation count | Original loop order | Averaging inside the sweep |
|---|---|---|
| Flux offset updates | 8,200 | 41 |
| Measurement shots | 8,200 | 8,200 |

- The original program updates the offset at every point in every pass.
- The transformed program sets the offset once per bias, then collects all 200 shots.
- Reducing host updates can reduce overhead. The actual runtime depends on the platform.

---

## Execution domains

| Domain | Execution |
|---|---|
| `rt` | A real-time component, such as an instrument sequencer |
| `host` | The control computer |

- Each `BusCapabilities` object contains an `rt` and a `host` component. Either can be `None`.
- Profiles can differ by bus kind, such as `("q", "flux")` and `("q", "drive")`.
- Platform-level profiles cover features such as blocks and expressions.

---

## Tokens, limits, and predicates

| Mechanism | Purpose | Example |
|---|---|---|
| Token | Declare support for a feature | `op.play`, `waveform.iq_drag` |
| Limit | Constrain a numeric property | `max_loop_nesting` |
| Predicate | Check a rule using program context | Restrict a swept flux offset |

- Nodes report requirements through `required_capabilities()`.
- Profiles supply tokens, limits, and predicates without requiring an instrument connection.
- The core validator checks four limit keys. Additional published limits need their own enforcement.

---

## Reading an execution plan

| Label | Meaning |
|---|---|
| `[rt]` | Real-time execution is supported |
| `[host]` | Host execution is supported |
| `[rt\|host]` | Both domains are supported |
| `[--]` | No supported execution domain |

- `qp.validate` returns diagnostics and a plan. `qp.explain` displays them beside the program.
- An unsupported operation can remove the enclosing loop's available domains.
- Inspect the child diagnostics as well as the block labels to understand an error.

---

## Host execution in the plan

![h:460](img/plan.svg)

<p class="cap">The flux operation supports only host execution. That restriction moves its enclosing bias sweep and averaging block to the host, even though drive and readout operations support real-time execution.</p>

---

## Reordering averaging

- `qp.optimize(program, capabilities)` returns a new program for a supported transformation.
- It moves the bias sweep outside averaging and places the offset update before the shots at each point.
- This changes the measurement order from repeated full scans to all shots at one point.
- Consider device drift and operation side effects before applying it. The `reorderable-averaging` hint identifies when the transformation is available.

---

## Synchronisation and optimisation

- `sync()` includes every bus in the program.
- If the flux bus supports only host execution, including it can restrict the synchronisation to the host.
- A synchronisation in the middle of the sequence can prevent the averaging transformation.
- Use an explicit bus list to express which timelines must align, then inspect the plan.

---

## Custom validation rules

- The example uses `BIAS_LIMIT = 0.1` V as the maximum absolute flux offset.
- `ctx.binding_loop_of(variable)` finds the sweep whose values the predicate must check.
- A predicate can yield a `Diagnostic` to report a violation.
- A `DomainConstraint` restricts a block's execution domains while allowing a supported alternative, such as host execution.

---

## Diagnostics and command-line tools

```sh
python -m qprogram.lsp check flux_sweep.qp
python -m qprogram.lsp explain flux_sweep.qp
```

- Diagnostics provide a severity, code, message, and location in the program.
- `qp.validate` returns validation failures as data for notebooks, editors, or automated checks.
- A platform's `execute` implementation should reject error diagnostics before execution.
- `check` returns JSON diagnostics and `explain` displays the execution plan. `lsp serve` provides editor integration.

---

## Exercise 3.1: a custom measurement field

- Register `measure.fields.counts` to make `"counts"` available to `measure`.
- Request both `"counts"` and `MeasurementField.STATE`.
- Validate against descriptors that support the field and omit it.
- The reference platform allocates the custom field but leaves it at zero. A supporting platform must supply the measured values.


---

## Where to go next

- **Docs**: [qilimanjaro-tech.github.io/qprogram](https://qilimanjaro-tech.github.io/qprogram) · **Source**: [github.com/qilimanjaro-tech/qprogram](https://github.com/qilimanjaro-tech/qprogram)
- The Reference section is normative, and `qp.lark` is the machine-readable grammar.
- Read `qprogram-qblox` or `qprogram-qdac` before writing your own extension.
- Write a rule your lab cares about as a predicate.
- Issues and pull requests are welcome.

---

## Other events at QCE 2026

- **Paper: QProgram**: *A Hardware-Agnostic DSL for Portable Pulse-Level Quantum Programming* (Q-SET 2026), Vyron Vasileiadis, Flavie Le Bars, David Arcos. Wed Sep 16, 10:00–11:30 AM EDT, Room 714B.
- **Poster: QiliSim**: *A C++ Quantum Simulator for Digital/Analog Workflows*, Luke Mortimer, Ameer Azzam, Vyron Vasileiadis, Natàlia Padilla. Board 76, Hall E. Mon Sep 14, 18:30–20:00 (reception); Tue Sep 15, 11:30–12:30; Wed Sep 16, 14:30–15:00.
- **Poster: QPySequence**: *Pythonic Sequence Programming for Qblox Hardware*, Flavie Le Bars, Vyron Vasileiadis, Joel Pérez Díaz. Board 86, Hall E. Mon Sep 14, 18:30–20:00 (reception); Tue Sep 15, 11:30–12:30; Wed Sep 16, 14:30–15:00.

---
<!-- _class: lead center -->
<!-- _footer: '' -->

<img class="logo" src="img/qilimanjaro-logo-white.png" alt="Qilimanjaro Quantum Tech" />

# Thank you

<p class="sub">Questions welcome.</p>
<p class="sub">The notebooks are yours to keep.</p>

<p class="meta">vyron@qilimanjaro.tech · flavie.lebars@qilimanjaro.tech · QCE 2026</p>
