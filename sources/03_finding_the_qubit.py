# %% [markdown]
r"""
# 03 · Finding the qubit

Part 2 found the readout resonator, which tells you where to point the readout tone and nothing about the qubit. A transmon at 4.85 GHz leaves no mark on a 7.2 GHz transmission scan.

Two-tone spectroscopy closes that gap and finds `f01`. Rabi in amplitude turns it into a pi pulse. A `WaveformLibrary` holds the pulse so later programs can name it. The flux arc maps `f01` against a DC bias, and its outer loop is the first here that cannot run on a sequencer.

Each experiment consumes the answer the one before it produced, and every fit prints its value next to the true one.
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
from dataclasses import replace

import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy.optimize import curve_fit

import qprogram as qp
from qprogram import MeasurementField as MF
from qprogram.buses import BusSchema
from qprogram.plotting import DEFAULT_SIZE, LIGHT, Quantity, Style
from qprogram.waveforms import IQDrag, IQPair, Square

print("numpy", np.__version__, "| scipy", scipy.__version__, "(curve_fit does every fit below)")

# %% [markdown]
r"""
## 3.0 The device

`DEVICE` holds the truth about the simulated chip. The measurement models read it because they play the part of the fridge, and the print statements read it to grade the fits. The programs use one number from it, `q0_fr`, and only because Part 2 measured that one already. Code destined for hardware would know none of them.

Part 2 also left the readout pulse and the integration weights behind. The programs below name them as `"readout"` and `"weights"`, and the library in 3.3 is where the objects go.
"""

# %%
DEVICE = {
    "q0_f01": 4.85e9,  # Hz, qubit transition at the flux sweet spot
    "q0_fr": 7.20e9,  # Hz, readout resonator (found in Part 2)
    "q0_kappa": 1.5e6,  # Hz, resonator linewidth (FWHM)
    "q0_chi": -1.8e6,  # Hz, dispersive shift
    "q0_a_pi": 0.62,  # drive amplitude of a pi pulse (DAC units)
    "q0_linewidth": 2.0e6,  # Hz, spectroscopy FWHM at low power
    "flux_period": 1.0,  # V, one flux quantum in bias volts
    "flux_offset": 0.05,  # V, where the sweet spot actually sits
}

schema = BusSchema.transmon()
q = schema.q

READOUT_PULSE = IQPair(I=Square(amplitude=0.2, duration=2000), Q=Square(amplitude=0.0, duration=2000))
WEIGHTS = IQPair(I=Square(amplitude=1.0, duration=2000), Q=Square(amplitude=1.0, duration=2000))

print("drive bus  :", q[0].drive, "channel:", q[0].drive.channel)
print("readout bus:", q[0].readout, "acquires:", q[0].readout.acquires)
print("readout pulse:", READOUT_PULSE.get_duration(), "ns")
print("target to recover: f01 =", DEVICE["q0_f01"] / 1e9, "GHz")

# %% [markdown]
r"""
## 3.1 Two-tone spectroscopy

Nothing you send down the readout line at 7.2 GHz touches something sitting at 4.85 GHz, and the drive line has no ADC. The qubit is only ever seen through the resonator, so you run two tones at once.

1. Park the readout tone on the resonator, where Part 2 put it.
2. Send a second tone down the **drive** line and sweep it across the band where the qubit ought to be.
3. On resonance the qubit is excited, the coupled resonator shifts by $2\chi$ = 3.6 MHz, and against a 1.5 MHz linewidth the parked readout tone falls off the dip. The transmission jumps.

The signal is not the qubit. It is the resonator moving, and you cannot see that unless you were already parked in the right place. The resonator had to come first for that reason.
"""

# %% [markdown]
r"""
### The saturation tone

The drive pulse for this scan is weak and long, and both choices are deliberate.

Weak, because the amplitude of a pi pulse is the thing this part exists to produce, so a clean flip is not yet available. A weak tone saturates the transition instead, and a saturated two-level system tops out at a population of 0.5. The model below returns 0.45 on resonance. A two-tone peak above 0.5 is a readout calibration error, not a very excited qubit.

Long, because the steady state has to be reached before the readout looks, and the transition saturates in well under a microsecond.

The drive bus is an IQ channel, so the tone is an `IQPair`. A bare `Square` there raises a `ValidationError` at build time.
"""

# %% [markdown]
r"""
### The scan window

The window is 20 MHz wide, so this scan assumes you already know `f01` to about that much, from the chip design or from a survey like the flux arc in 3.4. A weak tone leaves the line near its 2 MHz low-power width, and the step below puts several points across it. Part 1 derives that width from the much narrower coherence linewidth, power-broadened by the very tone you are using to see it.
"""

# %%
SATURATION = IQPair(
    I=Square(amplitude=0.02, duration=4000),  # 4 us at 2% of full scale
    Q=Square(amplitude=0.0, duration=4000),
)


def p_spec(bus, env):
    """Excited-state population under a long weak drive: a Lorentzian peak at f01."""
    hwhm = DEVICE["q0_linewidth"] / 2
    return 0.45 / (1.0 + ((env["drive_freq"] - DEVICE["q0_f01"]) / hwhm) ** 2)


print("on resonance :", round(p_spec(None, {"drive_freq": DEVICE["q0_f01"]}), 4))
print("2 MHz off    :", round(p_spec(None, {"drive_freq": DEVICE["q0_f01"] + 2e6}), 4))
print("20 MHz off   :", round(p_spec(None, {"drive_freq": DEVICE["q0_f01"] + 20e6}), 4))

# %% [markdown]
r"""
### The state field

