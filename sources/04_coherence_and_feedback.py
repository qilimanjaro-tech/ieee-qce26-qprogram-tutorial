# %% [markdown]
r"""
# 04 · Coherence and feedback

Part 3 fitted a pi pulse. Once you can put the qubit in $|1\rangle$ on demand, you can ask how long it stays there.

Three numbers off the datasheet, then single shots, then a shot that decides what the program does next:

- **T1**, energy relaxation, from inversion recovery.
- **T2\***, dephasing, from a Ramsey fringe on a detuned drive.
- **T2**, dephasing after refocusing, from a Hahn echo.
- **Single-shot readout**, two blobs in the IQ plane and a threshold between them.
- **Active reset**, a pi pulse fired only if the qubit came up hot.

Three QProgram features arrive with them: **fragments**, the three **measurement fields**, and **conditionals** driven by a measured state.
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

# %% [markdown]
r"""
## 4.0 The device

Same simulated chip as the other parts. `DEVICE` holds the truth the fits have to recover: `q0_T1`, `q0_T2star`, and `q0_T2echo`. The models read the whole dict, because they stand in for the fridge.

The programs read two entries a real experiment would already have: `q0_f01` from Part 3's two-tone scan, and `q0_a_pi` from its Rabi fit. Taking them from the device keeps this notebook runnable on its own. `DETUNING` is a deliberate mistake, putting the drive 400 kHz above the qubit so the Ramsey fringe has something to show.
"""

# %%
import math
from dataclasses import replace

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

import qprogram as qp
from qprogram import MeasurementField as MF
from qprogram import fragment
from qprogram.buses import BusSchema
from qprogram.plotting import LIGHT, Quantity, Style
from qprogram.waveforms import IQDrag, IQPair, Square

DEVICE = {
    "q0_f01": 4.85e9,  # Hz, at the flux sweet spot
    "q0_a_pi": 0.62,  # drive amplitude of a pi pulse (DAC units)
    "q0_T1": 18_000,  # ns
    "q0_T2star": 9_000,  # ns
    "q0_T2echo": 16_000,  # ns
}
DETUNING = 0.4e6  # Hz, how far off the drive frequency is set on purpose

A_PI = DEVICE["q0_a_pi"]
DRIVE_FREQ = DEVICE["q0_f01"] + DETUNING

schema = BusSchema.transmon()
q = schema.q

print(f"pi amplitude {A_PI}, drive set to {DRIVE_FREQ / 1e9:.6f} GHz")
print("truth to recover:", {k: v for k, v in DEVICE.items() if k.startswith("q0_T")})

# %% [markdown]
r"""
## 4.1 Fragments

Every experiment in this part is the same shape. Put the qubit somewhere, wait, read it out. Only the middle changes, and the three middles are one pi pulse, two pi/2 pulses, and two pi/2 pulses with a pi in between.

Copy the pulse lines into three programs and the three drift apart. Someone fixes the DRAG `beta` in two of them and forgets the third. A `Fragment` is a named, parameterized sub-program. Write the pulse once, call it everywhere.
"""

# %% [markdown]
r"""
### Three rules

- The **first argument is the builder**. Every other argument becomes a `Parameter`, in order, and the fragment takes the function's name.
- Parameters are **untyped placeholders**. One can stand for a number, a bus, or a waveform, and the call site decides. `x90` below puts one in arithmetic (`amp / 2`).
- The body runs **once, at decoration time**, to record the AST. A Python `if` inside it is evaluated then, not per call.

One consequence follows. A repeat count cannot be a parameter. A Python `for` inside a fragment body runs at decoration and writes its copies into the definition, so a train of four pulses and a train of eight are two fragments rather than one called twice.
"""

# %%
@fragment
def x180(f, drive, amp):
    """A pi pulse: the DRAG shape Part 3 calibrated. `f` is the fragment builder."""
    f.play(drive, IQDrag(amplitude=amp, duration=40, sigma=10, beta=0.1))


@fragment
def x90(f, drive, amp):
    """A pi/2 pulse: same shape, half the area. `amp` is still the *pi* amplitude."""
    f.play(drive, IQDrag(amplitude=amp / 2, duration=40, sigma=10, beta=0.1))


print(x180)
print(x90)

demo = qp.QProgram(label="fragment_demo", schema=schema)
demo.call(x180, q[0].drive, A_PI)  # positional
demo.call(x90, q[0].drive, amp=A_PI)  # or by keyword, Python's own binding rules
print(qp.dumps(demo))

# %% [markdown]
r"""
Definitions come out as `fragment` sections before `body:`, and call sites stay call sites, so `x180(q[0].drive, 0.62)` is one AST node rather than an inlined copy. The expression survives too, as `IQDrag(amplitude=(amp / 2), ...)`.

`expand()` is the lowering. It returns a new program with every call replaced by a plain `block:` holding the substituted body. Validation and execution do this for you, so you rarely call it, but it is the thing to print when you want to see what a compiler will get. Substitution stops at the bound value, so the expanded pi/2 pulse reads `amplitude=(0.62 / 2)`, arithmetic still described rather than folded.
"""

# %%
flat = demo.expand()

print("fragments registered on the program:", list(demo.fragments))
print("fragments after expand():", list(flat.fragments))
print()
print(qp.dumps(flat))

# %% [markdown]
r"""
### Measurements inside a fragment

