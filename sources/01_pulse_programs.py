# %% [markdown]
r"""
# 01 · The program is data

A gate is a promise. A pulse is what the instrument actually does.

This part is about the second one. You will write the first two programs of a real bring-up. A
readout tone with an acquisition, then a pi pulse followed by a readout. After that you take them
apart. The builder does not hand you a string to give to a box. It hands you a tree you can
inspect, transform, and save.

Nothing here runs. Not on hardware, not even on the simulator. Part 1 is build and inspect. Part 2
presses go.
"""

# %%
# Run me first. A no-op when qprogram is already installed, an install when it is not
# (a fresh Google Colab runtime, for example).
try:
    import qprogram  # noqa: F401
except ImportError:
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "qprogram[viz]==0.1.0", "scipy"],
        check=True,
    )
    import qprogram  # noqa: F401

from importlib.metadata import version

print("qprogram", version("qprogram"))

# %%
import difflib
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import qprogram as qp
from qprogram import MeasurementField as MF
from qprogram.buses import BusSchema
from qprogram.operations import Play, Wait
from qprogram.waveforms import Arbitrary, FlatTop, Gaussian, IQDrag, IQPair, Ramp, Square, SuddenNetZero

# What a core measurement can ask for, in the canonical order QProgram sorts fields into.
# A vendor extension can register more names; these three are what ships in the box.
print("measurement fields:", [field.value for field in MF])

# %% [markdown]
r"""
## 1.1 From a circuit to a voltage

A circuit says `X(q0)`. To emit it, an instrument has to be told which output port, at what carrier
frequency, with what envelope shape, for how many nanoseconds, at what amplitude, and what else has
to stay quiet while it happens. A gate carries none of that, because supplying those numbers is the
calibration engineer's job and not the algorithm's. QProgram's answer is to keep the program as
data and let the platform decide how to run it. Part 5 is about that decision, Part 1 is about the
data, and the slides carry the chip and the rack that the data describes.

Three facts about the wiring are enough to read every cell below. The first is that a qubit is
reached by at most three coaxial lines and each one has a single job. A drive line carries a
microwave tone near $f_{01}$ and rotates the state. A readout line carries a tone near $f_r$, the
frequency of a resonator sitting next to the qubit, and interrogates it. A flux line holds a slow,
near-DC level that moves $f_{01}$, on tunable qubits only. Every operation in this part puts a
voltage on one of those lines or records what comes back on one.

The second concerns the return path. A circuit's `measure(q0)` returns a bit; the hardware returns
one complex number per shot, the amplitude and phase of a tone that went past the resonator and
picked up a state-dependent shift on the way. Turning that number into a 0 or a 1 means putting a
threshold between two clouds in the IQ plane, and the threshold is a calibration of its own that
Part 4 measures. Until then `MF.IQ` is the raw point and `MF.STATE` is the platform's
classification of it.

The third is that every number in those two paragraphs was measured, on this chip, by somebody
running a scan that has no gate-level spelling, and that all of them move. The chip here is
simulated so that you can run the scans on a laptop, and these are its numbers.
"""

# %%
# The simulated chip this tutorial calibrates. Every part uses the same numbers, and every fit you
# do later has to recover them. Part 1 needs the frequencies and the two pi amplitudes.
DEVICE = {
    "q0_f01": 4.85e9,  # Hz, qubit 0 transition frequency at the flux sweet spot
    "q0_fr": 7.20e9,  # Hz, readout resonator
    "q0_kappa": 1.5e6,  # Hz, resonator linewidth (FWHM)
    "q0_chi": -1.8e6,  # Hz, dispersive shift
    "q0_a_pi": 0.62,  # drive amplitude of a pi pulse (DAC units)
    "q0_T1": 18_000,  # ns
    "q0_T2star": 9_000,  # ns
    "q0_T2echo": 16_000,  # ns
    "q0_linewidth": 2.0e6,  # Hz, spectroscopy FWHM at low power
    "q1_f01": 5.12e9,
    "q1_a_pi": 0.55,
}

print("qubit 0 drive:  ", DEVICE["q0_f01"] / 1e9, "GHz")
print("qubit 0 readout:", DEVICE["q0_fr"] / 1e9, "GHz")
print("pi amplitude:   ", DEVICE["q0_a_pi"], "(DAC units)")

