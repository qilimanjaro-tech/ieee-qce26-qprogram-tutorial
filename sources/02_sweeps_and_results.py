# %% [markdown]
r"""
# 02 · Sweeps, averaging, and what comes back

Part 1 built programs that do one thing, once. Every calibration you will ever run is a loop: step a
knob, measure, step it again, and look at the shape of what came back. Three pieces turn a sequence
into an experiment. A variable is the hole in the program where the knob goes. A sweep source says
how that variable moves, in a form a compiler can read. And `average(shots)` repeats the whole thing
and hands you a mean instead of one sample.

Then the other half, the data. `qp.simulate` gives back an `xarray.DataArray` whose dimensions carry
the names you gave your variables, and whose axes, when you declared a label and a unit alongside
those names, know how to draw themselves.

Two experiments carry it. Resonator spectroscopy finds the readout resonator, the first measurement
anyone makes on a new chip. Punchout is the 2D scan that shows the resonator sliding as you push
more power at it, and it tells you what power to read out at. About 35 minutes.
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
import numpy as np

import qprogram as qp
from qprogram import MeasurementField as MF
from qprogram.buses import BusSchema
from qprogram.plotting import Quantity, Style
from qprogram.waveforms import Square

schema = BusSchema.transmon()
q = schema.q

print("readout bus:", q[0].readout, "| channel:", q[0].readout.channel,
      "| has ADC:", q[0].readout.acquires)

# %% [markdown]
r"""
## The device under test

Every notebook in this tutorial talks to the same simulated chip, and every notebook writes its
true parameters down in one place. The numbers are in plain sight, and the job of each experiment
is to recover them from data. If your fit disagrees with `DEVICE`, either the fit is wrong or you
learned something about the analysis.

Part 1 went through how these numbers constrain each other. Part 2 uses three of them. The
resonator frequency `q0_fr` is the answer this notebook is looking for. The linewidth `q0_kappa`
sets how finely you have to step to see it: 1.5 MHz wide means a 200 kHz grid puts seven or eight
points across the dip, and a 2 MHz grid steps over it. And the dispersive shift `q0_chi` gives the
second experiment its point, because it is the part of the resonator frequency that
depends on the qubit, and therefore the part that goes away when you push too hard.
"""

# %%
DEVICE = {
    # qubit 0
    "q0_f01": 4.85e9,        # Hz, at the flux sweet spot
    "q0_fr": 7.20e9,         # Hz, readout resonator
    "q0_kappa": 1.5e6,       # Hz, resonator linewidth (FWHM)
    "q0_chi": -1.8e6,        # Hz, dispersive shift
    "q0_a_pi": 0.62,         # drive amplitude of a pi pulse (DAC units)
    "q0_T1": 18_000,         # ns
    "q0_T2star": 9_000,      # ns
    "q0_T2echo": 16_000,     # ns
    "q0_linewidth": 2.0e6,   # Hz, spectroscopy FWHM at low power
    # qubit 1
    "q1_f01": 5.12e9,
    "q1_fr": 7.35e9,
    "q1_a_pi": 0.55,
    "q1_T1": 15_000,
}

print(f"resonator        {DEVICE['q0_fr'] / 1e9:.3f} GHz")
print(f"linewidth kappa  {DEVICE['q0_kappa'] / 1e6:.2f} MHz")
print(f"dispersive shift {DEVICE['q0_chi'] / 1e6:+.2f} MHz")

# %% [markdown]
r"""
## 2.1 A variable is a hole in the program

You do not know where the resonator is. You know roughly, because a designer drew it and a
simulator predicted 7.2 GHz, but a resonator's frequency depends on the physical length of a
patterned line and on the kinetic inductance of the film that got sputtered that day, and neither
comes back from the fab to better than a percent or two. One percent of 7.2 GHz is 72 MHz, against a
resonance 1.5 MHz wide. So you cannot write `set_frequency(readout, 7.2e9)` and be done. You have to
write the program once with a hole in it and let something else decide what goes in the hole.

`program.variable(id, label=..., units=...)` declares that hole. The id is the only part that
matters to the machine. It becomes the identifier in the `.qp` file and the dimension name in the
result. `label` and `units` are for people, and they travel further than decoration would. Both ride
out to the coordinate in the result and label the axes of every figure drawn from it, so those two
strings are the difference between a plot that names itself and one you annotate by hand. Section
2.6 is where you see them arrive.

Arithmetic on a variable builds an expression tree. Nothing is computed at that point.
`freq - 7.2e9` is a `BinaryOp` node holding a variable and a constant, and you can print it, walk
it, serialize it, or hand it to any operation that takes a number.
"""

# %%
scratch = qp.QProgram(label="expressions", schema=schema)
freq = scratch.variable("freq", label="Readout frequency", units="Hz")
amp = scratch.variable("amp", label="Readout amplitude", units="DAC units")

# Detuning from the resonator, in half-linewidths. This is data, not a number.
detuning = (freq - DEVICE["q0_fr"]) / (DEVICE["q0_kappa"] / 2)

print("the expression:  ", detuning)
print("free variables:  ", sorted(v.id for v in detuning.variables()))
print("value of freq:   ", freq.value)

# %% [markdown]
r"""
### Where the value comes from

A variable holds one value at a time, and it starts out as `UNASSIGNED`. The loop that binds it
decides the value. On each iteration the runtime calls `set_value`, every expression built on that
variable re-evaluates, and the operations inside the loop see the new number. Nothing is passed as
an argument anywhere.

Two ways to read a tree. `evaluate()` returns `UNASSIGNED` if anything in it is unbound, so code
that inspects a program before it has run never has to guard. `evaluate_or_raise()` insists on a
number and raises `UnassignedVariableError` naming what is missing. The interpreter calls that one
on every operation as it executes, because by then there is no value it is allowed to skip.
"""

# %%
print("unbound:", detuning.evaluate())   # UNASSIGNED propagates up through the whole tree

freq.set_value(7.2015e9)                 # the loop does exactly this, once per iteration
print("bound:  ", detuning.evaluate())   # 1.5 MHz above resonance is 2.0 half-linewidths
freq.reset()

try:
    detuning.evaluate_or_raise()
except qp.UnassignedVariableError as err:
    print("evaluate_or_raise:", sorted(v.id for v in err.free_variables), "still unbound")

# A waveform parameter is one more slot an expression fits into.
tone = Square(amplitude=amp / 2, duration=8)
amp.set_value(0.8)
print("envelope:", tone.envelope())      # half of 0.8, eight samples of it
amp.reset()

# %% [markdown]
r"""
## 2.2 Sweep sources: how the variable moves