A measurement's auto-generated name normally embeds its bus (`q0/readout/m0`). Inside a fragment the bus is still a parameter, so the name is a plain `m0`, and repeated calls get suffixed at expansion (`m0`, `m0_2`). The handle lives inside the fragment, so `measurement_handles()` on the host program shows nothing until you expand.
"""

# %%
@fragment
def readout_block(f, ro):
    """Play the readout tone and integrate it."""
    f.play(ro, IQPair(Square(0.2, 2000), Square(0.0, 2000)))
    f.measure(ro, "readout", "weights", fields=(MF.IQ, MF.STATE))


read_demo = qp.QProgram(label="readout_demo", schema=schema)
read_demo.call(readout_block, q[0].readout)
read_demo.call(readout_block, q[0].readout)

print("handles before expand:", [h.name for h in read_demo.measurement_handles()])
print("handles after expand: ", [h.name for h in read_demo.expand().measurement_handles()])

# %% [markdown]
r"""
Fragments carry the pulses, `measure` stays in the host program. The handle then stays an ordinary Python variable and `result.get(m)` reads the way you wrote it. Every experiment below follows that rule.
"""

# %% [markdown]
r"""
## 4.2 T1

The first middle is the shortest one. Excite the qubit, wait, look. Sweep the wait and the excited-state population decays as

$$P_1(t) = e^{-t/T_1}.$$

The sweep below runs to a bit over three $T_1$. Stop at one and the amplitude and the time constant go degenerate, so both come back with a large error bar. Run to five and the last points only measure the noise floor. Three to four is the usual compromise.

One warning that holds for the whole part. **The reference executor has no timing model.** `wait` and `sync` change nothing about the numbers that come back. The delay reaches the result only because the measurement model reads `env["delay"]`, the dict of currently bound loop variables.
"""

# %%
t1 = qp.QProgram(label="t1", description="inversion recovery on q0", schema=schema)
delay = t1.variable("delay", label="Delay", units="ns")
t1_delays = qp.Range(0, 60_000, 1500)  # 1500 divides 60000, so the last point lands on it

with t1.average(shots=400):  # the shots collapse into one number per delay
    with t1.sweep(delay, t1_delays):
        t1.set_frequency(q[0].drive, DEVICE["q0_f01"])
        t1.call(x180, q[0].drive, A_PI)
        t1.wait(q[0].drive, delay)
        t1.sync()
        m_t1 = t1.measure(q[0].readout, "readout", "weights", fields=(MF.STATE, MF.IQ, MF.RAW))

delays = np.array(t1_delays.values())
print(f"{len(delays)} delays from {delays[0]:.0f} to {delays[-1]:.0f} ns")
print("measurement:", m_t1.name)

# %% [markdown]
r"""
The model plays the qubit and the readout chain. Two callables:

- `p_excited` is the probability that a shot is classified as $|1\rangle$, and it drives the `state` field.
- `response` is the noiseless IQ point. Dispersive readout puts $|0\rangle$ and $|1\rangle$ at two places in the IQ plane, and the shot average lands between them at the fraction given by the population. `blob` computes that point.

`noise=0.4` is per-shot gaussian noise on each quadrature, so the averaged IQ point carries real shot noise. `average(shots=400)` adds no dimension. The `state` field comes back as the fraction of shots classified as excited, one number per delay.
"""

# %%
GROUND = -1.0 - 0.4j  # where a |0> shot lands in the IQ plane
EXCITED = 1.0 + 0.4j  # where a |1> shot lands
AXIS = (EXCITED - GROUND) / abs(EXCITED - GROUND)  # the unit vector between them


def blob(p):
    """The shot-averaged IQ point for an excited-state population `p`."""
    return GROUND + p * (EXCITED - GROUND)


def p_t1(bus, env):
    """T1 (inversion recovery), delay in ns."""
    return np.exp(-env["delay"] / DEVICE["q0_T1"])


t1_result = qp.simulate(
    t1,
    model=qp.MockMeasurementModel(
        response=lambda bus, env: blob(p_t1(bus, env)),
        p_excited=p_t1,
        noise=0.4,
        raw_samples=16,
        seed=17,
    ),
)
population = t1_result.get(m_t1, field=MF.STATE)
print("state field:", population.dims, population.shape)
print("first three points:", np.round(population.values[:3], 3))

# %% [markdown]
r"""
Fit the exponential, then draw both. `result.plot` takes the handle and the field, reads from the shape that a one-dimensional sweep wants a line, and hands back the `Axes` it drew on, so the fit is one more call on the object that comes back. `markers=True` earns its place where the points are the measurement and the line is interpolation.

The delays are stored in nanoseconds and nobody reads a $T_1$ that way, so `coords=` restates the axis in microseconds and `value=` names the y axis. Anything you draw on the returned axes is in the figure's units, so the fit line divides the delays by 1000 too.
"""

# %%
# Fit an exponential with a free offset and read T1 off it.
def decay(t, amplitude, tau, offset):
    return amplitude * np.exp(-t / tau) + offset


popt, _ = curve_fit(decay, delays, population.values, p0=[1.0, 10_000.0, 0.0])
t1_fit = popt[1]
print(f"fitted T1 = {t1_fit / 1000:.2f} us   true = {DEVICE['q0_T1'] / 1000:.2f} us")

ax = t1_result.plot(
    m_t1,
    field=MF.STATE,
    style=Style(markers=True),
    coords={"delay": Quantity(units="us", transform=lambda v: v / 1000)},
    value=Quantity("Excited-state population"),
    title="Inversion recovery on q0",
)
ax.plot(delays / 1000, decay(delays, *popt), label=f"fit, T1 = {t1_fit / 1000:.1f} us")
ax.legend(fontsize=8)

# %% [markdown]
r"""
### Where the energy goes