Part 2 read `iq`, the integrated readout point, because a resonator scan is about transmission. Here the quantity of interest is the qubit population, so the measurement asks for a different field.

```python
program.measure(bus, "readout", "weights", fields=(MF.STATE,))
```

`fields=` asks the platform for classified single-shot outcomes rather than the integrated point alone. Three things follow.

- `average(shots)` adds no dimension. Averaging classified zeros and ones gives the excited-state population directly, a float between 0 and 1.
- The scatter is binomial, not instrumental. $N$ classified shots of an outcome with excited probability $p$ carry a standard error of $\sqrt{p(1-p)/N}$, about 0.035 at the top of this peak. The `noise=` argument of `MockMeasurementModel` perturbs the IQ point, not the classified outcome, so the models here do not pass it.
- Read it back with `result.get(handle, field=MF.STATE)` and draw it with `result.plot(handle, field=MF.STATE)`. A bare `result.get(handle)` defaults to `iq` and raises `KeyError`, because this measurement never asked for `iq`.

In the simulator the `p_excited` callback supplies the probability and the model draws the shots. On real hardware the classifier needs its own calibration, and Part 4 does that with single shots.
"""

# %%
spec = qp.QProgram(
    label="qubit_spectroscopy",
    description="Two-tone scan for f01 on q0",
    schema=schema,
)
drive_freq = spec.variable("drive_freq", label="Drive frequency", units="Hz")

# 81 frequency points at 200 shots each.
with spec.average(shots=200):
    with spec.sweep(drive_freq, qp.Linspace(4.840e9, 4.860e9, 81)):
        spec.set_frequency(q[0].readout, DEVICE["q0_fr"])  # park the readout on the resonator
        spec.set_frequency(q[0].drive, drive_freq)  # the tone we are sweeping
        spec.play(q[0].drive, SATURATION)
        spec.sync()  # on hardware, hold the readout until the drive finishes
        m_spec = spec.measure(q[0].readout, "readout", "weights", fields=(MF.STATE,))

print("variables :", [v.id for v in spec.variables])
print("handle    :", m_spec.name)
print("sweep step:", (4.860e9 - 4.840e9) / 80 / 1e6, "MHz")
print()
print(qp.dumps(spec))

# %% [markdown]
r"""
Two details in that text. The readout pulse and weights are still the strings `"readout"` and `"weights"`, because nothing here depends on their shape. And `fields=["state"]` sits on the measure line, so the file records what the experiment asked the hardware to produce.

The `label` and `units` on `drive_freq` ride along on the coordinate, so the x axis of the next figure names itself. Declare them on every variable you sweep. `Quantity` then moves hertz to gigahertz on the drawing without touching the array.
"""

# %%
model = qp.MockMeasurementModel(p_excited=p_spec,  seed=11)
result = qp.simulate(spec, model=model)

pop = result.get(m_spec, field=MF.STATE)
print("dims:", pop.dims, "shape:", pop.shape)

spec_freqs = pop.coords["drive_freq"].values
spec_pop = pop.values

# Reused by every figure below. The array stays in hertz; only the drawing moves.
GHZ = Quantity(units="GHz", transform=lambda v: v / 1e9)
POPULATION = Quantity("Excited-state population")

ax = result.plot(
    m_spec,
    field=MF.STATE,
    style=Style(markers=True),  # 81 coarse points: the samples are the measurement
    coords={"drive_freq": GHZ},
    value=POPULATION,  # the state field would otherwise label itself "State"
    title="Two-tone qubit spectroscopy on q0",
)
ax.lines[0].set_label("measured")
ax.axvline(DEVICE["q0_f01"] / 1e9, color=LIGHT.muted, linestyle=":", label="true f01")
ax.legend(fontsize=8)
plt.show()

# %% [markdown]
r"""
### Fitting the peak

The highest point in the scan is a poor estimate of `f01`. It can only be as accurate as your step size, and with binomial scatter on every point it lands on the wrong grid point often enough to matter. A fit uses every point at once, so the uncertainty shrinks roughly as the square root of the point count, and it comes with an error bar you can quote.

The peak is a Lorentzian:

$$P(f) = P_0 + \frac{A}{1 + \left(\dfrac{f - f_{01}}{\gamma}\right)^2}$$

with $\gamma$ the half width at half maximum, so the linewidth you would quote in a paper is $2\gamma$. `curve_fit` wants a starting guess for each of the four parameters, and every one is read off the data: the peak position from `argmax`, the height from the range, the width from your prior, the floor from the median.