`program.sweep(variable, source)` is the only loop in QProgram. There is no separate `for_loop` and
no `while`. What changes between a frequency ramp and a table of calibrated phases is the
**source**, and a source is a small immutable value object, the sweep analogue of a waveform.

| Source | Kind | Reach for it when |
|---|---|---|
| `qp.Range(start, stop, step)` | linear | you know the spacing |
| `qp.Linspace(start, stop, num)` | linear | you know the point count |
| `qp.Values(seq)` | arbitrary | you have a list: calibrated values, a measured table |
| `qp.Logspace(start, stop, num)` | arbitrary | powers and decay times, anything spanning decades |
| `qp.File(path)` | arbitrary | the list lives in a `.npy` file next to the program |
| `qp.Repeat(src, times)` | arbitrary | the same sweep back to back |
| `qp.Rotate(src, by)` | arbitrary | the same sweep, cyclically shifted |
| `qp.Concat([src, src])` | arbitrary | several sweeps end to end |

One thing to fix in your head now, because it will bite you otherwise. **`Range` is `start + step *
i`, and it holds `round((stop - start) / step) + 1` points.** It lands on `stop` only when the step
divides `stop - start` evenly. Otherwise the last point falls short of `stop`, or steps past it.
Reach for `Linspace` when the last point has to land on `stop` exactly.
"""

# %%
print("Range(0, 10, 2)   ->", qp.Range(0, 10, 2).values())    # 6 points, landing on 10
print("Range(0, 10, 3)   ->", qp.Range(0, 10, 3).values())    # 4 points, stopping short at 9
print("Range(0, 1, 0.6)  ->", qp.Range(0, 1, 0.6).values())   # 3 points, overshooting to 1.2
print("Linspace(0, 10, 5)->", qp.Linspace(0, 10, 5).values())
print("Values([...])     ->", qp.Values([7.19e9, 7.20e9, 7.21e9]).values())

span = qp.Range(7.19e9, 7.21e9, 0.2e6)
print("a 20 MHz span at 200 kHz steps:", span.length(), "points")   # 101, not 100

with scratch.sweep(freq).from_range(7.19e9, 7.21e9, 0.2e6):   # no source class named
    pass

print("fluent: ", qp.dumps(scratch).splitlines()[-1].strip())
print("object: for freq in", span)

# %% [markdown]
r"""
### Linear or arbitrary, and why a compiler cares

Every source declares a `KIND`, either `"linear"` or `"arbitrary"`, and a capability `TOKEN`.

`"linear"` is a promise about the values. Point $i$ is exactly `start + step * i`, so a sequencer
can run the loop out of a hardware register, incrementing a frequency word per iteration, with
nothing uploaded and no control computer in the loop. `Range` and `Linspace` make that promise.

`"arbitrary"` means the values are a list, and a list has to reach the instrument somehow. The
platform either uploads it as a table, which costs sequencer memory, or steps it from the host, one
round trip per point. Both of those are slower than a register, and how much slower is a property of
the rack rather than of the program. Part 5 takes a real capability descriptor and tells you which
of the two you landed in.

`Values` is arbitrary **even when the numbers you pass are evenly spaced**. The source carries the
claim, and a list of floats proves nothing about its own regularity. If your sweep
really is a ramp, say `Range` or `Linspace` and let the compiler use it.

The tokens are how a platform declines: a rack whose sequencer cannot do log sweeps refuses
`sweep.logspace`, and refuses it inside a combinator too, because combinators union their children's
tokens.
"""

# %%
sources = [
    qp.Range(7.19e9, 7.21e9, 0.2e6),
    qp.Linspace(0.0, 1.0, 21),
    qp.Values([0.0, 0.05, 0.10, 0.15]),   # an even ramp, and still arbitrary
    qp.Logspace(0.01, 1.0, 21),
]
for src in sources:
    print(f"{src!r:60} {src.KIND:10} {src.length():4d} points  {sorted(src.tokens())}")

# %% [markdown]
r"""
### Combinators

Three sources take another source and rearrange it. They exist because the patterns show up
constantly in the lab. `Repeat` runs a scan twice back to back so you can overlay the halves and see
whether the chip moved under you, the cheapest drift check there is. `Rotate` shifts a
phase list so the reference point lands somewhere else without rewriting the list. `Concat` glues a
coarse survey to a fine scan, so one program covers a wide band at low resolution and the
interesting 5 MHz at high resolution.

All three are arbitrary, and all three report their child's tokens alongside their own.
"""

# %%
base = qp.Values([0.0, 0.5, 1.0])
print("Repeat(base, 2) ", qp.Repeat(base, 2).values())
print("Rotate(base, 1) ", qp.Rotate(base, 1).values())
print("Concat([...])   ", qp.Concat([base, qp.Linspace(2.0, 3.0, 3)]).values())

# The tokens travel upward, so a platform without log sweeps also refuses this:
print("Rotate(Logspace(...)) needs:", sorted(qp.Rotate(qp.Logspace(0.01, 1.0, 4), 1).tokens()))

# %% [markdown]
r"""
There is a second spelling for the same loop. `program.sweep(freq).from_range(...)` and its siblings
`.from_linspace(...)`, `.from_logspace(...)`, `.from_values(...)` and `.from_file(...)` build the
same `Sweep` node and write the same `.qp` line as passing a source object, without naming a source
class at the call site. A bare list in the source position works too, and means `Values`.

This part passes source objects throughout, for two reasons. The `KIND` and the capability tokens
are what the rest of the section turns on, and both live on the class. And the combinators reach
further than the fluent form does. `qp.Concat([qp.Rotate(base, by=i) for i in range(4)])` has no
`from_*` equivalent, so a composed source is built as a value and handed in. Recognize both
spellings, because the library's own landing page opens with the fluent one.
"""

# %% [markdown]
r"""
## 2.3 `average(shots)` adds no dimension

A single measurement of a superconducting qubit is noisy, and it is noisy in two unrelated ways that
are worth keeping apart in your head.