Some of it goes down the readout line, since the resonator couples to the qubit on one side and to a 50 ohm line out of the fridge on the other. That channel, Purcell decay, runs at $\kappa (g/\Delta)^2$, and this chip's numbers put it alone at 16 microseconds, shorter than the 18 in `DEVICE` and therefore impossible. It is the same over-large $g$ Part 1 backed out of $\chi$. Real chips put a bandpass filter between resonator and line, which buys back an order of magnitude.

The rest goes into the materials. Two-level defects in the amorphous oxides absorb at whatever frequency they sit at, and they drift in and out of resonance with the qubit, so $T_1$ remeasured often enough wanders by a factor of two and is reported as a histogram rather than one number. Quasiparticles and stray radiation take the remainder, both fought with shielding rather than design.
"""

# %% [markdown]
r"""
## 4.3 Ramsey

$T_1$ does not care what your drive frequency is. Dephasing does. Relaxation loses the energy, dephasing keeps the energy and loses the clock. A qubit on the equator of the Bloch sphere is a phase, that phase advances at the difference between the qubit and the drive, and a qubit frequency that wanders takes the phase with it.

Same three moves, second middle. Two pi/2 pulses with a gap. The first puts the qubit on the equator, it precesses at the difference, and the second turns the accumulated phase into a population. The result is a fringe at the detuning, dying out at the dephasing time:

$$P_1(t) = \tfrac{1}{2}\left(1 + \cos(2\pi \delta t)\right) e^{-t/T_2^*}.$$
"""

# %% [markdown]
r"""
### What makes the frequency wander

- **$1/f$ flux noise**, from unpaired spins on the metal surfaces, and the reason the sweet spot in Part 3 matters.
- **Photon shot noise** in the readout resonator, since every stray photon Stark-shifts the qubit by $2\chi$.
- **Charge noise**, suppressed exponentially by the transmon design and rarely dominant now.
- **Two-level defects** again, coupling dispersively here instead of resonantly.
"""

# %% [markdown]
r"""
### Detuning on purpose

The drive is set 400 kHz high on purpose (`DRIVE_FREQ`). Sit exactly on resonance and the fringe stops oscillating, leaving a monotone decay that any slow drift can imitate and that tells you nothing about your frequency error. Detune by a known amount and you get a carrier. The fit has an oscillation to lock onto, the envelope separates from the drift, and the fringe frequency you measure is your frequency error directly.

Pick the detuning so that several periods fit inside $T_2^*$. Too slow and you see one lonely oscillation, too fast and you alias.
"""

# %%
ramsey = qp.QProgram(label="ramsey", description="Ramsey fringe on q0", schema=schema)
r_delay = ramsey.variable("delay", label="Delay", units="ns")

with ramsey.average(shots=400):
    with ramsey.sweep(r_delay, qp.Range(0, 20_000, 125)):
        ramsey.set_frequency(q[0].drive, DRIVE_FREQ)  # deliberately 400 kHz off
        ramsey.call(x90, q[0].drive, A_PI)
        ramsey.wait(q[0].drive, r_delay)
        ramsey.call(x90, q[0].drive, A_PI)
        ramsey.sync()
        m_ramsey = ramsey.measure(q[0].readout, "readout", "weights", fields=(MF.STATE,))


def p_ramsey(bus, env):
    """Ramsey with an intentional detuning and exponential decay."""
    t = env["delay"]
    return 0.5 * (1.0 + np.cos(2 * np.pi * DETUNING * t * 1e-9)) * np.exp(-t / DEVICE["q0_T2star"])


ramsey_result = qp.simulate(ramsey, model=qp.MockMeasurementModel(p_excited=p_ramsey, seed=23))
fringe = ramsey_result.get(m_ramsey, field=MF.STATE)
r_delays = fringe.coords["delay"].values
print(f"{len(r_delays)} points, {r_delays[-1] / 1000:.0f} us long, {fringe.dims} {fringe.shape}")

# %% [markdown]
r"""
Four parameters to fit: amplitude, $T_2^*$, the fringe frequency, and a phase. A least-squares fit of a cosine needs a decent starting frequency or it walks into a local minimum, so take the guess from an FFT of the data rather than typing a number. It lands within one bin, and the habit generalises to any oscillating fit.

The fit function has no constant offset. In this model the fringe and the mean decay together, so the curve relaxes to zero rather than to one half.
"""

# %% [markdown]
r"""
The fringe frequency is the practical output: it is the error in your drive frequency, and subtracting it tunes the qubit up. Run Ramsey, correct, run it again with a longer sweep, and each round buys roughly the ratio of the two sweep lengths in precision. Two or three rounds reach a kilohertz, where the qubit's own drift sets the floor.

One caveat. A single Ramsey gives the *magnitude* of the detuning, not its sign, because $\cos$ is even. Move the drive a known amount and see whether the fringe speeds up or slows down.