`curve_fit` is a local optimizer, so a Lorentzian started three linewidths away sees a flat landscape and stays where it was put.
"""

# %%
def lorentzian(f, f0, height, hwhm, floor):
    """Lorentzian peak, parameterised the way a spectroscopist reads it off a plot."""
    return floor + height / (1.0 + ((f - f0) / hwhm) ** 2)


guess = (
    spec_freqs[spec_pop.argmax()],  # centre
    spec_pop.max() - np.median(spec_pop),  # height
    1e6,  # HWHM, order of magnitude is enough
    float(np.median(spec_pop)),  # floor
)
spec_fit, spec_cov = curve_fit(lorentzian, spec_freqs, spec_pop, p0=guess)
f01_fit, height_fit, hwhm_fit, floor_fit = spec_fit
f01_sigma = float(np.sqrt(np.diag(spec_cov))[0])

print(f"argmax    : {spec_freqs[spec_pop.argmax()] / 1e9:.6f} GHz  (grid step 0.250 MHz)")
print(f"fitted    : {f01_fit / 1e9:.6f} GHz  +/- {f01_sigma / 1e6:.3f} MHz")
print(f"true      : {DEVICE['q0_f01'] / 1e9:.6f} GHz")
print(f"error     : {(f01_fit - DEVICE['q0_f01']) / 1e6:+.3f} MHz")
print(f"linewidth : {2 * abs(hwhm_fit) / 1e6:.3f} MHz fitted vs {DEVICE['q0_linewidth'] / 1e6:.3f} MHz true")

# %% [markdown]
r"""
Drawing the fit on top of the data brings out one rule of the plotting API. `GHZ` moved the numbers rather than the tick labels, so the axes the call returns is in gigahertz and everything you add has to arrive in gigahertz too. The fit and the reference lines were computed in hertz, so each gets divided by `1e9` on the way in. The colours come from `LIGHT`, the theme the measurement was drawn with.
"""

# %%
dense = np.linspace(spec_freqs[0], spec_freqs[-1], 800)

ax = result.plot(
    m_spec,
    field=MF.STATE,
    style=Style(markers=True),
    coords={"drive_freq": GHZ},
    value=POPULATION,
    title="f01 from a Lorentzian fit",
)
ax.lines[0].set_label("measured")
ax.plot(dense / 1e9, lorentzian(dense, *spec_fit), color=LIGHT.series[1], label="Lorentzian fit")
ax.axvline(f01_fit / 1e9, color=LIGHT.series[1], linestyle="--", label=f"fit {f01_fit / 1e9:.5f} GHz")
ax.axvline(DEVICE["q0_f01"] / 1e9, color=LIGHT.muted, linestyle=":", label="true f01")
ax.legend(fontsize=8)
plt.show()

# %% [markdown]
r"""
## 3.2 Rabi

You now know where the qubit is, to a fifth of a linewidth. The next question is how much amplitude a 40 ns pulse needs to rotate the state by $\pi$, and the scan that answers it sets the drive to the frequency you just fitted.

A resonant drive rotates the Bloch vector about an axis in the equatorial plane at a rate set by the amplitude. Hold the shape and the duration fixed and the angle turned is proportional to the amplitude. The population after a rotation by $\theta$ is $\sin^2(\theta/2)$, so sweeping amplitude sweeps through $\theta = \pi$ and the first maximum is the pi pulse. The ceiling is 1 here rather than 0.45, because a coherent rotation can put everything in $|1\rangle$ and a saturated transition cannot.
"""

# %% [markdown]
r"""
### Amplitude or duration

Both produce an oscillation and both are used. An amplitude sweep keeps the envelope shape fixed, so the spectral content does not change along the axis, and it is a continuous knob with 14 or 16 bits behind it. A duration sweep changes the shape and is quantised to the sample clock, so at 40 ns the step is a few percent of the answer. Amplitude is the knob you calibrate with; duration is the one you sweep when you are studying the pulse itself.
"""

# %% [markdown]
r"""
### A variable inside a waveform

Two things in the program are new. The pulse is an `IQDrag`, the standard single-qubit envelope on a transmon, a Gaussian on I with its scaled derivative on Q, and Part 1 explains why the derivative is there. And the swept variable goes **inside the waveform**:

```python
program.play(q[0].drive, IQDrag(amplitude=amp, duration=40, sigma=10, beta=0.1))
```

`amp` is a `Variable`, not a number. Every waveform parameter accepts an `Expression`, so the pulse is parametric and the loop binds it. The `.qp` text keeps the variable name, so the file records the sweep rather than 41 hard-coded pulses.
"""

# %%
def p_rabi(bus, env):
    """Rabi oscillation in amplitude: a full pi rotation at DEVICE['q0_a_pi']."""
    return np.sin(np.pi * env["amp"] / (2 * DEVICE["q0_a_pi"])) ** 2


rabi = qp.QProgram(label="rabi_amplitude", description="Amplitude Rabi on q0", schema=schema)
amp = rabi.variable("amp", label="Drive amplitude", units="DAC units")

with rabi.average(shots=200):
    with rabi.sweep(amp, qp.Linspace(0.0, 1.0, 41)):
        rabi.set_frequency(q[0].drive, f01_fit)  # the fitted frequency, not the true one
        rabi.play(q[0].drive, IQDrag(amplitude=amp, duration=40, sigma=10, beta=0.1))
        rabi.sync()
        m_rabi = rabi.measure(q[0].readout, "readout", "weights", fields=(MF.STATE,))

print(qp.dumps(rabi))

# %%
rabi_result = qp.simulate(rabi, model=qp.MockMeasurementModel(p_excited=p_rabi,  seed=17))
rabi_data = rabi_result.get(m_rabi, field=MF.STATE)

rabi_amps = rabi_data.coords["amp"].values
rabi_pop = rabi_data.values
print("dims:", rabi_data.dims, "shape:", rabi_data.shape)
print("highest measured point at amplitude", round(float(rabi_amps[rabi_pop.argmax()]), 4))
print("(a noisy estimate of the pi amplitude; the fit below uses every point)")

# The amplitude axis carries no unit change, so this figure needs no coords= at all.
ax = rabi_result.plot(
    m_rabi,
    field=MF.STATE,
    style=Style(markers=True),
    value=POPULATION,
    title="Amplitude Rabi on q0",
)
ax.lines[0].set_label("measured")
ax.axvline(DEVICE["q0_a_pi"], color=LIGHT.muted, linestyle=":", label="true pi amplitude")
ax.legend(fontsize=8)
plt.show()

# %% [markdown]
r"""
### Fitting the pi amplitude