The first is the amplifier chain. What comes back from the fridge is a few tens of microwave photons
at 7 GHz, roughly $10^{-19}$ joules, and every stage between the chip and the ADC adds noise to it.
Even a quantum-limited parametric amplifier adds half a photon of vacuum noise because it is not
allowed to do better; a HEMT-only chain adds ten or twenty. That noise lands on the `iq` point and
averaging beats it down.

The second is the qubit. A superposition is not a dim signal, it is a coin. Measure a state that is
half excited and you get a 1 or a 0, never a 0.5, and the spread you see across repetitions is the
projection itself rather than anything the electronics did. That noise lands on the `state` field
and averaging turns it into a population.

Both shrink as $1/\sqrt{N}$, so the same knob fixes both. They differ in where the floor is: the
first can be improved by buying a better amplifier, and the second cannot be improved at all.

`with program.average(shots=N)` is that repetition, and it is the one loop that does **not** show
up as a dimension in the result. `iq` and `raw` come back as means over the shots; `state` comes
back as the excited-state population. You almost always want that, and when you do want the
individual shots there is a trick for it in Part 4.

The shot loop has one job. Same program, same 64 sweep points, one flat response with a lot of
noise on it, four different shot counts.
"""

# %%
def noise_scan(shots):
    """Measure a constant signal 64 times, averaged `shots` deep. Returns the iq array."""
    p = qp.QProgram(label=f"flat_{shots}", schema=schema)
    idx = p.variable("idx")
    with p.average(shots=shots):
        with p.sweep(idx, qp.Range(0, 63, 1)):
            m = p.measure(q[0].readout, "readout", "weights")
    flat = qp.MockMeasurementModel(response=lambda bus, env: 1 + 0j, noise=0.5, seed=5)
    return qp.simulate(p, model=flat).get(m)


for shots in (1, 4, 64, 256):
    da = noise_scan(shots)
    spread = da.sel(IQ="I").values.std()
    print(f"shots={shots:4d}  dims={da.dims}  shape={da.shape}  std(I)={spread:.4f}")

# %% [markdown]
r"""
The shape never changes. The spread falls as $1/\sqrt{N}$, so halving the noise costs four times the
measurement time. That exchange rate is why shot counts get argued about in group meetings, and it
is worth being blunt about which direction the argument usually goes. Doubling your shots is the
laziest possible improvement and it buys you 1.4x. Fixing the thing that made the signal small in
the first place, a badly placed readout frequency or a lossy cable, routinely buys you 10x. Reach
for shots last.

Averaging does something different to the `state` field. A single shot is classified 0 or 1, so one
shot gives you a bit. Average 500 of them and the same array position holds a population, a number
between 0 and 1. Nothing about the array shape tells you which of the two you are holding. The
shot count decides, and the shot count is not in the result.
"""

# %%
def population_scan(shots):
    """Five repeats of a measurement on a qubit that is excited 30% of the time."""
    p = qp.QProgram(label=f"pop_{shots}", schema=schema)
    rep = p.variable("rep")
    with p.average(shots=shots):
        with p.sweep(rep, qp.Range(0, 4, 1)):
            m = p.measure(q[0].readout, "readout", "weights", fields=(MF.IQ, MF.STATE))
    biased = qp.MockMeasurementModel(
        response=lambda bus, env: 0j, p_excited=lambda bus, env: 0.3, noise=0.0, seed=9
    )
    return qp.simulate(p, model=biased).get(m, field=MF.STATE)


print("shots=1   ->", population_scan(1).values)      # one classified shot per point
print("shots=500 ->", population_scan(500).values)    # the same shape, now a population near 0.3

# %% [markdown]
r"""
## 2.4 The measurement model is the fake fridge

`qp.simulate` runs the program on `ReferencePlatform`, a pure-Python interpreter that ships inside
QProgram. It walks the AST, drives the loops, binds the variables, and asks a **measurement model**
for one sample per shot per `measure`. The model is the only source of numbers.

`MockMeasurementModel(response=..., p_excited=..., noise=..., raw_samples=..., seed=...)` covers
most cases. Your `response(bus, env)` returns one noiseless complex IQ point. `bus` is the bus being
measured, so one model can answer differently for two resonators. `env` is a dict of the currently
bound loop variables, keyed by variable id, plus any platform parameters keyed as
`"bus.parameter"`.

**The simulator is not physics**, and this notebook will say so again. The pulses you play, the
waits, the syncs, the gains you set are all recorded in the AST, validated against the platform, and
then ignored by the interpreter. There is no timing model and no waveform model. When you sweep an
amplitude and watch a dip move, it moved because your `response` function read `env["ro_amp"]` and
did the arithmetic itself.

That sounds like a limitation and it is really a choice about what is under test. A tutorial with a
real Lindblad solver behind it would teach you to trust a simulation. This one puts the two things
you actually carry to a fridge under test instead: the program, which has to say the right thing to
a machine, and the analysis, which has to get the right number out of noisy data. Both of those are
identical here and on hardware. The qubit is the only stand-in.

One consequence of that, and every cell below leans on it. Every `measure` here passes the string
aliases `"readout"` and `"weights"` and never binds them to real waveforms, and the run works
anyway, because the interpreter never looks at a pulse. A real platform does look. It needs samples
to upload, so `program.with_waveforms(library)` has to come first. Part 3 does that binding for
real.

One operation below is new. `set_frequency` and `set_gain` write registers a sequencer owns.
`set_parameter(bus, name, value)` writes something the platform holds as configuration instead, an
attenuator setting or a local oscillator, and platforms expose it host-side only for that reason.
The name is a free string that nothing validates, so a typo becomes a parameter the platform has
never heard of rather than an error at the call site. Its value reaches the measurement model under
the key `"bus.parameter"`, and that is why `env` below carries `q0/readout.attenuation` alongside
the loop variables. `get_parameter` is the read direction, handing back a fresh variable the runtime
fills in.