The figure is the T1 figure with a different middle in it. This sweep is dense enough that the markers want to be small, which `Style` takes as `markersize`.
"""

# %%
def fringe_model(t, amplitude, tau, freq, phase):
    return amplitude * np.exp(-t / tau) * (1.0 + np.cos(2 * np.pi * freq * t * 1e-9 + phase))


spectrum = np.abs(np.fft.rfft(fringe.values - fringe.values.mean()))
freq_axis = np.fft.rfftfreq(len(r_delays), d=(r_delays[1] - r_delays[0]) * 1e-9)
freq_guess = freq_axis[spectrum.argmax()]

popt, _ = curve_fit(fringe_model, r_delays, fringe.values, p0=[0.5, 8000.0, freq_guess, 0.0])
t2star_fit, detuning_fit = popt[1], popt[2]
print(f"FFT guess          = {freq_guess / 1e3:.1f} kHz")
print(f"fitted T2*         = {t2star_fit / 1000:.2f} us   true = {DEVICE['q0_T2star'] / 1000:.2f} us")
print(f"fitted detuning    = {detuning_fit / 1e3:.1f} kHz   true = {DETUNING / 1e3:.1f} kHz")

ax = ramsey_result.plot(
    m_ramsey,
    field=MF.STATE,
    style=Style(markers=True, markersize=3),
    coords={"delay": Quantity(units="us", transform=lambda v: v / 1000)},
    value=Quantity("Excited-state population"),
    title=f"Ramsey at {detuning_fit / 1e3:.0f} kHz detuning",
)
ax.plot(r_delays / 1000, fringe_model(r_delays, *popt), lw=1, label=f"fit, T2* = {t2star_fit / 1000:.1f} us")
ax.legend(fontsize=8)

# %%
corrected = DRIVE_FREQ - detuning_fit
print(f"drive was at   {DRIVE_FREQ / 1e9:.6f} GHz")
print(f"corrected to   {corrected / 1e9:.6f} GHz")
print(f"true f01 is    {DEVICE['q0_f01'] / 1e9:.6f} GHz")
print(f"residual error {(corrected - DEVICE['q0_f01']) / 1e3:+.1f} kHz")

# %% [markdown]
r"""
## 4.4 Hahn echo

$T_2^*$ mixes two things that are not the same: real decoherence, and a qubit frequency slightly different on every shot because something slow is drifting under you. Averaged over a few hundred shots the second looks exactly like the first, because a phase wrong in a different direction each time washes out as thoroughly as a phase destroyed.

A pi pulse in the middle of the delay separates them. It flips the Bloch vector about the drive axis, so the phase picked up in the first half gets subtracted during the second. An offset that held still across the sequence cancels exactly, one that changed halfway through does not. What survives is $T_2$, longer than $T_2^*$:

$$P_1(t) = \tfrac{1}{2} + \tfrac{1}{2} e^{-t/T_2}.$$
"""

# %% [markdown]
r"""
### Fixing the offset

Third middle, and the pieces are in hand. x90, wait $t/2$, x180, wait $t/2$, x90, built from the two fragments of 4.1 and from `wait` with an expression, since `delay / 2` is a perfectly good duration and serializes as `wait q[0].drive (delay / 2)`.

Fix the offset at 0.5 rather than fitting it. With the detuning refocused the curve relaxes to the fully mixed value, and you know that number without measuring it. Leave it free and it trades against `tau`, and the error bar on $T_2$ roughly triples for nothing.
"""

# %%
def p_echo(bus, env):
    """Hahn echo: the detuning is refocused, only decay is left."""
    return 0.5 + 0.5 * np.exp(-env["delay"] / DEVICE["q0_T2echo"])


echo = qp.QProgram(label="hahn_echo", description="Hahn echo on q0", schema=schema)
e_delay = echo.variable("delay", label="Delay", units="ns")

with echo.average(shots=600):
    with echo.sweep(e_delay, qp.Range(0, 40_000, 800)):
        echo.set_frequency(q[0].drive, DEVICE["q0_f01"])
        echo.call(x90, q[0].drive, A_PI)
        echo.wait(q[0].drive, e_delay / 2)
        echo.call(x180, q[0].drive, A_PI)
        echo.wait(q[0].drive, e_delay / 2)
        echo.call(x90, q[0].drive, A_PI)
        echo.sync()
        m_echo = echo.measure(q[0].readout, "readout", "weights", fields=(MF.STATE,))

echo_result = qp.simulate(echo, model=qp.MockMeasurementModel(p_excited=p_echo, seed=31))
echo_data = echo_result.get(m_echo, field=MF.STATE)
e_delays = echo_data.coords["delay"].values

echo_fit, _ = curve_fit(
    lambda t, amplitude, tau: 0.5 + amplitude * np.exp(-t / tau),
    e_delays,
    echo_data.values,
    p0=[0.5, 10_000.0],
)
echo_amp, t2_fit = echo_fit
print(f"fitted T2 = {t2_fit / 1000:.2f} us   true = {DEVICE['q0_T2echo'] / 1000:.2f} us")

# %% [markdown]
r"""
Plot it, then put the three numbers next to each other. The ordering $T_2^* < T_2 < 2T_1$ follows from arithmetic rather than from agreement among labs, so a set that violates either bound is a bug in the analysis and not a discovery.
"""

# %%
ax = echo_result.plot(
    m_echo,
    field=MF.STATE,
    style=Style(markers=True),
    coords={"delay": Quantity(units="us", transform=lambda v: v / 1000)},
    value=Quantity("Excited-state population"),
    title="Hahn echo on q0",
)
ax.plot(
    e_delays / 1000,
    0.5 + echo_amp * np.exp(-e_delays / t2_fit),
    label=f"fit, T2 = {t2_fit / 1000:.1f} us",
)
ax.axhline(0.5, ls=":", lw=1, label="fully mixed")
ax.legend(fontsize=8)

# %%
rows = [
    ("T1", t1_fit, DEVICE["q0_T1"]),
    ("T2*", t2star_fit, DEVICE["q0_T2star"]),
    ("T2 (echo)", t2_fit, DEVICE["q0_T2echo"]),
]
print(f"{'quantity':<11}{'fitted':>12}{'true':>12}{'error':>9}")
for name, fitted, true in rows:
    print(f"{name:<11}{fitted / 1000:>9.2f} us{true / 1000:>9.2f} us{100 * (fitted / true - 1):>8.1f}%")
print()
print(f"T2* < T2 < 2*T1 holds: {t2star_fit < t2_fit < 2 * t1_fit}")

# %% [markdown]
r"""
## 4.5 The three measurement fields