The curve is

$$P(a) = P_0 + C \sin^2\!\left(\frac{\pi a}{2 a_\pi}\right)$$

so $a_\pi$ is the amplitude at the first maximum. Fitting for it directly, rather than fitting a generic sinusoid and converting afterwards, means `curve_fit` reports the uncertainty on the number you actually want. Write the model in terms of the calibration parameter every time.

$C$ is the readout contrast and $P_0$ the floor, and neither is a nuisance parameter. The floor sits above zero because the qubit is not perfectly cold and because the classifier sometimes calls a $|0\rangle$ a $|1\rangle$, and the contrast falls below one for the same reasons in reverse, plus whatever relaxes during the readout window. A rising floor means the fridge or the classifier is drifting. A collapsed contrast usually means the readout tone moved, not the qubit.
"""

# %% [markdown]
r"""
### Amplifying the error

This fit is only a first pass. The precision on $a_\pi$ is limited by how sharply the curve turns over at its maximum, and a $\sin^2$ is flat there. Play the pi pulse an odd number of times, say 21, and sweep the amplitude again: an error $\epsilon$ per pulse becomes $21\epsilon$ in the measured angle, so the same scan resolves the amplitude 21 times better.
"""

# %%
def rabi_model(a, a_pi, contrast, floor):
    """Rabi in amplitude, parameterised by the pi amplitude itself."""
    return floor + contrast * np.sin(np.pi * a / (2 * a_pi)) ** 2


rabi_fit, rabi_cov = curve_fit(
    rabi_model,
    rabi_amps,
    rabi_pop,
    p0=(rabi_amps[rabi_pop.argmax()], rabi_pop.max() - rabi_pop.min(), rabi_pop.min()),
)
a_pi_fit, contrast_fit, floor_fit = rabi_fit
a_pi_sigma = float(np.sqrt(np.diag(rabi_cov))[0])

print(f"a_pi fitted : {a_pi_fit:.4f} +/- {a_pi_sigma:.4f}")
print(f"a_pi true   : {DEVICE['q0_a_pi']:.4f}")
print(f"error       : {100 * (a_pi_fit - DEVICE['q0_a_pi']) / DEVICE['q0_a_pi']:+.2f}%")
print(f"contrast    : {contrast_fit:.3f}   floor: {floor_fit:.3f}")

# %%
dense_amp = np.linspace(rabi_amps[0], rabi_amps[-1], 400)

ax = rabi_result.plot(
    m_rabi,
    field=MF.STATE,
    style=Style(markers=True),
    value=POPULATION,
    title="Pi amplitude from a sin^2 fit",
)
ax.lines[0].set_label("measured")
ax.plot(dense_amp, rabi_model(dense_amp, *rabi_fit), color=LIGHT.series[1], label="sin^2 fit")
ax.axvline(a_pi_fit, color=LIGHT.series[1], linestyle="--", label=f"pi at {a_pi_fit:.4f}")
ax.axvline(a_pi_fit / 2, color=LIGHT.series[3], linestyle="--", label=f"pi/2 at {a_pi_fit / 2:.4f}")
ax.axvline(DEVICE["q0_a_pi"], color=LIGHT.muted, linestyle=":", label="true pi amplitude")
ax.legend(fontsize=8)
plt.show()

# %% [markdown]
r"""
### The calibrated pulses

A calibrated gate, in this stack, is a waveform object with numbers in it.

`PI_PULSE` flips the qubit. `X90_PULSE` takes it to the equator and is the workhorse of Part 4, where Ramsey needs two and the echo needs two with a pi pulse between. Both are plain `IQDrag` instances, so they compare by structure and a calibration set is diffable. The amplitude is rounded to four decimals, already finer than the 0.002 the fit knows it to.

Halving `a_pi` for the x90 assumes the response is exactly $\sin^2$. On this simulated chip it is, by construction. On a real one the DAC and the amplifier chain are not perfectly linear, and a shorter effective rotation samples the envelope differently. Exercise 3.1 measures the pi/2 amplitude instead.
"""

# %% [markdown]
r"""
### Drawing both pulses