The write sits above both loops on purpose. One attenuator setting covers the whole scan, so writing
it once outside is both what you mean and what the cheaper program looks like. Part 5 has the tools
that tell you when a write inside a loop has dragged the loop off the sequencer with it.
"""

# %%
seen = []


def peek(bus, env):
    """A response function that records what it was asked, then returns a flat signal."""
    seen.append((str(bus), dict(env)))
    return 1 + 0j


env_probe = qp.QProgram(label="env_probe", schema=schema)
ro_freq = env_probe.variable("ro_freq", units="Hz")
ro_amp = env_probe.variable("ro_amp", units="DAC units")
env_probe.set_parameter(q[0].readout, "attenuation", 30.0)  # above the loops, deliberately
with env_probe.average(shots=2):
    with env_probe.sweep(ro_amp, qp.Values([0.1, 0.4])):
        with env_probe.sweep(ro_freq, qp.Linspace(7.19e9, 7.21e9, 3)):
            env_probe.measure(q[0].readout, "readout", "weights")

# qp.simulate() builds one of these per call and forwards model=, schema= and parameters= into it.
# The platform is spelled out here because section 6.4 works with the object directly.
platform = qp.ReferencePlatform(model=qp.MockMeasurementModel(response=peek))
platform.execute(env_probe)

print("samples requested:", len(seen), "= 2 shots x 2 amplitudes x 3 frequencies")
print("bus:", seen[0][0])
print("env:", seen[0][1])

# %% [markdown]
r"""
## 2.5 Resonator spectroscopy

The first real measurement on a new chip. Send a tone down the feedline, step its frequency across
the band where the readout resonator should be, and record what comes back.

Take a second on the geometry, because it explains the shape of the curve. The resonator is not in
line with the signal path. It hangs off the side of a feedline that runs past it and continues to
the output port. Hence the two names it goes by, hanger and notch. Off resonance the resonator
is invisible and the tone reaches the output untouched, so $|S_{21}| = 1$. On resonance the
resonator absorbs power out of the feedline and dumps it, mostly back into the input and into its
own losses, so less arrives at the output and the trace dips. The dip tells you the frequency; its
width tells you the linewidth $\kappa$; and its **depth** tells you something people often skip
over.

$$ S_{21}(f) = 1 - \frac{0.9}{1 + i\,\delta}, \qquad \delta = \frac{f - f_r}{\kappa / 2} $$

That 0.9 is a loss budget. For a notch resonance the depth is $Q_L/Q_c$, the fraction of the total
loss that goes out through the coupler rather than into the material. A dip 90 percent deep means
nine tenths of the energy leaves the way you want it to, and one tenth is lost to the substrate, the
oxides, and whatever else. Run the numbers: $Q_L = f_r/\kappa = 4800$, so $Q_c = Q_L/0.9 = 5300$ and
$1/Q_i = 1/Q_L - 1/Q_c$ gives $Q_i = 48000$. Overcoupled by a factor of ten, and for readout
that is the right direction, because a photon lost to the substrate carries its information nowhere.

A shallow dip on a real chip is therefore bad news rather than a measurement problem. It means
$Q_i$ has collapsed, and the usual culprits are a warm fridge, a stray photon population, or a
two-level defect that has wandered into the resonator's frequency.

The model carries no amplitude, so this scan has one number in it and the dip sits on the bare
resonator frequency. How hard the feedline is driven moves that answer, and section 2.7 puts the
power axis back. Everything else is the program:

- one variable, `ro_freq`, swept with `Range` over a 20 MHz window at 200 kHz steps,
- `set_frequency` on the readout bus, so the tone follows the variable,
- `measure`, returning the handle you pull data out with,
- 200 shots per point. 101 points x 200 shots is 20200 samples, about a fifth of a second of
  interpreter time.
"""

# %%
def s21(bus, env):
    """Transmission past one resonator: a Lorentzian notch, 90% deep on resonance."""
    detuning = (env["ro_freq"] - DEVICE["q0_fr"]) / (DEVICE["q0_kappa"] / 2)
    return 1.0 - 0.9 / (1.0 + 1j * detuning)


spec = qp.QProgram(
    label="resonator_spectroscopy", description="find the q0 readout resonator", schema=schema
)
ro_freq = spec.variable("ro_freq", label="Readout frequency", units="Hz")

with spec.average(shots=200):
    with spec.sweep(ro_freq, qp.Range(7.19e9, 7.21e9, 0.2e6)):
        spec.set_frequency(q[0].readout, ro_freq)
        m_spec = spec.measure(q[0].readout, "readout", "weights")

print(qp.dumps(spec))

# %%
result = qp.simulate(spec, model=qp.MockMeasurementModel(response=s21, noise=0.02, seed=7))

iq = result.get(m_spec)
freqs = iq.coords["ro_freq"].values
s21_data = iq.sel(IQ="I").values + 1j * iq.sel(IQ="Q").values

print("dims:", iq.dims, "shape:", iq.shape)
print("101 frequencies by 2 quadratures. The 200 shots are gone: average() collapsed them.")
print("first three points:", np.round(s21_data[:3], 3))

# %% [markdown]
r"""
### Reading the numbers off the curve

The picture comes in a moment, and it is worth more with the answer already drawn on it, so take the
two numbers first.

`argmin` is enough for the centre here, with one caveat: it can never be better than your step size.
A 200 kHz grid gives you the resonator to 200 kHz, full stop. Part 3 fits a real curve and does
better than the grid.

The width needs one step of care, and the reason is a mistake people make once. The dip in
$|S_{21}|$ is not a Lorentzian. $S_{21}$ is one minus a complex Lorentzian, and taking the magnitude
of that mixes the real and imaginary parts, so the shape you see is narrower on one side than the
Lorentzian it came from and its half-depth width is not $\kappa$. Subtract the off-resonance
baseline first and square what is left. $|S_{21} - 1|^2$ is a plain Lorentzian in power, and its
full width at half maximum is $\kappa$ exactly. Reading the half-maximum crossings with `np.interp`
interpolates between grid points, which is how the number below lands within 10 kHz on a 200 kHz
grid.
"""

# %%
f_dip = freqs[np.abs(s21_data).argmin()]

baseline = np.mean(np.concatenate([s21_data[:5], s21_data[-5:]]))   # flat away from resonance
lorentzian = np.abs(baseline - s21_data) ** 2
lorentzian = lorentzian / lorentzian.max()

peak = lorentzian.argmax()
left = np.interp(0.5, lorentzian[: peak + 1], freqs[: peak + 1])           # rising edge
right = np.interp(0.5, lorentzian[peak:][::-1], freqs[peak:][::-1])        # falling edge, reversed

print(f"f_r    measured {f_dip / 1e9:.6f} GHz    true {DEVICE['q0_fr'] / 1e9:.6f} GHz")
print(f"kappa  measured {(right - left) / 1e6:.3f} MHz     true {DEVICE['q0_kappa'] / 1e6:.3f} MHz")
print(f"sweep step {(freqs[1] - freqs[0]) / 1e3:.0f} kHz, so f_r is quantised to that")

# %% [markdown]
r"""
### The figure the result already knows how to draw