The T1 program asked for all three: `fields=(MF.STATE, MF.IQ, MF.RAW)`. One `measure` call, three arrays, three shapes. `field=` picks one.

| field | shape | what it is |
|---|---|---|
| `MF.IQ` | `(*sweeps, IQ)` | integrated I and Q, averaged over shots. The default. |
| `MF.STATE` | `(*sweeps)` | classified 0/1 per shot, averaged into a population. |
| `MF.RAW` | `(*sweeps, time, IQ)` | the ADC trace, averaged over shots. |
"""

# %% [markdown]
r"""
### One pipeline

The three are points along one pipeline, and each throws something away. `raw` is the ADC stream, and you ask for it when you are debugging the readout itself: it shows the resonator ringing up, it catches a pulse longer than the acquisition window, and optimal integration weights are computed from it. Multiply it by the weights and sum, and you have `iq`. Compare `iq` to a threshold, and you have `state`. Ask for `raw` while commissioning a readout and stop once it works, because the data volume is a hundred times larger.
"""

# %% [markdown]
r"""
### Fields you did not ask for

`result.get(m)` defaults to `MF.IQ` and raises `KeyError` for a field the measurement never requested. It never substitutes a different array, because a `state` array returned where the caller expected IQ would look like data all the way downstream.

The `time` axis of a `raw` array is the model's `raw_samples`, read once at the start of the run, and that is where the 16 in the shape below comes from. A model that simulates no ADC leaves the attribute off and `MeasurementSample.raw` keeps its empty default, so the two hand-written models later declare neither. A model that does produce traces has every trace checked against `raw_samples`.
"""

# %%
for field in (MF.IQ, MF.STATE, MF.RAW):
    array = t1_result.get(m_t1, field=field)
    print(f"{field:<6} dims={array.dims!s:<26} shape={array.shape}")

no_iq = qp.QProgram(schema=schema)
m_state_only = no_iq.measure(q[0].readout, "readout", "weights", fields=(MF.STATE,))
try:
    qp.simulate(no_iq, model=qp.MockMeasurementModel()).get(m_state_only)
except KeyError as exc:
    print("bare get() on a state-only measurement:", exc)

# %% [markdown]
r"""
`state` and `iq` are two views of the same shots. The classifier already collapsed each shot to a 0 or a 1, so `state` is the population directly. `iq` has to be projected onto the line between the two blobs before it means anything, and it carries the shot noise of the integration. Both recover T1 to better than 2 percent, and the state fit is closer because classification already threw away noise the projection has to average over.

Drawing them together is the case the composable axes were built for: the result can draw `state` on its own, the projection is arithmetic no result could know about, and the second goes on the axes the first returned with an ordinary `ax.plot`.
"""

# %%
iq = t1_result.get(m_t1)  # default field
z = iq.sel(IQ="I").values + 1j * iq.sel(IQ="Q").values
projected = ((z - GROUND) * np.conj(AXIS)).real / abs(EXCITED - GROUND)

from_state, _ = curve_fit(decay, delays, population.values, p0=[1.0, 10_000.0, 0.0])
from_iq, _ = curve_fit(decay, delays, projected, p0=[1.0, 10_000.0, 0.0])
print(f"T1 from state = {from_state[1] / 1000:.2f} us")
print(f"T1 from iq    = {from_iq[1] / 1000:.2f} us")

ax = t1_result.plot(
    m_t1,
    field=MF.STATE,
    style=Style(markers=True),
    coords={"delay": Quantity(units="us", transform=lambda v: v / 1000)},
    value=Quantity("Excited-state population"),
    title="Same shots, two fields",
)
ax.lines[0].set_label("state field")
ax.plot(delays / 1000, projected, "x", ms=5, ls="none", label="iq, projected")
ax.legend(fontsize=8)

# %% [markdown]
r"""
## 4.6 Single-shot readout

Where do the two clouds come from? The resonator sits at $f_r - \chi$ when the qubit is in $|0\rangle$ and at $f_r + \chi$ when it is in $|1\rangle$. Park a tone between them and the returning field has a different amplitude and phase in the two cases, so the integrated IQ point lands in one of two places.

The distance $d$ between them grows with the photon number and with $2\chi/\kappa$, the ratio Part 1 worked out. The width $\sigma$ of each cloud is amplifier noise over the square root of the integration time, so it shrinks the longer you look. Readout fidelity is the ratio of those two numbers and nothing else.
"""

# %% [markdown]
r"""
### Dropping the average

`average(shots)` throws the individual shots away and hands you the mean. To keep them, make the shot index a **sweep variable** and drop the average:

```python
with program.sweep(shot, qp.Range(0, 599, 1)):
    ...
```

Every point then holds exactly one shot, and the result array gains a `shot` dimension. Nothing reads the variable, and that is fine: a sweep variable no operation uses still drives its loop. A sequencer does this when you ask it to stream every acquisition instead of accumulating.
"""

# %% [markdown]
r"""
### Repeat is not a shot axis

`qp.Repeat` from Part 2 looks like the shorter way to write this and it is not. It multiplies a source's points rather than adding an axis. `qp.Repeat(qp.Values([0, 1]), times=4)` sweeps `0 1 0 1 0 1 0 1` on one flattened dimension whose coordinates give no way to tell the repetitions apart. A shot dimension has to come from a loop of its own.
"""

# %% [markdown]
r"""
### The single-shot model