# %% [markdown]
r"""
### Reading the datasheet

Those eleven numbers are the whole chip, and they are not independent. Spending five minutes on how
they hang together is worth it, because every experiment in this tutorial is an attempt to recover
one of them, and knowing what constrains what is how you tell a bad fit from a surprising result.

**The two frequencies and the gap between them.** The qubit sits at 4.85 GHz and its readout
resonator at 7.20 GHz, so the detuning is $\Delta = f_{01} - f_r = -2.35$ GHz. That gap is the
entire design. Put the resonator too close and it eats the qubit's lifetime through the Purcell
channel; put it too far and it stops learning anything about the qubit's state. Between those, at a
detuning of a couple of gigahertz, the two systems can no longer exchange energy but they can still
shift each other, and that residual shift is the whole of dispersive readout.

**The dispersive shift.** $\chi = -1.8$ MHz is how far the resonator moves when the qubit goes from
$|0\rangle$ to $|1\rangle$, halved. For a transmon,

$$\chi = \frac{g^2}{\Delta}\cdot\frac{\alpha}{\Delta + \alpha}$$

with $g$ the qubit-resonator coupling and $\alpha \approx -300$ MHz the anharmonicity. Put the
numbers in and this chip is claiming $g \approx 190$ MHz, a coupling at the top of what anybody
builds. Nothing breaks, because the simulated device was specified by the numbers you can measure
rather than derived from a Hamiltonian, but the arithmetic is worth doing on a real datasheet.
Parameters that do not close usually mean one of them is wrong.

**Why $\chi$ and $\kappa$ appear together.** The resonator is 1.5 MHz wide and the two qubit states
pull it apart by $2\chi = 3.6$ MHz, so the ratio $2\chi/\kappa = 2.4$. That ratio is the readout.
Too small and the two Lorentzians overlap and no amount of averaging separates them; too large and
the tone you park between them barely enters the cavity at all. The optimum for information per
photon sits near $2\chi \approx \kappa$, so this chip is a little over-separated, trading signal for
cleanliness. The same 1.5 MHz also fixes the cavity's fill time at $1/\kappa \approx 106$ ns, and
that is why the readout pulse below is 2000 ns and not 200.

**The three coherence times.** They obey

$$\frac{1}{T_2} = \frac{1}{2T_1} + \frac{1}{T_\varphi}$$

which is the only hard constraint among them. Relaxation contributes half its rate to dephasing and
pure dephasing $T_\varphi$ adds the rest. With $T_1 = 18$ us the relaxation floor puts $T_2$ at most
36 us. The measured $T_2^* = 9$ us therefore implies $T_\varphi^* = 12$ us of pure dephasing, and
the echoed $T_2 = 16$ us implies $T_\varphi = 29$ us. Refocusing removed about 60 percent of the
dephasing rate, which tells you the noise causing it is slow compared to the sequence. Part 4
measures all three and checks the inequality out loud.

**The spectroscopy linewidth is not a coherence linewidth.** $T_2^* = 9$ us corresponds to an
intrinsic line $1/\pi T_2^* = 35$ kHz wide. The 2 MHz in the dict is nearly sixty times that, and
the difference is not a mistake. Two-tone spectroscopy needs a saturating drive to produce any
population at all, and a saturating drive broadens the line it is measuring,

$$\Delta f = \frac{1}{\pi T_2}\sqrt{1 + \Omega^2 T_1 T_2}$$

so 2 MHz corresponds to a Rabi rate of roughly 700 kHz. Part 3 drives its survey scans harder still
and quotes 20 MHz, on purpose, so that a coarse frequency grid cannot step over the peak. Whenever a
linewidth in this tutorial looks too wide, it is because somebody chose to make it wide.
"""

# %% [markdown]
r"""
## 1.2 Buses and schemas

Those numbers reach the chip along wires, and a wire is the thing QProgram makes you name. A bus is
one signal path taken whole, from a port on an instrument, through the room-temperature attenuator,
into the fridge, down through the cold attenuators and filters at each temperature stage, and out at
one line on the chip. QProgram names that chain once and addresses everything through the name.

The interesting question is why the *path* is the unit of addressing rather than the qubit, which is
what a circuit person would reach for. Two facts settle it.

**One qubit owns several lines that have nothing in common.** `q[0].drive` is a pair of DACs feeding
an IQ mixer at 4.85 GHz. `q[0].flux` is a single filtered wire holding a DC level. Different
bandwidths, different failure modes, different waveform types, and on the rack in Part 5 they are
different instruments in different chassis. Calling them both "qubit 0" would hide the only
distinction that matters.

**One line often serves several qubits.** Readout resonators are deliberately spread across a couple
of gigahertz so that one feedline and one ADC can carry all of them at once, each on its own
frequency. Eight qubits, eight resonators, one physical cable. `q[0].readout` and `q[1].readout` are
two names for two frequencies on one wire.

So `play` names a bus, never a qubit, and `q[0].drive` is a name for a signal path that happens to
end near qubit 0. The deck draws the mapping from instrument ports through bus names to the chip in
`slides/img/buses.svg`.

Almost every operation names the bus it acts on (a bare `sync()` is the exception, later in this
part), and the simplest spelling is a string.
"""

# %%
raw = qp.QProgram(label="readout_raw_strings")
raw.set_frequency("readout_q0", DEVICE["q0_fr"])
m_raw = raw.measure("readout_q0", "readout", "weights")

print(qp.dumps(raw))
print("buses:  ", sorted(raw.buses))
print("handle: ", m_raw.name)  # a global counter: a raw string has no bus name to derive one from

# %% [markdown]
r"""
That is a valid program and it will run. You gave up two things by typing strings. No
tab-completion, and no checking. Type `"raedout_q0"` by accident and you find out on hardware, at
2 a.m., after the fridge is cold.

`BusSchema` fixes both without changing what lands in the AST. A schema declares which kinds of bus
each element of the chip has. It does not declare how many qubits exist, so any index works.

A schema hands back a `BusRef`, a real `str` subclass that also carries metadata. Everywhere
QProgram wants a bus name, a `BusRef` works, and the extra fields are what make checking possible.
"""

# %%
schema = BusSchema.transmon()  # each qubit: drive (IQ), readout (IQ, with an ADC)
q = schema.q