`result.plot(handle)` reads the array the way `result.get(handle)` reads it and lets the shape
choose the figure. One swept dimension besides `IQ` makes a line, and `channels="magnitude"` takes
the hypotenuse of the two quadratures instead of drawing both. Nothing in the call names the x axis,
because the variable was declared with a label and a unit back when the program was written and both
rode out to the coordinate.

The unit that reached the axis is hertz, and a frequency axis wants gigahertz, so `coords=` restates
it for the figure alone. The restatement is a pair and the library insists on both halves.
`units="GHz"` on its own would relabel numbers it never moved, and `transform=lambda v: v / 1e9` on
its own would leave an axis reading hertz over values near 7.2. Either one alone raises.

That pair has a consequence on the next line. The drawn numbers moved, so everything you hand the
returned `Axes` afterwards is in the figure's units too, and both reference lines below are divided
by `1e9` while `f_dip` itself stays in hertz. `Style(markers=True)` puts a dot at each of
the 101 samples, and on a sweep this coarse the dots are the measurement while the line between them
is the renderer joining them up.
"""

# %%
ax = result.plot(
    m_spec,
    channels="magnitude",
    coords={"ro_freq": Quantity(units="GHz", transform=lambda v: v / 1e9)},
    value=Quantity("Readout magnitude"),
    style=Style(markers=True),
    title="Resonator spectroscopy",
)
ax.axvline(f_dip / 1e9, color="tab:red", lw=1, label=f"argmin at {f_dip / 1e9:.4f} GHz")
ax.axvline(DEVICE["q0_fr"] / 1e9, color="grey", ls=":", label="true $f_r$")
ax.legend(fontsize=8)

# %% [markdown]
r"""
Draw the same measurement again with `channels="phase"` and you get the other half of the story. The
two fail in different ways. Magnitude shows the dip and you look at it first, but it flattens out
when the dip is shallow, which is how an over-coupled resonator often looks. Phase turns by about a
radian either side of the resonance and stays readable there.

The size of the turn is set by the coupling, and you can read it off the same 0.9. In the complex
plane the trace draws a circle of diameter 0.9 that passes through $1$ off resonance and through
$0.1$ on it, so its centre sits at $0.55$ and the largest phase excursion is
$\arcsin(0.45/0.55) = 55$ degrees. A total swing of 110 degrees, or about 60 percent of the $\pi$
that a perfectly matched notch would give. If your phase swings the full $\pi$, the resonator is
critically coupled and half your photons are going into the substrate.
"""

# %%
ax_phase = result.plot(
    m_spec,
    channels="phase",
    coords={"ro_freq": Quantity(units="GHz", transform=lambda v: v / 1e9)},
    value=Quantity("Phase", "rad"),
    style=Style(markers=True),
    title="The same sweep, phase instead of magnitude",
)
ax_phase.axvline(DEVICE["q0_fr"] / 1e9, color="grey", ls=":")

phase = np.unwrap(np.angle(s21_data))
swing = np.degrees(phase.max() - phase.min())
print(f"total phase swing {swing:.0f} degrees, against the 110 the loss budget predicts")

# %% [markdown]
r"""
## 2.6 Results are xarray, and the dimension names are yours

`qp.simulate` returns a `QProgramResult`: one record per `measure` call, keyed by the handle.
`result.get(handle)` hands you an `xarray.DataArray` whose dimensions are the enclosing sweeps,
outermost first, named after your **variable ids**, with the swept values as coordinates. Integrated
measurements carry one extra `IQ` axis of length two.

The ids have to be identifiers for that reason. They are the dimension names you will type in
`.sel()` six months from now, and the identifiers in the `.qp` file. Pick them like you pick column
names.

The label and the units ride out alongside the id. They land on the coordinate as `long_name` and
`units`, and that is where the axis of the figure above got its words, since nothing in that call
named an axis. Declaring the two strings when you declare the variable is therefore the whole of
plot labeling, done once, at the point where you still remember what the variable means.

`result.get(handle)` defaults to `field=MF.IQ`. Ask for a field the measurement never requested and
you get a `KeyError`, including the default, so a state-only measurement needs `field=MF.STATE`
spelled out.

`get` accepts three spellings of the same question. A handle is the one to prefer, because it says
what it means and survives a reordering of the program, and every read in this tutorial uses one. A
plain name string selects the same record, and that is the form you reach for when the handle
objects are gone. After a `.qp` round trip, `QProgram.measurement_handles()` hands back handles that
compare equal to the originals, and Part 5 does exactly that. An integer is positional sugar for
declaration order. `bus=` narrows the candidates before any of the three is matched, so `get(0,
bus=q[1].readout)` means the first measurement on that bus rather than the first in the program.

`plot` takes all three spellings too, for the same reason and with the same lookup behind it.
"""

# %%
print(iq.isel(ro_freq=slice(0, 4)))   # the first four rows, so the repr fits on screen

print("\nwhat the variable left on the coordinate:", iq.coords["ro_freq"].attrs)

# Label-based selection is the point of xarray: no index arithmetic, no guessing the axis order.
on_resonance = iq.sel(IQ="I").sel(ro_freq=DEVICE["q0_fr"], method="nearest")
print("I at the resonator:", round(float(on_resonance), 4))

try:
    result.get(m_spec, field=MF.STATE)   # this measurement asked for iq and nothing else
except KeyError as err:
    print("asking for a field that was never requested:", err)

# %% [markdown]
r"""
## 2.7 Punchout: nesting two sweeps

You have the resonator frequency at one particular readout power, and that is not enough to set up
readout, because the frequency you measured depends on the power you measured it with.

Here is why. Dispersive readout works because the qubit and the resonator are coupled but far apart
in frequency, so they cannot swap energy and can only shift each other. The approximation behind
that has a validity limit, and the limit is a photon number:

$$ n_{\text{crit}} = \frac{\Delta^2}{4g^2} $$

With this chip's 2.35 GHz detuning and the $g \approx 190$ MHz that Part 1 backed out,
$n_{\text{crit}}$ is about 37 photons. Below that the resonator sits at $f_r + \chi$, pulled by the
qubit it is coupled to. Drive the cavity past a few tens of photons and the dispersive description
stops holding, the pull washes out, and the resonator lands on its bare frequency $f_r$. The
crossover is called punchout, and it is abrupt enough to be obvious in a 2D map.