The model changes with the loop. Averaged IQ was one point on a line, single shots are two clouds, and `sigma` decides whether this readout works. Two programs follow, one reading the qubit as it sits and one with a pi pulse in front. The 2 percent that come out wrong in each are preparation error, and realistic, because a real pi pulse is never perfect and a real qubit is never perfectly cold.
"""

# %%
class BlobModel:
    """Single-shot readout: two gaussian clouds in the IQ plane, `p1` of the shots in the upper one."""

    def __init__(self, p1, sigma=0.55, seed=3):
        self.p1, self.sigma = p1, sigma
        self.rng = np.random.default_rng(seed)

    def sample(self, bus, env):
        state = int(self.rng.random() < self.p1)
        center = EXCITED if state else GROUND
        return qp.MeasurementSample(
            i=center.real + self.rng.normal(0, self.sigma),
            q=center.imag + self.rng.normal(0, self.sigma),
            state=state,
        )


one = BlobModel(p1=1.0, seed=0).sample("q0/readout", {})
print(f"one excited shot: I={one.i:+.2f} Q={one.q:+.2f} state={one.state} raw={one.raw.shape}")
# Nothing here asks for the trace, so the model produces none and `raw` keeps its empty default.

# %%
def single_shots(prepare_excited, n=600):
    program = qp.QProgram(label="single_shot", schema=schema)
    shot = program.variable("shot", label="Shot index")
    with program.sweep(shot, qp.Range(0, n - 1, 1)):  # one shot per point, no average
        if prepare_excited:
            program.call(x180, q[0].drive, A_PI)
        program.sync()
        handle = program.measure(q[0].readout, "readout", "weights", fields=(MF.IQ, MF.STATE))
    return program, handle


ground_program, m_ground = single_shots(prepare_excited=False)
excited_program, m_excited = single_shots(prepare_excited=True)

ground_run = qp.simulate(ground_program, model=BlobModel(p1=0.02, seed=5))
excited_run = qp.simulate(excited_program, model=BlobModel(p1=0.98, seed=6))
ground, excited = ground_run.get(m_ground), excited_run.get(m_excited)

# The model reports the true state of each shot, so keep it as the answer key.
truth = np.concatenate(
    [
        ground_run.get(m_ground, field=MF.STATE).values,
        excited_run.get(m_excited, field=MF.STATE).values,
    ]
)
print("dims:", ground.dims, ground.shape)
print("no average, so each point is one shot:", np.round(ground.values[:3, 0], 2))
print(f"prepared wrong: {int(truth[:600].sum())} cold shots hot, {int(600 - truth[600:].sum())} hot shots cold")

# %% [markdown]
r"""
`kind="scatter"` is the one figure the shape never implies, since plotting I against Q is a choice no dimension count makes for you. It puts I on one axis and Q on the other and flattens everything else into the cloud.

Two clouds means two calls. The first makes the axes, the second draws on it through `target=`, and a palette rotated by one slot keeps them from sharing a hue. The legend labels go on afterwards, because the two runs are separate results. A scatter refuses `value=Quantity(label=...)` outright: its two axes are I and Q and already name themselves. A name for the figure goes in `title=`.
"""

# %%
ax = ground_run.plot(m_ground, kind="scatter", title="600 single shots per preparation")
rotated = Style(theme=replace(LIGHT, series=LIGHT.series[1:] + LIGHT.series[:1]))
excited_run.plot(m_excited, kind="scatter", target=ax, style=rotated)
for cloud, label in zip(ax.collections, ("prepared |0>", "prepared |1>"), strict=True):
    cloud.set_label(label)
ax.set_aspect("equal")
ax.legend()

# %% [markdown]
r"""
### The threshold

To turn a shot into a bit, project onto the line joining the two cloud centres and threshold at the midpoint. The centres come from the data, not from the model. This is a calibration, and you redo it whenever the readout drifts.

The midpoint is right here because both clouds have the same width and you prepared each equally often. On a real device neither holds. The excited cloud grows a tail toward the ground cloud, since a qubit that relaxes partway through the integration window lands somewhere in between, and the optimal threshold slides toward $|0\rangle$ to compensate.
"""

# %% [markdown]
r"""
### Two error numbers

- The **measured** error is the threshold decision against what you prepared. The lab has nothing else, and it charges readout for preparation error too.
- The **assignment** error is that decision against the state each shot was really in. Only the simulator knows it, so only here can you price the readout alone.

The gap between them is the preparation error. A readout fidelity quoted without saying which of the two it is invites misuse, usually a vendor putting assignment fidelity next to a competitor's measured fidelity.

The histogram is the one figure here the result cannot draw: its x axis is a projection you computed from two runs and its y axis is a bin count, so nothing on either result says those numbers belong in one picture. Hand-rolled axes are the right answer there.
"""

# %%
def project(array):
    """Project single shots onto the |0> to |1> axis."""
    z = array.sel(IQ="I").values + 1j * array.sel(IQ="Q").values
    return ((z - GROUND) * np.conj(AXIS)).real


shots = np.concatenate([project(ground), project(excited)])
prepared = np.concatenate([np.zeros(ground.sizes["shot"]), np.ones(excited.sizes["shot"])])
threshold = 0.5 * (shots[prepared == 0].mean() + shots[prepared == 1].mean())
decided = (shots > threshold).astype(float)

separation = shots[truth == 1].mean() - shots[truth == 0].mean()
sigma = 0.5 * (shots[truth == 0].std() + shots[truth == 1].std())
print(f"blob separation  = {separation / sigma:.1f} sigma")
print(f"threshold        = {threshold:+.3f}")
print(f"measured error   = {100 * (decided != prepared).mean():.1f}%  (readout plus preparation)")
print(f"assignment error = {100 * (decided != truth).mean():.1f}%  (readout alone)")
print(f"gaussian estimate= {100 * 0.5 * math.erfc(separation / (2 * np.sqrt(2) * sigma)):.1f}%")

bins = np.linspace(-2.0, 4.0, 60)
_, ax = plt.subplots()
ax.hist(shots[prepared == 0], bins=bins, alpha=0.6, label="prepared |0>")
ax.hist(shots[prepared == 1], bins=bins, alpha=0.6, label="prepared |1>")
ax.axvline(threshold, color="k", ls="--", lw=1, label=f"threshold = {threshold:.2f}")
ax.set_xlabel("Projection onto the |0> to |1> axis (arb.)")
ax.set_ylabel("Shots")
ax.set_title("Single-shot histogram and threshold")
ax.legend(fontsize=8)

# %% [markdown]
r"""
## 4.7 Active reset