An `IQWaveform` draws itself on two stacked panels, one per quadrature, and `plot()` hands back that `(I, Q)` pair. Give the pair to a second call as `target=` and both pulses land on the same panels. The second call takes a rotated palette, because the theme hands out its colours in order and would otherwise draw the x90 in the pi pulse's hues.
"""

# %%
PI_PULSE = IQDrag(amplitude=round(float(a_pi_fit), 4), duration=40, sigma=10, beta=0.1)
X90_PULSE = IQDrag(amplitude=round(float(a_pi_fit) / 2, 4), duration=40, sigma=10, beta=0.1)

print("pi  :", PI_PULSE.amplitude, "over", PI_PULSE.get_duration(), "ns")
print("x90 :", X90_PULSE.amplitude, "over", X90_PULSE.get_duration(), "ns")
print("structural equality:", PI_PULSE == IQDrag(PI_PULSE.amplitude, 40, 10, 0.1))
print("a different beta is a different pulse:", PI_PULSE == IQDrag(PI_PULSE.amplitude, 40, 10, 0.2))

ax_i, ax_q = PI_PULSE.plot()
rotated = Style(theme=replace(LIGHT, series=LIGHT.series[2:] + LIGHT.series[:2]))
X90_PULSE.plot(target=(ax_i, ax_q), style=rotated)

for panel in (ax_i, ax_q):
    for line, name in zip(panel.lines, ("pi", "x90"), strict=True):
        line.set_label(name)
    panel.legend(fontsize=8)
ax_i.set_title("The two calibrated drive pulses", loc="left", fontsize=10, pad=6)
plt.show()

# %% [markdown]
r"""
### 🧩 Exercise 3.1

Fit the x90 amplitude rather than halving the pi amplitude. Refit **only the rising branch** of the Rabi curve (everything up to the maximum) with the model written in terms of $a_{90}$:

$$P(a) = P_0 + C \sin^2\!\left(\frac{\pi a}{4 a_{90}}\right)$$

At $a = a_{90}$ the sine argument is $\pi/4$ and the population is halfway up, the definition of a $\pi/2$ rotation.

Print the fitted $a_{90}$, the halved $a_\pi$, and the true $a_\pi / 2$ from `DEVICE`. You have `rabi_amps`, `rabi_pop`, `a_pi_fit`, `contrast_fit`, and `floor_fit` in scope. On a real drive line the assumed number and the measured one can differ by percent.
"""

# %% solution
rising = slice(0, int(rabi_pop.argmax()) + 1)  # up to and including the maximum


def x90_model(a, a_90, contrast, floor):
    """The same physics as rabi_model, parameterised by the pi/2 amplitude."""
    return floor + contrast * np.sin(np.pi * a / (4 * a_90)) ** 2


x90_fit, x90_cov = curve_fit(
    x90_model,
    rabi_amps[rising],
    rabi_pop[rising],
    p0=(a_pi_fit / 2, contrast_fit, floor_fit),
)
a_90_fit = float(x90_fit[0])
a_90_true = DEVICE["q0_a_pi"] / 2

print(f"points used   : {len(rabi_amps[rising])} of {len(rabi_amps)}")
print(f"a_90 fitted   : {a_90_fit:.4f} +/- {float(np.sqrt(np.diag(x90_cov))[0]):.4f}")
print(f"a_pi_fit / 2  : {a_pi_fit / 2:.4f}")
print(f"true a_pi / 2 : {a_90_true:.4f}")
print(f"error vs true : {100 * (a_90_fit - a_90_true) / a_90_true:+.2f}%")

# %% stub
# TODO: fit the pi/2 amplitude from the rising branch of the Rabi curve.
# 1) rising = slice(0, int(rabi_pop.argmax()) + 1)
# 2) def x90_model(a, a_90, contrast, floor): return floor + contrast * sin(pi * a / (4 * a_90))**2
# 3) curve_fit(x90_model, rabi_amps[rising], rabi_pop[rising], p0=(a_pi_fit / 2, contrast_fit, floor_fit))
# 4) print the fitted a_90, a_pi_fit / 2, and DEVICE["q0_a_pi"] / 2 side by side.

# %% [markdown]
r"""
## 3.3 The calibration seam

The Rabi program has `IQDrag(amplitude=amp, ...)` baked into it, and that was right, because the pulse shape *is* the experiment. But every program after it wants "the pi pulse", whatever its current amplitude is. Inline 0.6176 in each one and recalibrating means editing every file, while an old file silently claims a calibration it never had.

QProgram splits the two. Where a waveform is expected you may write a **string alias**, leaving a hole in the program:

```python
program.play(q[0].drive, "pi")
```

The alias survives serialization, so the `.qp` file says `play q[0].drive "pi"`. Filling the hole is a separate step, `program.with_waveforms(...)`, which returns a new program with the names resolved and leaves the original untouched.

The reference platform never looks at a waveform, so an unbound alias costs nothing there, and every `measure` in this notebook can name `"readout"` and `"weights"` because of it. A real platform has to turn the name into samples, so off the simulator the binding step is not optional.
"""

# %%
seq = qp.QProgram(label="pi_then_read", description="Flip q0 and read it out", schema=schema)

with seq.average(shots=200):
    seq.play(q[0].drive, "pi")
    seq.sync()
    m_seq = seq.measure(q[0].readout, "readout", "weights", fields=(MF.STATE,))

print(qp.dumps(seq))

# %% [markdown]
r"""
A `WaveformLibrary` is where the numbers live. It resolves a name **per bus**, in three tiers.

| Tier | How you register it | Matches |
|---|---|---|
| exact | `element=`, `idx=`, `kind=` | one bus |
| family | `element=`, `kind=` | every index of that element and kind |
| global | no keywords | every bus |