That map is how you choose a readout power, and the choice is a squeeze from both sides. More
photons means more signal, and signal-to-noise per shot grows with the square root of the photon
number, so you want to be as high as you can. But the information lives in the $2\chi$ pull, and the
pull is the thing punchout destroys. So you park a few decibels below the crossover: enough photons
to separate the two states in one shot, few enough that there are still two states to separate.

Two nested `with` statements, two variables, and the outer one becomes the outer dimension. That is
the whole change to the program.

The arithmetic changes though. A 25 x 41 grid is 1025 points, so 200 shots each would be 205k
samples. Drop to 50 shots per point and the same scan is 51k samples, about a second. Shots x points
is the number to keep an eye on, in the simulator and on real hardware alike.
"""

# %%
def s21_power(bus, env):
    """The resonator sits at f_r + chi at low power and slides to bare f_r as it saturates."""
    saturation = 1.0 / (1.0 + (env["ro_amp"] / 0.35) ** 2)
    f_eff = DEVICE["q0_fr"] + DEVICE["q0_chi"] * saturation
    detuning = (env["ro_freq"] - f_eff) / (DEVICE["q0_kappa"] / 2)
    return 1.0 - 0.9 / (1.0 + 1j * detuning)


punchout = qp.QProgram(label="punchout", schema=schema)
pun_amp = punchout.variable("ro_amp", label="Readout amplitude", units="DAC units")
pun_freq = punchout.variable("ro_freq", label="Readout frequency", units="Hz")

with punchout.average(shots=50):
    with punchout.sweep(pun_amp, qp.Linspace(0.02, 1.0, 25)):
        with punchout.sweep(pun_freq, qp.Linspace(7.1955e9, 7.2025e9, 41)):
            punchout.set_gain(q[0].readout, pun_amp)
            punchout.set_frequency(q[0].readout, pun_freq)
            m_pun = punchout.measure(q[0].readout, "readout", "weights")

shot_loop = punchout.body.elements[0]          # Average
outer_sweep = shot_loop.elements[0]            # Sweep over ro_amp
inner_sweep = outer_sweep.elements[0]          # Sweep over ro_freq
print("points:", 25 * 41, "at 50 shots =", 25 * 41 * 50, "samples")
print(f"nesting: {type(shot_loop).__name__}({shot_loop.shots}) -> "
      f"{type(outer_sweep).__name__}({outer_sweep.variable.id}) -> "
      f"{type(inner_sweep).__name__}({inner_sweep.variable.id})")

# %% [markdown]
r"""
Two sweeps make two plot dimensions, so the same `result.plot` call that drew a line for the
one-dimensional scan draws a heatmap here, with the magnitude on the colour bar because a surface
has only one number per cell to colour. The inner sweep runs along x and the outer up y, matching
the loop nesting, so frequency comes out left to right and power upward without either being asked
for. `x=` and `y=` override that when you want it the other way round, and naming one settles the
other, which beats transposing the array yourself and then relabeling both axes to match.

Both variables were declared with a label and a unit, so the frequency axis, the amplitude axis and
the colour bar all name themselves. The two white lines are the physics, at $f_r + \chi$ and at bare
$f_r$, and they are in gigahertz because the figure is.
"""

# %%
punch_result = qp.simulate(
    punchout, model=qp.MockMeasurementModel(response=s21_power, noise=0.02, seed=11)
)
punch_iq = punch_result.get(m_pun)
print("dims:", punch_iq.dims, "shape:", punch_iq.shape, "(outermost sweep first)")

ax_pun = punch_result.plot(
    m_pun,
    coords={"ro_freq": Quantity(units="GHz", transform=lambda v: v / 1e9)},
    value=Quantity("Readout magnitude"),
    title=r"Punchout. Dotted: $f_r + \chi$. Dashed: bare $f_r$.",
)
ax_pun.axvline((DEVICE["q0_fr"] + DEVICE["q0_chi"]) / 1e9, color="w", ls=":", lw=1)
ax_pun.axvline(DEVICE["q0_fr"] / 1e9, color="w", ls="--", lw=1)

# %%
punch_mag = np.abs(punch_iq.sel(IQ="I") + 1j * punch_iq.sel(IQ="Q")).values
amps = punch_iq.coords["ro_amp"].values
scan_freqs = punch_iq.coords["ro_freq"].values
dip_per_amp = scan_freqs[punch_mag.argmin(axis=1)]

for k in (0, 12, 24):
    print(f"amplitude {amps[k]:.2f} V  ->  dip at {dip_per_amp[k] / 1e9:.6f} GHz")
print(f"low-power target   f_r + chi = {(DEVICE['q0_fr'] + DEVICE['q0_chi']) / 1e9:.6f} GHz")
print(f"high-power target  bare f_r  = {DEVICE['q0_fr'] / 1e9:.6f} GHz")
print(f"frequency step {(scan_freqs[1] - scan_freqs[0]) / 1e3:.0f} kHz,"
      " which is all the accuracy an argmin can have")

# %% [markdown]
r"""
### The power axis, log spaced

Readout power spans decades and a linear amplitude axis spends most of its points at the top end,
where nothing is moving any more. The pull in `s21_power` has already halved at 0.35 V and is down
to a fifth of itself by 0.7 V, and the 25-point linear sweep above put eight of its points past
that and only six below 0.25 V. `qp.Logspace(0.02, 1.0, 20)` puts thirteen of its twenty below
0.25 V, with five fewer measurements in total.

That costs something at the other end. `Logspace` is `arbitrary`, so no sequencer register can
produce it and the platform is back to uploading a table or stepping from the host, where `Linspace`
would have been free. Twenty points is a cheap table, so this is the trade going the right way, and
`KIND` printed below is the declaration a platform reads to decide.

The dip depth, by the way, does not move in this model. The response is always 90 percent deep and
only the centre slides, so the position carries all of the information in the figure.