A qubit does not start cold, and waiting for it to get there is the slowest thing in a run. Passive reset idles for several $T_1$ before every shot. Active reset measures instead and fires a pi pulse only if the qubit came up excited, turning a wait into a decision.
"""

# %% [markdown]
r"""
### Why the qubit is warm

A transmon at 4.85 GHz in thermal equilibrium with a 20 mK stage would sit at $e^{-hf/k_BT}$, and nobody has ever measured that. Real devices come in at an effective temperature of 40 to 60 mK, a residual excited population of a percent or two. The gap is stray infrared, imperfect filtering, and hot electrons in the ground plane. The model below uses 18 percent, hotter than any device you would keep, so the effect is unmistakable.
"""

# %% [markdown]
r"""
### Conditionals

`if_` / `elif_` / `else_` are context managers, and they chain exactly like Python's. The condition is a **measurement-state predicate**, nothing wider yet:

| shape | reads as |
|---|---|
| `m.state == 1` | this measurement classified as excited |
| `m.state != 0` | the same thing, spelled the other way |
| `m1.state == m2.state` | two measurements agreed |
| `qp.eq(m.state, 0)`, `qp.ne(m.state, 1)` | the helper forms, for building conditions programmatically |

The narrowness is deliberate rather than unfinished. A condition inside a sequence has to be evaluated by an FPGA between one pulse and the next, in tens of nanoseconds, while the qubit is still coherent. Comparing one classified bit against a constant fits in that budget. Arbitrary arithmetic does not.
"""

# %% [markdown]
r"""
### Where the rules are enforced

The condition has to be a measurement-state predicate, and passing anything else raises on the spot. `elif_` and `else_` have to come **immediately** after their arm, because anything appended in between closes the chain. The third rule waits for `validate`. Every measurement you reference must have asked for `MF.STATE`, so a condition on a classification nobody computed is a diagnostic rather than a guess. `qp.simulate` validates before it executes, so such a program raises `UnsupportedOperationError` instead of branching.

There is no `and` or `or`. `qp.and_(a, b)` inside an `if_` raises and names what it got, so a compound test becomes a second `if_` nested inside the arm.
"""

# %%
oops = qp.QProgram(schema=schema)
m_no_state = oops.measure(q[0].readout, "readout", "weights")  # default fields=(MF.IQ,)
with oops.if_(m_no_state.state == 1):
    oops.play(q[0].drive, "pi")
for diagnostic in qp.validate(oops, qp.reference_capabilities())[0]:
    print(f"[{diagnostic.severity}] {diagnostic.code}: {diagnostic.message}")

bad = qp.QProgram(schema=schema)
counter = bad.variable("counter")
try:
    with bad.if_(counter > 3):  # not a measurement-state predicate
        bad.play(q[0].drive, "pi")
except qp.ValidationError as exc:
    print("ValidationError:", exc)

# %% [markdown]
r"""
Now the fake qubit. The reference executor does not simulate the pi pulse, so the model keeps the bookkeeping itself. A fresh shot starts hot with probability `p_hot`, and the *second* measurement of a shot happens after the reset attempt, which lands the qubit in the ground state unless the pulse missed.

The model is a stand-in. The program, the conditional, the NaN handling, and the arithmetic at the end are the real thing.
"""

# %%
class ResetModel:
    """A qubit that is sometimes born hot, and a reset pulse that usually works."""

    def __init__(self, p_hot=0.18, pi_error=0.03, sigma=0.3, seed=11):
        self.p_hot, self.pi_error, self.sigma = p_hot, pi_error, sigma
        self.rng = np.random.default_rng(seed)
        self.shot, self.excited = None, 0

    def sample(self, bus, env):
        if env["shot"] != self.shot:  # a new shot: the qubit arrives however it arrives
            self.shot, self.excited = env["shot"], int(self.rng.random() < self.p_hot)
        elif self.excited:  # a later measurement in the same shot: the pi pulse has fired
            self.excited = int(self.rng.random() < self.pi_error)
        center = EXCITED if self.excited else GROUND
        return qp.MeasurementSample(
            i=center.real + self.rng.normal(0, self.sigma),
            q=center.imag + self.rng.normal(0, self.sigma),
            state=self.excited,
        )


# Two looks at the same shot. The second one happens after the reset pulse, by construction.
peek_model = ResetModel(seed=3)
print("shot 0, first look :", peek_model.sample("q0/readout", {"shot": 0.0}).state)
print("shot 0, second look:", peek_model.sample("q0/readout", {"shot": 0.0}).state)

# %% [markdown]
r"""
One more piece of the result contract. **A measurement inside a conditional arm holds NaN wherever the arm did not run.** The averaging is count-based, and no executions means no mean. A zero would be indistinguishable from a measurement that ran and came back cold, and any downstream average would quietly include shots that never happened. With single shots on the sweep axis you can see which shots took which branch.
"""

# %%
peek = qp.QProgram(label="nan_demo", schema=schema)
peek_shot = peek.variable("shot", label="Shot index")
with peek.sweep(peek_shot, qp.Range(0, 11, 1)):  # 12 shots, small enough to read
    check = peek.measure(q[0].readout, "readout", "weights", name="check", fields=(MF.STATE,))
    with peek.if_(check.state == 1):
        peek.call(x180, q[0].drive, A_PI)
        peek.sync()
        verify = peek.measure(q[0].readout, "readout", "weights", name="verify", fields=(MF.STATE,))

peek_result = qp.simulate(peek, model=ResetModel(seed=0))
print("check :", peek_result.get(check, field=MF.STATE).values)
print("verify:", peek_result.get(verify, field=MF.STATE).values)
print("arm ran on", int(np.isfinite(peek_result.get(verify, field=MF.STATE).values).sum()), "of 12 shots")

# %% [markdown]
r"""
### 🧩 Exercise 4.1