Different parts of a calibration have different scopes, and a plain dictionary flattens them into one namespace. Drive pulses go in the exact tier, because `q[0]` and `q[1]` never share a pi amplitude. Readout pulses are often a family default, since a chip's resonators usually take the same shape at the same power. Integration weights are frequently global. Section 5.7 returns to this when the library has to move to another rack.
"""

# %%
library = qp.WaveformLibrary()
library.set("pi", PI_PULSE, element="q", idx=0, kind="drive")  # exact: this qubit only
library.set("x90", X90_PULSE, element="q", idx=0, kind="drive")
library.set("readout", READOUT_PULSE, element="q", kind="readout")  # family: any q readout
library.set("weights", WEIGHTS)  # global

bound = seq.with_waveforms(library)

print(qp.dumps(bound))
print("bound body differs from the original:", seq.body != bound.body)

# %% [markdown]
r"""
One name, three buses, and the tiers decide what each one gets. Give the neighbour its own exact entry and watch `"pi"` resolve to two different amplitudes in the same program.
"""

# %%
library.set("pi", IQDrag(amplitude=0.55, duration=40, sigma=10, beta=0.1),
            element="q", idx=1, kind="drive")  # exact: a standing calibration, not measured here

three = qp.QProgram(label="three_buses", schema=schema)
for i in (0, 1, 2):
    three.play(q[i].drive, "pi")
    three.measure(q[i].readout, "readout", "weights", fields=(MF.STATE,))

for line in qp.dumps(three.with_waveforms(library)).splitlines():
    if line.strip().startswith(("play", "measure")):
        print(line.strip()[:98])

# %% [markdown]
r"""
`q[0]` and `q[1]` each have an exact entry, so the same alias becomes two different pulses, while all three readouts come from the one family entry. `q[2]` has no `pi` at any tier, so the alias survives the bind as the string it was and the complaint comes from the platform that needs samples.
"""

# %% [markdown]
r"""
Binding costs you something. The `measure` line now carries two full `IQPair` constructors. An aliased file is short and reviewable but means nothing without its library. A bound file is self-contained but unreadable and out of date the moment you recalibrate.

The library has its own text format, `.wfl`, kept outside the `.qp` on purpose. The program is the experiment you designed. The library is the state of the fridge when you ran it. The two change at different rates, and a lab that keeps them in one file cannot tell whether two runs were the same experiment.

Below, the same program binds to a stale library and to the current one, so one unchanged file on disk gives two different pulses.
"""

# %%
print(library.dumps())

stale = qp.WaveformLibrary()
stale.set("pi", IQDrag(amplitude=0.50, duration=40, sigma=10, beta=0.1), element="q", idx=0, kind="drive")


def play_line(program):
    """Pull the single `play` statement out of a program's .qp text."""
    return next(line.strip() for line in qp.dumps(program).splitlines() if line.strip().startswith("play"))


print("bound to the stale library  :", play_line(seq.with_waveforms(stale)))
print("bound to the current library:", play_line(bound))
print("the program on disk         :", play_line(seq))

# %% [markdown]
r"""
## 3.4 The flux arc

A flux-tunable transmon has a third line. A DC bias threads flux through a SQUID loop on the chip and moves `f01`. The loop's Josephson energy follows a cosine of that flux and the transmon frequency follows the square root of the energy, so the curve you measure is a square root of a cosine:

$$f_{01}(V) = f_{\max} \sqrt{\left| \cos \frac{\pi (V - V_0)}{V_\Phi} \right|}$$

Three numbers in it are yours to measure. Your DAC puts out volts, not flux quanta, and they reach the loop through a mutual inductance nobody wrote down, so $V_\Phi$, the bias interval that threads one flux quantum, comes out of a fit. $V_0$ is the bias where the loop sees zero flux, and it is not zero volts, because the fridge has an ambient field and the neighbouring flux lines couple into this loop too. It moves with every cooldown, so it is measured rather than looked up.

$V_0$ is the flat top of the arc and the number you want. Park the qubit there and first-order flux noise stops moving its frequency, so $T_2^*$ is at its maximum. Every coherence number in Part 4 was measured at $V_0$.
"""

# %% [markdown]
r"""
### Two changes to the program

You find $V_0$ by repeating the spectroscopy of 3.1 at a series of biases, which makes the scan two dimensional. Bias on the outer loop, drive frequency on the inner one.

`BusSchema.flux_tunable_transmon()` adds `q[i].flux`, a **single**-channel bus with no ADC. Single channel means single-channel waveforms, `Square` rather than `IQPair`, and the builder raises if you try it the other way.

`set_offset(bus, value)` writes a DC level rather than playing a pulse. The value is the swept variable, so the outer loop is a sequence of DC writes.
"""

# %% [markdown]
r"""
### The other presets

Six presets ship. `transmon`, `flux_tunable_transmon`, and `fluxonium`, each with a `_coupled` variant that adds an element `c` for the tunable couplers. A coupler is indexed by the pair it sits between, so `c[0, 1].flux` is one bus. When none of the six fits, `add_element` on a bare `BusSchema()` registers an element at run time, at the cost of the typed accessors.
"""

# %%
flux_schema = BusSchema.flux_tunable_transmon()
qf = flux_schema.q

print("flux bus:", qf[0].flux, "channel:", qf[0].flux.channel, "acquires:", qf[0].flux.acquires)