readout_bus = q[0].readout
print("schema:      ", schema)
print("the ref:     ", repr(readout_bus), "| a str?", isinstance(readout_bus, str))
print("element/idx: ", readout_bus.element, readout_bus.idx)
print("kind:        ", readout_bus.kind)
print("channel:     ", readout_bus.channel, "| acquires:", readout_bus.acquires)
print("any index:   ", q[7].drive, q[7].drive.channel)

# %% [markdown]
r"""
### Two mistakes the schema catches for free

The two extra fields describe the wiring. `channel` records how many DACs feed the line, `acquires`
records whether an ADC listens to it, and both of those are facts about copper.

A drive line ends at an IQ mixer, which needs two synchronized DACs to place a tone at an arbitrary
sideband of the local oscillator without also placing a mirror image of it somewhere you did not
want one. So an IQ bus needs an IQ waveform, and handing it a single-channel `Square` means half the
data is missing. A flux line is a single DC-coupled wire and takes one channel, no mixer and no
carrier at all. And an ADC exists on the readout line only, because that is the only line anything
comes back on.

QProgram turns both facts into build-time errors:

- an IQ bus needs an IQ waveform, and a single-channel bus needs a real-valued one.
- `measure` needs a bus with an ADC. Asking a drive line for data is not a mistake hardware will
  tell you about politely.

Both raise `qp.ValidationError` at build time, on the line that made the mistake. Read the two
messages below. They name the bus, the reason, and what to do instead.
"""

# %%
scratch = qp.QProgram(label="deliberate_mistakes", schema=schema)

try:
    scratch.play(q[0].drive, Square(amplitude=0.5, duration=40))
except qp.ValidationError as exc:
    print("channel mismatch ->", exc)

try:
    scratch.measure(q[0].drive, "readout", "weights")
except qp.ValidationError as exc:
    print("\nno ADC          ->", exc)

# %% [markdown]
r"""
Raw strings skip every one of these checks, on purpose. A `.qp` file can be mostly schema-backed
with one odd bus slotted in by name, and QProgram will not argue. You lose the checks for that bus
only.
"""

# %% [markdown]
r"""
## 1.3 Operations: what the electronics offer

Naming a line is half of the vocabulary. The other half is the list of things you can tell the
electronics to do on that line, and the list is short. The shortness is the point.

| What the hardware does | QProgram | Where it lands |
|---|---|---|
| write the NCO frequency on an output | `set_frequency` | a register |
| write or zero the NCO phase | `set_phase`, `reset_phase` | a register, and how a virtual Z is spelled |
| scale the whole output path | `set_gain` | a register |
| hold a DC level | `set_offset` | a register, or a slow-control write |
| emit an envelope out of waveform memory | `play` | one instruction plus an address |
| idle a channel for N clock cycles | `wait` | a counter |
| bring channels back to a common time reference | `sync` | a barrier the compiler resolves |
| emit, integrate the return, optionally threshold it | `measure` | the acquisition path |
| repeat a block N times | `average`, `sweep` | a loop over a register |
| take a branch on a classified bit | `if_` / `else_` | a comparison and a jump |
| change a setting the sequencer does not own | `set_parameter` | the control PC, over the network |

QProgram did not invent that vocabulary. It is roughly the intersection of what commercial
sequencers offer, given portable names. Which is why the operation list is short, why adding to it
takes a vendor namespace instead of a patch to the core (Part 6), and why a program written in it
has any chance of running on a rack you have never seen (Part 5).

Four hardware facts explain most of the constraints you will meet later:

- **Instructions land on a clock grid**, 4 ns on a typical box. Ask for a 3 ns wait and you get 4.
- **Waveform memory is finite**, tens of thousands of samples. You play from a small library of
  envelopes rather than streaming samples, and that is why a program refers to pulses and a separate
  library holds them (Part 3).
- **Loop counters are integer registers.** A sweep the hardware can generate on its own is one where
  the next value is the previous plus a constant. Everything else has to be uploaded as a table, and
  Part 2 is where that distinction starts costing real time.
- **A branch has to resolve in tens of nanoseconds**, while the qubit is still coherent. That budget
  is why the conditional in Part 4 compares one classified bit against a constant and nothing wider.

### The first readout pulse

The first measurement on a new chip is the readout resonator, and the smallest program that does
anything useful is one readout tone plus one acquisition.

Three arguments to `measure`: the bus, the pulse to play, and the integration weights. `measure`
outputs the pulse itself, so there is no separate `play` on the readout line.

Both of those arguments deserve a sentence about what the hardware does with them.

**The pulse.** Two microseconds of flat tone, at a fifth of full scale. Flat because the resonator
takes about 106 ns to fill and you want it in steady state for as much of the window as possible,
and long because the signal you are integrating is a handful of microwave photons through an
amplifier chain whose noise you cannot avoid. Signal-to-noise grows as the square root of the
integration time, so a 2 us window is four times better than a 500 ns one. The upper limit comes
from the other side. The qubit relaxes during the measurement, and integrating for a time comparable
to $T_1$ means the state you report is not the state you had. Two microseconds against an 18 us
$T_1$ is about a ninth, and a ninth is roughly where labs land.

**The weights.** The ADC hands the platform a stream of samples, and the weights are what that
stream is multiplied by before it is summed into the single IQ point you get back. A flat window of
ones is the honest starting default, and this tutorial uses it throughout. It is not the best you
can do. The optimal weights are the difference between the average trace you get from $|0\rangle$ and
the one you get from $|1\rangle$, which downweights the beginning of the record while the resonator
is still filling and the two states have not separated yet. Labs measure that pair of traces once
and keep the difference as a calibrated array. It travels through the same seam as a calibrated pi
pulse and lives in the same library.

`fields=` says which data you want back; `iq` is the default, and `state` asks the platform to
classify the point into 0 or 1.

Both pulses below are `IQPair`s because a readout line is two paths, and spelling both channels out
is what makes that visible. When the quadrature is silent,
`IQZero(Square(amplitude=0.2, duration=2000))` names the same pulse in one constructor, and it is
the one to reach for when a calibrated single-channel envelope has to go down an IQ line.
"""