Run the reset experiment on 400 single shots and report the excited-state population before and after. Reading a measurement outcome back into the control flow is the one move here you have not written before.

1. One variable `shot`, swept with `qp.Range(0, 399, 1)`, no `average`.
2. `check = program.measure(..., name="check", fields=(MF.STATE,))`.
3. `with program.if_(check.state == 1):` call `x180`, `sync`, and measure again as `"verify"`.
4. `with program.else_():` wait out the pi pulse the other arm plays, `program.wait(q[0].drive, 40)`. Nothing requires a second arm, but on hardware an arm that holds a bus longer than its sibling shifts everything after the branch.
5. Run it with `ResetModel()` and pull both state arrays.
6. The population before is the mean of `check`. For the population after, remember the NaN: a cold shot never entered the arm, so its outcome is the one `check` already reported, and `np.where(np.isnan(verify), check, verify)` is the whole calculation.

Expect roughly 18 percent before and 1 percent after, the residual being the shots where the pi pulse missed. Call the program `reset`, because the cell after your solution prints its `.qp` text.
"""

# %% solution
reset = qp.QProgram(label="active_reset", description="measure, then fix it", schema=schema)
r_shot = reset.variable("shot", label="Shot index")

with reset.sweep(r_shot, qp.Range(0, 399, 1)):
    check = reset.measure(q[0].readout, "readout", "weights", name="check", fields=(MF.STATE,))
    with reset.if_(check.state == 1):
        reset.call(x180, q[0].drive, A_PI)
        reset.sync()
        verify = reset.measure(q[0].readout, "readout", "weights", name="verify", fields=(MF.STATE,))
    with reset.else_():
        reset.wait(q[0].drive, 40)

reset_result = qp.simulate(reset, model=ResetModel())
before = reset_result.get(check, field=MF.STATE).values
verified = reset_result.get(verify, field=MF.STATE).values
after = np.where(np.isnan(verified), before, verified)

print(f"reset fired on {int(np.isfinite(verified).sum())} of {len(before)} shots")
print(f"population before reset = {100 * before.mean():.1f}%")
print(f"population after reset  = {100 * after.mean():.1f}%")

# %% stub
# TODO: active reset on 400 single shots.
#
# 1) reset = qp.QProgram(label="active_reset", schema=schema); r_shot = reset.variable("shot")
# 2) with reset.sweep(r_shot, qp.Range(0, 399, 1)):
# 3)     check = reset.measure(..., name="check", fields=(MF.STATE,))
# 4)     with reset.if_(check.state == 1): x180, sync, measure(name="verify", fields=(MF.STATE,))
# 5)     with reset.else_(): reset.wait(q[0].drive, 40)
# 6) reset_result = qp.simulate(reset, model=ResetModel())
# 7) before = ...get(check, field=MF.STATE).values; verified = ...get(verify, ...).values
# 8) after = np.where(np.isnan(verified), before, verified)
#
# Print both populations. Expect about 18% before and 1% after.

# %%
print(qp.dumps(reset))

# %% [markdown]
r"""
Read that text once more. The feedback is in the file. `if check.state == 1:` is a statement in a portable text format, not a vendor call, and the same intent used to be spelled `program.<vendor>.active_reset(...)`, which locked the experiment to one rack. A platform with a hand-tuned reset choreography can still recognise the pattern and lower it to whatever its sequencer does best.
"""

# %% [markdown]
r"""
## Recap

- A **fragment** is a pulse block with parameters. `@fragment` records the body once, `call` appends a node, `expand()` inlines it. Keep `measure` in the host program.
- **T1, T2\*, T2** came out of the same three moves with a different middle, and all three fits landed within a couple of percent of the device.
- $T_1$ is energy leaving. $T_2^*$ adds every source of frequency wander on top, and the echo removes whatever is slower than the sequence.
- The fringe frequency from Ramsey is your drive frequency error, and detuning on purpose gives the fit a carrier to lock onto.
- One `measure` produces up to three **fields**, and they are one pipeline. Weight and sum `raw` for `iq`, threshold `iq` for `state`.
- Every figure but the histogram came out of `result.plot(...)`, with the fit and the legend labels added to the `Axes` it returned.
- Dropping `average` and sweeping a **shot index** gives you single shots, the data a threshold gets calibrated on.
- **Feedback** is `if_(handle.state == 1)`, with NaN in the arm that did not run, and it serializes like any other statement.
"""

# %% [markdown]
r"""
## Next

Part 5 takes these exact programs to a machine where the flux line has no sequencer, and asks what has to change before they run.
"""