coupled = BusSchema.flux_tunable_transmon_coupled()
print("coupler bus:", coupled.c[0, 1].flux, "channel:", coupled.c[0, 1].flux.channel)


def f01_of_bias(bias):
    """Where the qubit sits at a given flux bias. Maximum at DEVICE['flux_offset']."""
    phase = np.pi * (bias - DEVICE["flux_offset"]) / DEVICE["flux_period"]
    return DEVICE["q0_f01"] * np.sqrt(np.abs(np.cos(phase)))


POWER_BROADENED = 20e6  # Hz FWHM: this scan drives hard, so the line is much wider than 2 MHz


def p_arc(bus, env):
    """Spectroscopy peak that follows the arc as the bias steps."""
    hwhm = POWER_BROADENED / 2
    return 0.45 / (1.0 + ((env["arc_freq"] - f01_of_bias(env["bias"])) / hwhm) ** 2)


for bias_v in (-0.15, 0.05, 0.25):
    print(f"bias {bias_v:+.2f} V -> f01 {f01_of_bias(bias_v) / 1e9:.4f} GHz")

# %% [markdown]
r"""
### A survey scan

A flux arc is a survey, and the grid below is coarse enough to step straight over a 2 MHz line. The model uses a power-broadened width for that reason. You drive a survey hard on purpose so the peak comes out wider than your grid, find the ridge to within a step or two, then go back with a narrow low-power scan at the one bias you care about.

Shots drop for the same reason. A two-dimensional map has to show a ridge, not measure a population to three digits.
"""

# %%
arc = qp.QProgram(label="flux_arc", description="f01 against flux bias on q0", schema=flux_schema)
bias = arc.variable("bias", label="Flux bias", units="V")
arc_freq = arc.variable("arc_freq", label="Drive frequency", units="Hz")

with arc.average(shots=50):
    with arc.sweep(bias, qp.Linspace(-0.15, 0.25, 25)):
        arc.set_offset(qf[0].flux, bias)  # a DC write, not a pulse
        with arc.sweep(arc_freq, qp.Linspace(4.30e9, 4.90e9, 61)):
            arc.set_frequency(qf[0].drive, arc_freq)
            arc.play(qf[0].drive, SATURATION)
            arc.sync()
            m_arc = arc.measure(qf[0].readout, "readout", "weights", fields=(MF.STATE,))

print(qp.dumps(arc))

# %%
arc_result = qp.simulate(arc, model=qp.MockMeasurementModel(p_excited=p_arc,  seed=23))
arc_data = arc_result.get(m_arc, field=MF.STATE)

biases = arc_data.coords["bias"].values
arc_freqs = arc_data.coords["arc_freq"].values
arc_grid = arc_data.values
ridge = arc_freqs[arc_grid.argmax(axis=1)]  # brightest frequency at each bias

print("dims:", arc_data.dims, "shape:", arc_data.shape)
print("bias step:", round(float(biases[1] - biases[0]), 4), "V")
print("frequency step:", round(float(arc_freqs[1] - arc_freqs[0]) / 1e6, 2), "MHz")
print("ridge (GHz):", np.round(ridge / 1e9, 3))

# %% [markdown]
r"""
Two nested sweeps mean two plot dimensions, so `plot` infers a heatmap and colours it by the population. Left alone it would put the inner sweep along x, matching the loop nesting. `x=` overrides that, so the bias runs along the bottom the way a bring-up log draws it. The ridge and the sweet-spot line go on afterwards, in the units the figure is drawn in.
"""

# %%
ax = arc_result.plot(
    m_arc,
    field=MF.STATE,
    x="bias",  # bias along the bottom, frequency up the side
    coords={"arc_freq": GHZ},
    value=POPULATION,  # this labels the colour bar rather than an axis
    title="Flux arc: f01 against bias",
)
# The theme's ramp is blue, so the two annotations take warm slots from the same palette and
# stay legible over the map and inside the legend box.
ax.plot(biases, ridge / 1e9, ".", color=LIGHT.series[1], markersize=5, label="brightest point")
ax.axvline(DEVICE["flux_offset"], color=LIGHT.series[3], linestyle="--", linewidth=1.2, label="true sweet spot")
ax.legend(fontsize=8, loc="lower center")
plt.show()

# %% [markdown]
r"""
### Fitting the arc

The ridge is quantised to the frequency grid, so no single point in it is better than one step, and the fit still comes out far better than any of its inputs. The ridge carries far more points than the model has parameters, and the curve on each side of the maximum votes on where the middle is, so the symmetry pins $V_0$ much more tightly than the bias step suggests.

The arc is flat at the top and steep at the edges, so a bad guess for the period can land the fit a full period away. Start $V_0$ at the brightest column and $V_\Phi$ at twice the bias span you scanned.
"""

# %%
def arc_model(bias_v, f_max, offset, period):
    """The transmon flux arc: cosine under a square root."""
    return f_max * np.sqrt(np.abs(np.cos(np.pi * (bias_v - offset) / period)))


arc_fit, arc_cov = curve_fit(
    arc_model,
    biases,
    ridge,
    p0=(ridge.max(), float(biases[ridge.argmax()]), 2 * (biases[-1] - biases[0])),
)
f_max_fit, offset_fit, period_fit = arc_fit
arc_sigma = np.sqrt(np.diag(arc_cov))