The figure is the same heatmap call with one line added to it. A log amplitude axis is not something
the result can know you want, so it is `ax.set_yscale("log")` on the axes that comes back. That
division holds all the way through this tutorial. The library draws the measurement, and you draw
every decision about the figure.
"""

# %%
power_scan = qp.QProgram(label="punchout_log", schema=schema)
log_amp = power_scan.variable("ro_amp", label="Readout amplitude", units="DAC units")
log_freq = power_scan.variable("ro_freq", label="Readout frequency", units="Hz")

with power_scan.average(shots=50):
    with power_scan.sweep(log_amp, qp.Logspace(0.02, 1.0, 20)):
        with power_scan.sweep(log_freq, qp.Linspace(7.1955e9, 7.2025e9, 41)):
            power_scan.set_gain(q[0].readout, log_amp)
            power_scan.set_frequency(q[0].readout, log_freq)
            m_log = power_scan.measure(q[0].readout, "readout", "weights")

log_result = qp.simulate(
    power_scan, model=qp.MockMeasurementModel(response=s21_power, noise=0.02, seed=13)
)
log_iq = log_result.get(m_log)
log_amps = log_iq.coords["ro_amp"].values
log_freqs = log_iq.coords["ro_freq"].values
log_mag = np.abs(log_iq.sel(IQ="I") + 1j * log_iq.sel(IQ="Q")).values
log_dip = log_freqs[log_mag.argmin(axis=1)]

print("Logspace kind:", qp.Logspace(0.02, 1.0, 20).KIND, "against Linspace:",
      qp.Linspace(0.02, 1.0, 20).KIND)
print(f"{log_amps[0]:.3f} V -> {log_dip[0] / 1e9:.6f} GHz, "
      f"target f_r + chi = {(DEVICE['q0_fr'] + DEVICE['q0_chi']) / 1e9:.6f}")
print(f"{log_amps[-1]:.3f} V -> {log_dip[-1] / 1e9:.6f} GHz, "
      f"target bare f_r = {DEVICE['q0_fr'] / 1e9:.6f}")

ax_log = log_result.plot(
    m_log,
    coords={"ro_freq": Quantity(units="GHz", transform=lambda v: v / 1e9)},
    value=Quantity("Readout magnitude"),
    title="Punchout on a log power axis",
)
ax_log.set_yscale("log")

# %% [markdown]
r"""
### The same scan as a diagonal: parallel loops

Either map cost you a rectangle of measurements and most of them were off resonance. Now that you
know where the ridge is, you can walk along it instead: step the amplitude and the frequency
**together**, one point per amplitude, 25 measurements instead of 1025.

`sweep(a, src) | sweep(b, src)` is that lockstep pair. Both loops advance on the same tick, so they
must have the same length. Every source can report its length without running, so the check happens
in `Parallel`'s constructor. Mismatched lengths raise `ValidationError` on the `|` line itself, not
at run time. In the result the pair shares one dimension named `"ro_amp|ro_freq"`, carrying both
coordinate arrays. Point $k$ of one is always paired with point $k$ of the other, and there is no
grid.

The frequency list here comes from the linear map rather than the log one, so it is a `Values`
source: arbitrary by construction, and honestly so.

One dimension carrying two coordinates is more than an axis can hold, and `plot` draws both rather
than dropping one. The first variable of the pair goes along the bottom and the second on a twin
scale across the top, in the order the loops were written. Those top ticks land on samples instead
of round numbers, because tick $k$ and sample $k$ are the same measurement and a tick anywhere else
would be labeling a position nothing was measured at.

The twin takes a `coords=` restatement keyed by its own name, the same way the bottom axis does, so
the frequencies below are drawn as a detuning from the bare resonator in MHz. Left in gigahertz they
would have been five ticks spanning 1.8 MHz, every one of them rounding to 7.199.

A diagonal is what you want whenever the interesting region is a curve rather than a rectangle, and
that covers more of a lab's day than the 2D map does. Ridge tracking like this. Chevron cuts, where
the gate duration and the flux amplitude have to move together. Any scan where one parameter has to
be compensated as another moves, and that covers most of the second half of a bring-up. The 40x
saving here is typical, and the reason people still take the full map first is that you cannot walk
a ridge you have not found.
"""

# %%
ridge = qp.QProgram(label="punchout_ridge", schema=schema)
d_amp = ridge.variable("ro_amp", label="Readout amplitude", units="DAC units")
d_freq = ridge.variable("ro_freq", label="Readout frequency", units="Hz")

with ridge.average(shots=50):
    with ridge.sweep(d_amp, qp.Values(amps)) | ridge.sweep(d_freq, qp.Values(dip_per_amp)):
        ridge.set_gain(q[0].readout, d_amp)
        ridge.set_frequency(q[0].readout, d_freq)
        m_ridge = ridge.measure(q[0].readout, "readout", "weights")

ridge_result = qp.simulate(
    ridge, model=qp.MockMeasurementModel(response=s21_power, noise=0.02, seed=11)
)
ridge_iq = ridge_result.get(m_ridge)
ridge_mag = np.abs(ridge_iq.sel(IQ="I") + 1j * ridge_iq.sel(IQ="Q")).values

print("dims:  ", ridge_iq.dims, ridge_iq.shape)
print("coords:", list(ridge_iq.coords))
print("measurements:", ridge_iq.sizes["ro_amp|ro_freq"], "against", 25 * 41, "for the full map")
print("|S21| along the ridge:", np.round(ridge_mag[:6], 3), "...")
print("still in the dip everywhere:", bool(ridge_mag.max() < 0.3))

ax_ridge = ridge_result.plot(
    m_ridge,
    channels="magnitude",
    coords={
        "ro_freq": Quantity(
            "Dip frequency minus bare f_r", "MHz", lambda v: (v - DEVICE["q0_fr"]) / 1e6
        )
    },
    value=Quantity("Readout magnitude"),
    style=Style(markers=True),
    title="Walking the ridge: in the dip at every power, and the pull closing as the power rises",
)

# %% [markdown]
r"""
### 🧩 Exercise 2.1: two resonators in one pass

Qubit 1 has its own readout resonator at 7.35 GHz. Its band does not overlap qubit 0's, so scanning
them one after the other doubles your measurement time for no reason. Sweep both frequencies in
lockstep instead and measure both buses at every point.

This is the shape that scales. A 50-qubit chip has 50 resonators spread across a couple of
gigahertz, and reading them one at a time is 50 times slower than reading them together. Frequency
multiplexing is why they were spread out in the first place.

1. Declare two variables, `f0` and `f1`, and sweep them in parallel with
   `sweep(f0, ...) | sweep(f1, ...)`. Give each a 41-point `Linspace` over its own 10 MHz band
   (`7.195` to `7.205` GHz, and `7.345` to `7.355` GHz). Use `shots=100`.