# %%
readout_pulse = IQPair(I=Square(amplitude=0.2, duration=2000), Q=Square(amplitude=0.0, duration=2000))
weights = IQPair(I=Square(amplitude=1.0, duration=2000), Q=Square(amplitude=1.0, duration=2000))

readout_program = qp.QProgram(
    label="first_readout",
    description="One 2 us readout tone on qubit 0, integrated into one IQ point.",
    schema=schema,
)
readout_program.set_frequency(q[0].readout, DEVICE["q0_fr"])
m0 = readout_program.measure(q[0].readout, readout_pulse, weights, fields=(MF.IQ, MF.STATE))

print(qp.dumps(readout_program))

# %% [markdown]
r"""
### The measurement handle

`measure` returns a `MeasurementHandle`. It is how you ask for this measurement's data after the run
(`result.get(m0)` in Part 2) and how you refer to its outcome inside a conditional (Part 4).

The handle is a name, nothing more. Names are auto-allocated per bus (`q0/readout/m0`,
`q0/readout/m1`, ...) unless you pass `name=`, and they are written into the `.qp` file verbatim.
Handles compare by name, so a handle you reconstruct after loading a file six months later still
refers to the same measurement.
"""

# %%
measure_node = readout_program.body.elements[-1]

print("handle name:  ", m0.name)
print("requested:    ", measure_node.fields)  # canonical order, not the order you asked in
print("rebuilt equal:", m0 == qp.MeasurementHandle("q0/readout/m0"))

# %% [markdown]
r"""
### The drive sequence

Now the other half of a bring-up: put energy into the qubit, then read it. This one uses most of the
verbs you will need all day.

- `set_frequency(bus, hz)` and `set_gain(bus, g)` touch hardware registers. Gain scales the whole
  output path; the `amplitude` inside a waveform shapes the envelope. Two different knobs.
- `reset_phase(bus)` zeroes the oscillator phase on a bus and `set_phase(bus, radians)` writes it to
  a value you choose. Both are register writes like the two above. Resetting the phase before a
  sequence makes every shot start from the same reference, so the phase the qubit accumulates is the
  phase you asked for rather than whatever the oscillator had been doing since the last shot.
  Setting it is how the second pulse of a sequence gets advanced by a chosen angle, which is one of
  the two ways a Ramsey fringe is produced and the whole of how a virtual Z gate is written.
- `play(bus, waveform)` outputs one envelope.
- `wait(bus, ns)` idles one bus.
- `sync(buses)` makes the listed buses agree on where "now" is. This is the operation that catches
  people arriving from circuits, because a circuit has one global clock and a pulse program does
  not. Every bus keeps its **own** cursor, advanced only by the pulses and waits written to that
  bus, so two buses that have played different amounts have drifted apart by exactly the difference:

  ```text
  without a sync
    q[0].drive     |play pi 40 ns|4|
    q[0].readout   |measure 2000 ns .....................................|
                   ^ both buses start from their own cursor, and both are still at 0

  with sync([q[0].drive, q[0].readout])
    q[0].drive     |play pi 40 ns|4|
    q[0].readout   .................|measure 2000 ns .....................................|
                                    ^ the barrier moved the readout cursor to 44 ns
  ```

  In the first one the acquisition is running while the qubit is still being flipped, so you measure
  the pulse rather than the state. The barrier fixes it by holding every named bus until the
  furthest-ahead one has finished. `sync()` with no argument covers every bus in the program, which
  is convenient here and expensive in Part 5, and `sync([])` raises rather than guess whether you
  meant nothing or everything. The deck draws both cases in `slides/img/timing.svg`.
- `with program.block():` groups statements and changes nothing about what they mean. There is no
  loop here yet. Part 2 replaces this grouping with a real sweep.

A mixer does not stop the instant its envelope reaches zero, and a readout tone that starts while
the drive is still ringing down measures the ringdown along with the qubit. Hence the 4 ns wait
between the drive and the readout. Four nanoseconds is one clock cycle on a typical sequencer, the
smallest gap you can ask for and enough on most racks.
"""

# %%
pi_pulse = IQDrag(amplitude=DEVICE["q0_a_pi"], duration=40, sigma=10, beta=0.15)