print(f"f_max  fitted: {f_max_fit / 1e9:.6f} GHz +/- {arc_sigma[0] / 1e6:.3f} MHz")
print(f"f_max  true  : {DEVICE['q0_f01'] / 1e9:.6f} GHz")
print(f"offset fitted: {offset_fit:+.4f} V +/- {arc_sigma[1]:.4f} V")
print(f"offset true  : {DEVICE['flux_offset']:+.4f} V   (bias step was 0.0167 V)")
print(f"period fitted: {period_fit:.4f} V +/- {arc_sigma[2]:.4f} V")
print(f"period true  : {DEVICE['flux_period']:.4f} V")

# %% [markdown]
r"""
The fitted arc is the one figure here still built by hand. A result knows its dimensions, its coordinates, and the units on them, so it can draw itself and label both axes. A curve computed from three fitted parameters is two numpy arrays and nothing else.
"""

# %%
dense_bias = np.linspace(biases[0], biases[-1], 400)

# No result to ask, so the figure, the size, and both axis labels are all typed out here.
fig, ax = plt.subplots(figsize=DEFAULT_SIZE)
ax.plot(biases, ridge / 1e9, ".", color=LIGHT.series[0], label="ridge from the map")
ax.plot(dense_bias, arc_model(dense_bias, *arc_fit) / 1e9, color=LIGHT.series[1], label="arc fit")
ax.axvline(offset_fit, color=LIGHT.series[1], linestyle="--", label=f"sweet spot {offset_fit:+.4f} V")
ax.axvline(DEVICE["flux_offset"], color=LIGHT.muted, linestyle=":", label="true sweet spot")
ax.set_xlabel("Flux bias (V)")
ax.set_ylabel("f01 (GHz)")
ax.set_title("The fitted flux arc", loc="left", fontsize=10, pad=6)
ax.legend(fontsize=8)
plt.show()

# %% [markdown]
r"""
### Parking the qubit

The arc is a calibration in both directions. You measured $f_{01}$ against bias, and the useful form is bias against $f_{01}$. Inverting the model gives

$$V = V_0 + \frac{V_\Phi}{\pi} \arccos\!\left( \left( \frac{f_{\text{target}}}{f_{\max}} \right)^{2} \right)$$

and the cell below solves it for 4.70 GHz, then grades itself against `f01_of_bias`, the true device.

`arccos` returns one value, but the arc is symmetric about the sweet spot, so two biases give any frequency below $f_{\max}$ and both are printed. Which side you want depends on the neighbours and couplers on the chip, since half the job of choosing a parking spot is staying away from them.
"""

# %%
f_target = 4.70e9
step = (period_fit / np.pi) * np.arccos((f_target / f_max_fit) ** 2)

for side, bias_solution in (("above the sweet spot", offset_fit + step), ("below", offset_fit - step)):
    print(f"{side:>20}: bias {bias_solution:+.4f} V")
    print(f"{'arc model says':>20}: {arc_model(bias_solution, *arc_fit) / 1e9:.6f} GHz")
    print(f"{'true device gives':>20}: {f01_of_bias(bias_solution) / 1e9:.6f} GHz")
    print(f"{'miss':>20}: {(f01_of_bias(bias_solution) - f_target) / 1e6:+.3f} MHz")

print(f"\ntarget was {f_target / 1e9:.3f} GHz; the two solutions are mirrored about the sweet spot.")

# %% [markdown]
r"""
### Two loops

The two `for` loops in the flux arc program are written identically, and on a real rack they are nothing alike. The inner one retunes a microwave source and fires a pulse, microseconds per step, and belongs inside the sequencer. The outer one writes a DC voltage to a bias source that settles in milliseconds, often a separate instrument with no sequencer at all, so that loop has to run host-side.

You never said which was which, and you should not have to. Which loop can run in real time is a property of the rack, not of the experiment. Part 5 hands this program to a platform descriptor that reports where each loop landed.
"""

# %% [markdown]
r"""
## Recap

- **Two-tone spectroscopy** found `f01` to well under a linewidth, by parking on the resonator and watching it shift by $2\chi$. The mechanism was `fields=(MF.STATE,)`, so averaging returned a population rather than a shot.
- **Rabi in amplitude** turned that frequency into a pi amplitude, with a `Variable` living inside a waveform constructor. `IQDrag(amplitude=amp, ...)` is one parametric pulse, not 41 literal ones.
- **Fit for the parameter you want.** `a_pi` and `f01` came with their own uncertainties because the models were written in terms of them.
- **Every measured figure came from `result.plot`.** `label=` and `units=` named the x axis, and `Quantity` moved hertz to gigahertz without touching the array.
- **The calibrated pulses are objects.** `PI_PULSE` and `X90_PULSE` are `IQDrag` instances that compare by structure.
- **The calibration seam** is the string alias plus `with_waveforms`. The program says `play "pi"`, and the `WaveformLibrary` carries the current numbers in its own `.wfl` file.
- **The flux arc** put the sweet spot well inside a bias step, and inverting the fit parks the qubit anywhere on the curve. Its outer loop steps a slow DC source, and the program never said so.
"""

# %% [markdown]
r"""
## Next

**Part 4, coherence and feedback.** T1, Ramsey, and echo, built out of reusable pulse fragments, then single-shot readout and active reset with a real conditional on a measured state.
"""