2. Inside the loop, `set_frequency` on each readout bus and `measure` both. You get two handles.
3. Write one response function for both resonators. It receives `bus`, so it can pick which
   frequency and which centre to use. `q1_fr` is in `DEVICE`.
4. Print the dims of each record and the dip frequency each one found. Then write a comment
   explaining why there is one dimension of length 41 here and not a 41 x 41 grid.
5. Draw each record with `result.plot(handle, channels="magnitude")`. Both records live on the same
   `"f0|f1"` dimension, so the default reads `f0` along the bottom and `f1` across the top. That is
   the right way round for the q0 record and the wrong way round for the q1 one, where `x="f1"` asks
   for a bare axis carrying the frequency that record was actually measured at. Restate whichever
   axes you draw into GHz with `coords=`, and remember that a `coords=` key naming an axis the
   figure does not draw raises rather than being ignored.
"""

# %% solution
def s21_pair(bus, env):
    """One model, two resonators. The bus argument says which one is being measured."""
    if bus == q[0].readout:
        detuning = (env["f0"] - DEVICE["q0_fr"]) / (DEVICE["q0_kappa"] / 2)
    else:
        # DEVICE carries no q1 linewidth, so q0's stands in. Nothing here measures it.
        detuning = (env["f1"] - DEVICE["q1_fr"]) / (DEVICE["q0_kappa"] / 2)
    return 1.0 - 0.9 / (1.0 + 1j * detuning)


pair = qp.QProgram(label="two_resonators", schema=schema)
f0 = pair.variable("f0", label="q0 readout frequency", units="Hz")
f1 = pair.variable("f1", label="q1 readout frequency", units="Hz")

with pair.average(shots=100):
    band_0 = pair.sweep(f0, qp.Linspace(7.195e9, 7.205e9, 41))
    band_1 = pair.sweep(f1, qp.Linspace(7.345e9, 7.355e9, 41))
    with band_0 | band_1:
        pair.set_frequency(q[0].readout, f0)
        pair.set_frequency(q[1].readout, f1)
        m_q0 = pair.measure(q[0].readout, "readout", "weights")
        m_q1 = pair.measure(q[1].readout, "readout", "weights")

pair_model = qp.MockMeasurementModel(response=s21_pair, noise=0.02, seed=5)
pair_result = qp.simulate(pair, model=pair_model)

# The two loops advance on the same tick, so they share one dimension, "f0|f1", of length 41,
# carrying two coordinate arrays. Point k of f0 is always measured with point k of f1. A 41 x 41
# grid would need the loops nested, and 1681 points instead of 41.
for handle, coord, truth in ((m_q0, "f0", DEVICE["q0_fr"]), (m_q1, "f1", DEVICE["q1_fr"])):
    da = pair_result.get(handle)
    mag = np.abs(da.sel(IQ="I") + 1j * da.sel(IQ="Q")).values
    axis = da.coords[coord].values
    found = axis[mag.argmin()] / 1e9
    print(f"{handle.name}: dims={da.dims}, dip {found:.4f} GHz, true {truth / 1e9:.4f} GHz")

in_ghz = Quantity(units="GHz", transform=lambda v: v / 1e9)

# Both coordinates are drawn here, f0 along the bottom and f1 above, so both get restated.
ax_pair_0 = pair_result.plot(
    m_q0,
    channels="magnitude",
    coords={"f0": in_ghz, "f1": in_ghz},
    value=Quantity("Readout magnitude"),
    style=Style(markers=True),
    title="q0 resonator, with the band q1 was scanned over at the same time on top",
)

# x= drops the twin, so only the axis that is left may be named in coords=.
ax_pair_1 = pair_result.plot(
    m_q1,
    channels="magnitude",
    x="f1",
    coords={"f1": in_ghz},
    value=Quantity("Readout magnitude"),
    style=Style(markers=True),
    title="q1 resonator, the same 41 measurements, drawn against f1 alone",
)

# %% stub
# TODO: scan both readout resonators in one lockstep sweep.
# 1) f0 over 7.195 to 7.205 GHz, f1 over 7.345 to 7.355 GHz, 41 points each, shots=100.
# 2) with pair.sweep(f0, ...) | pair.sweep(f1, ...):  then set_frequency and measure on both buses.
# 3) One response(bus, env): compare bus to q[0].readout to choose the centre and the env key.
#    DEVICE["q1_fr"] is 7.35e9.
# 4) Print each record's dims and its dip frequency, and explain the single 41-long dimension
#    in a comment.
# 5) result.plot(m_q0, channels="magnitude") reads f0 below and f1 above; the q1 record wants
#    x="f1". Restate the drawn axes into GHz with coords={...: Quantity(units="GHz",
#    transform=lambda v: v / 1e9)}.

# %% [markdown]
r"""
## Recap and what is next

- A **variable** is a hole in the program, and the loop that binds it decides what goes in.
  Expressions built on top of it re-evaluate every iteration, waveform parameters included. Its
  `label` and `units` follow the data out and label the axes of every figure you draw from it.
- A **sweep source** says how the variable moves. `Range` and `Linspace` are `linear`, so a
  sequencer can run them from a register. `Values`, `Logspace`, `File` and the combinators are
  `arbitrary`, and a platform pays for that in table space or host round trips. `Range` includes its
  stop value only when the step divides the span. `Values` stays arbitrary even when its numbers are
  evenly spaced.
- **`average(shots)` adds no dimension.** It shrinks the noise on `iq` as $1/\sqrt{N}$ and turns
  `state` from a 0/1 outcome into a population. Amplifier noise and projection noise both obey that
  law, and only one of them can be fixed by buying something.
- The **measurement model** is the fake fridge, and it is the only thing in the loop that produces a
  number. No timing, no pulse physics. The program and the analysis are the real parts.
- Results are **xarray**, one dimension per enclosing sweep, outermost first, named after your
  variable ids, with one shared `"a|b"` dimension for a parallel pair. `result.plot` reads that
  shape and picks the figure, a line for one swept dimension, a heatmap for two, a twin scale for
  the pair. Fits, reference lines and a log axis go on the `Axes` it hands back.
- You now have the bare resonator at 7.200 GHz, its 1.5 MHz linewidth, the loss budget hiding in the
  90 percent dip depth, and a punchout map that says how many photons you can spend before the qubit
  stops showing through. Part 3 puts a second tone on the drive line and goes looking for the qubit
  itself.
"""