drive_program = qp.QProgram(
    label="drive_then_read",
    description="A calibrated pi pulse on qubit 0, then a readout.",
    schema=schema,
)
with drive_program.block():  # the preparation, as one group
    drive_program.set_frequency(q[0].drive, DEVICE["q0_f01"])
    drive_program.set_gain(q[0].drive, 1.0)
    drive_program.reset_phase(q[0].drive)  # every shot starts from the same phase reference
    drive_program.play(q[0].drive, pi_pulse)
    drive_program.wait(q[0].drive, 4)  # ns of dead time before the readout
drive_program.sync([q[0].drive, q[0].readout])
m_drive = drive_program.measure(q[0].readout, readout_pulse, weights, fields=(MF.IQ, MF.STATE))

print(qp.dumps(drive_program))

# %% [markdown]
r"""
## 1.4 Waveforms are data

Both programs above played an envelope without ever saying what an envelope is. A waveform is a
pure-data description of one. It knows nothing about hardware, and it can be built, compared, and
drawn with no program around it.

Three methods carry the whole contract. `envelope(resolution=1)` returns the samples as a numpy
array, `get_duration()` returns nanoseconds, and `plot()` draws the envelope and hands back the
matplotlib `Axes` it drew on. The plot method is the route whenever the goal is to look at a shape.
matplotlib is for the parts a figure of one envelope cannot decide for itself, and a row of six
panels is one of those, so the gallery below opens the row by hand and then gives each panel to a
waveform as `target=`. Part 2 passes the same argument to `result.plot`.

Each of these shapes exists because a specific thing goes wrong without it:

- **`Square`** is the readout tone, and it is square because you want the resonator in steady state
  and the integration window at constant amplitude.
- **`Gaussian`** is the drive envelope, and it is not square because a square edge is broadband. A
  transmon has a $|1\rangle \to |2\rangle$ transition sitting 200 to 300 MHz below the one you are
  aiming at, and a sharp edge puts power there. It is also the shape your AWG can actually produce.
  Ask a 1 GS/s converter for a step and you get its own ringing, not yours.
- **`FlatTop`** is a Gaussian rise, a flat hold, and a Gaussian fall. Reach for it when the length
  of the interaction is the parameter you want to sweep and the edges have to stay bounded. Flux
  pulses for two-qubit gates are the usual customer.
- **`Arbitrary`** takes samples you brought yourself. Two sources dominate, numerical optimal
  control and predistortion. A flux line through a fridge is a filter with several time constants in
  it, so the step you asked for arrives at the chip with a tail on it. Labs measure that response
  once and then send the inverse. It arrives as a sample array and nothing prettier.
- **`Ramp`** is a linear excursion, the shape a bias line takes when it moves between two DC values.
- **`SuddenNetZero`** is the two-qubit flux pulse whose positive and negative halves cancel. The
  cancellation is the point. Those same long time constants mean a pulse with net area leaves a
  residual bias behind it, so the second gate in a circuit sees a chip the first gate detuned. Zero
  net area, no accumulation. The `b` parameter is detuned slightly from 1 to null whatever the line
  adds on top.
"""

# %%
gallery = [
    Square(amplitude=0.2, duration=2000),  # the readout tone
    Gaussian(amplitude=0.5, duration=40, sigma=8),  # a short drive envelope
    FlatTop(amplitude=0.5, duration=200, smooth_duration=20),  # rise, hold, fall
    Arbitrary(0.4 * np.hanning(120)),  # samples you brought yourself, from optimal control or a fit
    Ramp(from_amplitude=0.0, to_amplitude=0.4, duration=200),  # a flux excursion
    SuddenNetZero(amplitude=0.4, duration=100, b=0.4, t_phi=20),  # a two-qubit gate pulse
]

fig, axes = plt.subplots(1, len(gallery), figsize=(17, 2.4))
for ax, waveform in zip(axes, gallery, strict=True):
    waveform.plot(target=ax)  # the waveform draws itself onto the panel we opened for it
    # plot() titles the panel with the class name; add the duration to it.
    ax.set_title(f"{type(waveform).__name__}\n{waveform.get_duration()} ns", loc="left", fontsize=9)
fig.tight_layout()
plt.show()

# %% [markdown]
r"""
The last two are flux shapes, not drive shapes, and nothing in the waveform says so. A `Ramp` is
an envelope and only that. The line you send it down decides what it means, and a flux line is
where these two belong. `BusSchema.transmon()` has no flux bus at all. Part 3 reaches for
`BusSchema.flux_tunable_transmon()` when it starts tuning the qubit with flux.

### IQ waveforms, and what DRAG is actually for

A drive line is a pair of paths, I and Q, fed through an IQ mixer. An `IQWaveform` carries both, and
`get_I()` / `get_Q()` hand back the two halves as ordinary single-channel waveforms.

`IQDrag` is the standard drive shape: a Gaussian on I, plus its scaled derivative on Q. The
one-clause version of why is that the derivative term suppresses leakage to the second excited
state. The clause is true and it explains nothing, so here is the mechanism.

A transmon is an anharmonic oscillator, and the emphasis belongs on *oscillator*. Its levels are not
a two-state system that happens to have neighbours; they are a ladder whose rungs are almost evenly
spaced. The $|1\rangle \to |2\rangle$ transition sits only $|\alpha| \approx 300$ MHz below
$|0\rangle \to |1\rangle$, and its matrix element is $\sqrt{2}$ larger. Drive the lower transition
resonantly at Rabi rate $\Omega$ and the upper one is driven too, off resonance by $\alpha$, which
populates $|2\rangle$ during the pulse at order $(\Omega/\alpha)^2$. Most of that population comes
back at the end. Not all of it, and what stays behind is leakage out of the computational subspace,
which no amount of later correction recovers.

The scale is worth carrying around. A 40 ns pulse with `sigma=10` has a Gaussian area of roughly
$\sigma\sqrt{2\pi} = 25$ ns, so a pi rotation needs a peak Rabi rate near $\pi/25\,\mathrm{ns}$, or
20 MHz. Against a 300 MHz anharmonicity that puts $(\Omega/\alpha)^2$ at about $4\times10^{-3}$.
Shorten the same pulse to 10 ns and the peak rate goes to 80 MHz and the ratio to 7 percent, which
is the difference between a gate you tune and a gate that does not work. Fast gates are why DRAG
exists.

The correction itself is one term. Adding a quadrature component proportional to the derivative of
the envelope, $Q(t) = \beta\,\dot{I}(t)$, cancels the leading-order transfer to $|2\rangle$ and the
phase error it leaves on $|1\rangle$. The first-order value of $\beta$ is $1/|\alpha|$ expressed in
the derivative's own units, around half a nanosecond for a 300 MHz anharmonicity. In practice
nobody uses the first-order value. It gets calibrated per qubit by a dedicated experiment,
because the leading order is only the leading order.

Nothing in this tutorial measures `beta`, and the reference simulator has no third level to leak
into, so the 0.15 in the cells above is a placeholder with the right shape and no provenance. Treat
it the way you would treat any uncalibrated number in someone else's script.

An `IQWaveform` draws itself as two panels stacked on a shared time axis, and `plot()` returns them
as an `(I, Q)` pair, so the figure below is one call plus a title, a zero line, and a label written
onto the axes that came back. The two panels carry their own vertical scales, and the difference
between those scales is the physics. A derivative is antisymmetric and it picks up a factor of
$1/\sigma$, so with `beta=0.15` and `sigma=10` the Q peak is about a hundred times smaller than the
I peak. Forced onto one axis it would be a flat line at zero.
"""

# %%
ax_i, ax_q = pi_pulse.plot()  # an IQWaveform hands back the two panels it drew
ax_i.set_title(f"IQDrag, the pi pulse on qubit 0 ({pi_pulse.get_duration()} ns)", loc="left")
ax_q.axhline(0.0, color="grey", linewidth=0.6)
ax_q.annotate(
    f"the derivative of I, scaled by beta={pi_pulse.beta}",
    xy=(0.98, 0.95),
    xycoords="axes fraction",
    ha="right",
    va="top",
    fontsize=8,
)
plt.show()

i_samples = pi_pulse.get_I().envelope()  # the samples themselves, for the arithmetic
q_samples = pi_pulse.get_Q().envelope()
print("peak I:", round(float(i_samples.max()), 4), "| peak |Q|:", round(float(np.abs(q_samples).max()), 4))

# %% [markdown]
r"""
There is a shorter spelling still. Both waveform bases define `_repr_html_`, so a bare waveform on
the last line of a notebook cell renders its own envelope with no plotting call at all, in a light
and a dark version so the picture survives either notebook theme. `plot()` makes the axes the cell's
value instead, which a notebook prints as `<Axes: ...>` next to the figure, so bind it or end the
line with a semicolon.
"""

# %%
pi_pulse

# %% [markdown]
r"""
### Structural equality

Waveforms compare and hash by structure, not by identity. Two `Gaussian(0.5, 40, 8)` objects built
in different cells are the same waveform. Whole-program comparison after a file round-trip depends
on that, and so does the equality check in section 1.6.
"""

# %%
print("same shape:      ", Gaussian(0.5, 40, 8) == Gaussian(0.5, 40, 8))
print("one sigma apart: ", Gaussian(0.5, 40, 8) == Gaussian(0.5, 40, 9))
print("the pi pulse:    ", pi_pulse == IQDrag(DEVICE["q0_a_pi"], 40, 10, 0.15))
print("distinct in a set:", len({Gaussian(0.5, 40, 8), Gaussian(0.5, 40, 8), Gaussian(0.5, 40, 9)}))

# %% [markdown]
r"""
### String aliases: the calibration seam

Look again at the `.qp` text of `drive_program`. The amplitude 0.62 is welded into it. That number
came from a Rabi fit and it will change next Tuesday, which means the program text changes every
time the calibration changes. Every diff is noise.

There is a worse version of the same problem, and it is the one that actually costs people data. A
script with a literal amplitude in it is a script that claims a calibration. Run it six months later
against a chip that has been thermal-cycled twice and it will run perfectly and produce numbers that
mean nothing, because 0.62 stopped being a pi pulse in March and nothing in the file knows that.

`play` and `measure` also accept a **string alias** instead of a waveform. The program then says
*which* pulse it wants, and the numbers arrive later from `with_waveforms`. The sequence is the part
you keep under version control; the amplitudes are the part that drifts. A program with an unbound
alias in it cannot silently claim a stale calibration, because it does not carry one.

Part 3 fits a real pi pulse and binds it this way, and Part 5 replaces the plain dict below with a
`WaveformLibrary` that resolves a name differently per bus.
"""

# %%
aliased = qp.QProgram(label="drive_then_read", schema=schema)
aliased.play(q[0].drive, "pi")  # "whatever a pi pulse is today"
aliased.sync([q[0].drive, q[0].readout])
aliased.measure(q[0].readout, "readout", "weights", fields=(MF.IQ, MF.STATE))

print(qp.dumps(aliased).split("body:")[1])  # the body only: the header holds nothing new here

calibration = {"pi": pi_pulse, "readout": readout_pulse, "weights": weights}
bound = aliased.with_waveforms(calibration)  # a new program; `aliased` is untouched
resolved = next(line.strip() for line in qp.dumps(bound).splitlines() if line.strip().startswith("play"))
print("after binding:", resolved)

# %% [markdown]
r"""
## 1.5 The program is a tree

Binding a waveform produced a new program rather than mutating the old one, which is a hint about
what a program is underneath. Every builder call appended a node. `program.body` is the root
`Block`, and `body.elements` is a plain Python list of its immediate children, in the order you
wrote them.

`drive_program` has three top-level children, because the four preparation statements live inside
the `block()`.
"""

# %%
print("top-level elements:", len(drive_program.body.elements))
for index, node in enumerate(drive_program.body.elements):
    print(f"  [{index}] {type(node).__name__:<8} buses={sorted(node.buses())}")

# %% [markdown]
r"""
`walk()` is the same tree in pre-order: the root `body` block first, then the `block()` you opened,
then everything inside it, at any depth. One uniform API covers blocks and operations, so you never
write the recursion yourself.

Keeping a program as data means you can compute things about a sequence before anything runs. The
cell below reads how many nanoseconds this program books on the drive line, straight off the AST.
It is a toy version of a real question. Fridge time is the scarce resource in any lab, and the
duration of a sweep is the product of its point count, its shot count, and the length of one shot,
all three of which are sitting in the tree before you press go. A scan you can price is a scan you
can decide not to run.

That number came out of your own arithmetic rather than out of a run. The reference simulator has no
timing model at all, so nothing will report it back to you. What the AST gives you is the chance to
work it out before you spend fridge time.
"""

# %%
print("walk() order:")
for node in drive_program.body.walk():
    print("  ", type(node).__name__)

drive_ns = 0
for node in drive_program.body.walk():
    if isinstance(node, Play) and node.bus == q[0].drive:
        drive_ns += node.waveform.get_duration()
    elif isinstance(node, Wait) and node.bus == q[0].drive:
        drive_ns += node.duration
print("\ntime booked on q[0].drive:", drive_ns, "ns")

# %% [markdown]
r"""
Four more things to know about a built program. One of them is empty on purpose.
"""

# %%
print("buses:    ", sorted(drive_program.buses))
print("variables:", drive_program.variables, "<- nothing declared yet, that is Part 2")
print("waveforms:", len(drive_program.body.waveforms()), "distinct")
print("schema:   ", drive_program.schema)

# %% [markdown]
r"""
## 1.6 `.qp`, the text format

A tree of plain objects serializes. `qp.dumps` writes the `.qp` text format and `qp.loads` reads it
back; `qp.save` and `qp.load` are the same pair against a file.

The format is deliberately boring: one statement per line, indentation for nesting, quoting as the
type distinction (a quoted `"readout_q0"` is a plain string, a bare `q[0].readout` is a bus path).
Nothing is truncated, so a program holding an `Arbitrary` of 4000 samples writes 4000 samples.
Nothing is implied, so a file that loads has everything the program had.

Both of those choices cost something. Writing every sample means a predistorted flux pulse turns
into a large file, and there is no compression and no reference to an external array. The trade is
that a `.qp` file has no dependencies. It does not need the numpy version that wrote it, or a
sidecar, or a database. Six months from now it either parses or it does not, and there is no third
outcome where it parses into something subtly different.

The round-trip is exact, and structural equality is how you check it.
"""

# %%
out = Path("out")
out.mkdir(exist_ok=True)
path = out / "drive_then_read.qp"

qp.save(drive_program, path)
text = path.read_text()

reloaded = qp.load(path)
print("wrote:", path.resolve(), f"({len(text.splitlines())} lines)")
print("same structure:", reloaded.body == drive_program.body)
print("same text back:", qp.dumps(reloaded) == text)

assert reloaded.body == drive_program.body  # the guarantee, spelled out
assert qp.loads(qp.dumps(drive_program)).body == drive_program.body

# %% [markdown]
r"""
Three things follow from having that file, and a lab feels all three. A text diff of two calibration
runs a week apart shows exactly which numbers moved. A pulse sequence a colleague can read in a pull
request gets checked before it costs fridge time. And the file is the experiment. Six months from
now the `.qp` next to your data still loads, still carries the measurement names you indexed the
results by, and does not depend on the notebook that happened to build it.

The first of those is worth doing rather than describing. `out/drive_then_read.qp` is on disk, so
retune the pi pulse the way you would retune it in a lab, by opening the file and changing the
number from 0.62 to 0.31 (`str.replace` stands in for the editor). The unified diff shows the one
line that moved, and loading the edited text back gives a program whose body no longer compares
equal to the original.

Watch the last two loops in particular. Structural equality is not a yes-or-no answer about a file,
it is a yes-or-no answer about any node in the tree, so comparing `body.elements` pairwise and then
descending into the one child that changed localises a colleague's edit to a single operation
without reading the file at all.
"""

# %%
original_text = path.read_text()
edited_text = original_text.replace("amplitude=0.62", "amplitude=0.31")

diff = difflib.unified_diff(
    original_text.splitlines(keepends=True),
    edited_text.splitlines(keepends=True),
    "measured.qp",
    "retuned.qp",
)
print("".join(diff))

retuned = qp.loads(edited_text)
print("whole body equal?", retuned.body == drive_program.body)

for index, (before, after) in enumerate(zip(drive_program.body.elements, retuned.body.elements, strict=True)):
    print(f"  [{index}] {type(before).__name__:<8}", "same" if before == after else "CHANGED")

print("inside the changed block:")
inner = zip(drive_program.body.elements[0].elements, retuned.body.elements[0].elements, strict=True)
for index, (before, after) in enumerate(inner):
    print(f"  [0][{index}] {type(before).__name__:<13}", "same" if before == after else "CHANGED")

# %% [markdown]
r"""
### 🧩 Exercise 1.1: a two-qubit prepare-and-read

Build one program that excites qubit 0 and qubit 1 and reads both out, then make the schema catch a
mistake.

1. One `QProgram` with `label="prepare_and_read_2q"` and the same `schema`.
2. For each qubit, `set_frequency` its drive bus to `DEVICE["q<i>_f01"]`, then `play` an `IQDrag` at
   `DEVICE["q<i>_a_pi"]` with `duration=40, sigma=10, beta=0.15`.
3. `program.sync()` with no arguments, so both readouts start from the same point in time.
4. `measure` both readout buses, using the `"readout"` and `"weights"` aliases and
   `fields=(MF.IQ, MF.STATE)`. Collect the two handles and print their names.
5. Print `qp.dumps(program)`.
6. Then, inside `try` / `except qp.ValidationError`, measure `q[1].drive` and print the message.

Look at the two handle names in the output. They tell you how per-bus numbering works.
"""

# %% solution
two_qubit = qp.QProgram(label="prepare_and_read_2q", schema=schema)

for i in (0, 1):
    two_qubit.set_frequency(q[i].drive, DEVICE[f"q{i}_f01"])
    two_qubit.play(q[i].drive, IQDrag(amplitude=DEVICE[f"q{i}_a_pi"], duration=40, sigma=10, beta=0.15))
two_qubit.sync()  # every bus in the program, so the two readouts line up
handles = [two_qubit.measure(q[i].readout, "readout", "weights", fields=(MF.IQ, MF.STATE)) for i in (0, 1)]

print(qp.dumps(two_qubit))
print("handles:", [handle.name for handle in handles])  # per-bus counters, so both are m0

try:
    two_qubit.measure(q[1].drive, "readout", "weights")
except qp.ValidationError as exc:
    print("\ncaught:", exc)

# %% stub
# TODO: build the two-qubit prepare-and-read sequence.
# 1) two_qubit = qp.QProgram(label="prepare_and_read_2q", schema=schema)
# 2) for i in (0, 1): set_frequency(q[i].drive, DEVICE[f"q{i}_f01"]) then play an IQDrag at
#    DEVICE[f"q{i}_a_pi"] with duration=40, sigma=10, beta=0.15
# 3) two_qubit.sync()
# 4) measure both readout buses with the "readout" / "weights" aliases and
#    fields=(MF.IQ, MF.STATE); keep the handles and print their names
# 5) print(qp.dumps(two_qubit))
# 6) then measure q[1].drive inside try / except qp.ValidationError and print the message

# %% [markdown]
r"""
## Recap and what is next

- A **bus** is one signal path. Strings work; a `BusSchema` gives you `BusRef`s that are still
  strings but carry `channel` and `acquires`. Those two fields reject a single-channel waveform on
  an IQ line and a `measure` on a bus with no ADC, at the line that made the mistake.
- **Operations** are the verbs: `play`, `measure`, `wait`, `sync`, `set_frequency`, `set_gain`,
  `reset_phase`. You
  built a readout tone with an acquisition, and a pi pulse followed by a readout.
- **Waveforms are data.** `plot()` draws them, `envelope()` hands you the samples, structural
  equality compares them, and a string alias leaves the number to be filled in later. That alias is
  the seam between a stable sequence and a drifting calibration.
- **The program is a tree.** `body.elements`, `walk()`, `buses`, `variables`. You read a pulse-time
  budget off the AST before anything ran, the same move a compiler makes.
- **`.qp` is the artifact.** `loads(dumps(p)).body == p.body`, so the file is the experiment, and a
  diff of two files is a diff of two calibrations.
- And the chip itself has a shape worth remembering. A 2.35 GHz detuning between qubit and
  resonator, a 1.5 MHz cavity pulled 3.6 MHz apart by the qubit's state, 18 us of $T_1$ against 9 us
  of $T_2^*$, and a spectroscopy line whose width is set by how hard you drive it. Every scan from
  here on measures one of those.

Carry this forward: nothing you wrote in Part 1 said which loop runs on the sequencer and which runs
on the control computer, because there were no loops. Part 2 adds them, together with averaging and
the results that come back.
"""
