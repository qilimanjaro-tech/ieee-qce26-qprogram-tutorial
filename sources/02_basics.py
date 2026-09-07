# %% [markdown]
r"""
# 02 · Basics

Every program in the Introduction runs once. An experiment is a program repeated while something is varied, and three pieces turn one into the other. A **variable** is the hole in the program where the knob goes, a **sweep source** says how that knob moves, and **`average(shots)`** repeats the whole thing.

The other half of this notebook is the data. `qp.simulate` returns labeled arrays whose axes are named after the variables you declared, and which know enough to draw themselves.

Three worked examples close it out: one swept variable, two of them nested, and two of them stepping in lockstep.
"""

# %%
# Run me first. A no-op when qprogram is already installed, an install when it is not
# (a fresh Google Colab runtime, for example).
try:
    import qprogram  # noqa: F401
except ImportError:
    import subprocess
    import sys

    subprocess.run([sys.executable, "-m", "pip", "install", "qprogram[viz]==0.1.0"], check=True)
    import qprogram  # noqa: F401

from importlib.metadata import version

print("qprogram", version("qprogram"))

# %%
import matplotlib.pyplot as plt
import numpy as np

import qprogram as qp
from qprogram import MeasurementField as MF
from qprogram.buses import BusSchema
from qprogram.plotting import Quantity, Style
from qprogram.waveforms import IQDrag, IQZero, Square

schema = BusSchema.transmon()
q = schema.q

# %% [markdown]
r"""
## 2.0 The numbers this notebook needs

The Introduction declared three constants and used them as literals in a program. This notebook sweeps past two of them and measures a third, so it needs two more.

`KAPPA` is the linewidth of the readout resonator, the full width at half maximum of its resonance in hertz. It sets how finely you have to step a frequency sweep to see the resonance at all. `RABI_RATE` says how strongly the drive couples to the qubit, in hertz of rotation rate per DAC unit of amplitude. It is the number that turns an amplitude on a cable into a rotation on the Bloch sphere, and it sets both how hard the qubit responds and how wide the response looks in frequency.

Every model in this notebook is a short formula over these five numbers. Nothing is looked up, nothing is hidden, and every figure comes out of a function you can read.

One thing is deliberately left out. Every `measure` below passes the string aliases `"readout"` and `"weights"` of section 1.6 rather than concrete shapes, and never binds them. The reference platform models measurements rather than pulses, so it never reads a readout envelope, and leaving the aliases unbound keeps the printed `.qp` text short enough to read. The measurement model is the only stand-in for the fridge.
"""

# %%
F01 = 4.85e9  # Hz, the qubit 0 to 1 transition
F_READOUT = 7.20e9  # Hz, the readout resonator
A_PI = 0.62  # DAC units, the drive amplitude of a full 0 to 1 rotation
KAPPA = 1.5e6  # Hz, the readout resonator linewidth (full width at half maximum)
RABI_RATE = 40e6  # Hz per DAC unit, how fast the drive rotates the qubit

print(f"resonator {F_READOUT / 1e9:.3f} GHz, {KAPPA / 1e6:.1f} MHz wide")
print(f"a drive at amplitude {A_PI} rotates the qubit at {RABI_RATE * A_PI / 1e6:.1f} MHz")

# %% [markdown]
r"""
## 2.1 Variables

A variable is a named hole in a program, and you leave one for either of two reasons. You do not know the value yet, or you want to run the same program at a series of values.

Before any loop exists a variable is an ordinary object, and the whole of what it does is hold one number at a time. Start there, because a sweep does nothing to a variable that the cell below does not do by hand.
"""

# %%
scratch = qp.QProgram(label="variables", schema=schema)
amp = scratch.variable("amp")

print("nothing bound yet:", amp.value)
amp.set_value(0.25)  # what a loop does once per iteration
print("after set_value: ", amp.value)
amp.reset()
print("after reset:     ", amp.value)

# %% [markdown]
r"""
### Declaring one

`program.variable(id, *, label=None, units=None, description=None)` is the full signature. Only the id is positional and required, and the other three are keyword-only.

The id is the one part that has to be machine-legible. It becomes the token in the `.qp` file and the dimension name in the result, so it has to match `[A-Za-z_][A-Za-z0-9_]*`, has to be unique on the program, and has to avoid the handful of words the file format reserves. All three rules raise at the declaration rather than later.

`label` and `units` are for people, and they travel with the data. The executor writes them onto the swept coordinate of every result array, where they become the axis label of every figure drawn from it. Declaring both at the declaration is the whole of plot labeling, done once and never repeated. `description` is longer prose for a reader, and it rides into the file and back out again without the result or the figure reading it.
"""

# %%
freq = scratch.variable(
    "freq", label="Readout frequency", units="Hz", description="the tone sent down the feedline"
)

print("id / label / units:", freq.id, "|", freq.label, "|", freq.units)
print("declared so far:   ", [v.id for v in scratch.variables])

for bad_id, error in (("freq", qp.ValidationError), ("readout frequency", qp.InvalidVariableIdError)):
    try:
        scratch.variable(bad_id)
    except error as exc:
        print(f"\n{type(exc).__name__}:", exc)

# %% [markdown]
r"""
## 2.2 Expressions

An operator applied to a variable builds another node and computes nothing. Five families are available.

- `+`, `-`, `*` and `/`, with their reflected forms, build a `BinaryOp`. There is no power, floor division, or modulo.
- Unary `-` and `+` build a `UnaryOp`.
- `abs()` and the eight module functions `qp.sin`, `qp.cos`, `qp.tan`, `qp.exp`, `qp.log`, `qp.sqrt`, `qp.minimum` and `qp.maximum` build a `MathFunc`.
- `<`, `<=`, `>` and `>=` build a `Comparison`, and `qp.where(condition, then, else_)` turns one back into a value.
- `&`, `|` and `~` build a `LogicalBinaryOp` or a `LogicalNot`.

Equality is the one gap. `Variable.__eq__` has to keep returning a plain bool so that variables can live in a set, so the symbolic spellings are `qp.eq` and `qp.ne`. A measurement handle is under no such constraint, and the branch in the Advanced notebook is spelled `if_(handle.state == 1)` for that reason.

An expression also refuses to be a truth value, so `if amp > 0.5:` raises on the line that wrote it rather than quietly taking the object as true.
"""

# %%
sketch = qp.QProgram(label="expressions", schema=schema)
detuning = sketch.variable("detuning", label="Detuning", units="Hz")

sketch.set_frequency(q[0].readout, detuning + F_READOUT)  # an expression, written into the tree
sketch.wait(q[0].readout, 4 * detuning)

print(qp.dumps(sketch).split("body:")[1].rstrip())

try:
    if amp > 0.5:
        pass
except TypeError as exc:
    print("\nan expression is not a truth value:", exc)

# %% [markdown]
r"""
### Where an expression may appear

Anywhere QProgram takes a number. Among the operations that means `set_frequency`, `set_gain`, `set_phase`, both paths of `set_offset`, the value of `set_parameter`, and the duration of `wait`. Among the waveforms it means every numeric constructor argument of every parameterized shape, with the samples of `Arbitrary`, the wrapping shapes, and `FlatTop`'s integer buffer as the exceptions.

`play` and `measure` take a waveform rather than a number, so an expression reaches a pulse through the waveform's constructor. A shape built that way computes nothing until `envelope()` is called on it, and section 2.8 sweeps a pulse amplitude exactly this way.

Two methods read an expression tree, and they differ in what they do about a hole. `evaluate()` returns `qp.UNASSIGNED` as soon as anything in the tree is unbound, and the sentinel propagates upward, so code inspecting a half-built program never has to guard. `evaluate_or_raise()` insists on a number instead. The interpreter calls that one before running an operation, so a variable no enclosing loop binds becomes an error rather than a silent zero.
"""

# %%
tone = Square(amplitude=amp / 2, duration=8)
amp.set_value(0.8)
print("the shape computes on demand:", tone.envelope())
amp.reset()
print("and reports the hole once the value is gone:", tone.amplitude.evaluate())

orphan = qp.QProgram(label="unbound", schema=schema)
loose = orphan.variable("loose")
orphan.set_gain(q[0].readout, loose)  # nothing will ever bind it
try:
    qp.simulate(orphan)
except qp.UnassignedVariableError as exc:
    print("\nat run time:", exc)

# %% [markdown]
r"""
## 2.3 Sweeps

A variable left alone stays unassigned, and `program.sweep(variable, source)` binds it. The block runs its body once per value, writing that value into the variable first, so every operation inside sees the current one.

The values are not part of the block. They come from a **source**, and a source is to a sweep what a waveform is to a `play`: a small immutable value object that serializes as a constructor call and carries its own capability tokens. One loop type covers every shape of values because the shape lives in the source.
"""

# %%
tiny = qp.QProgram(label="smallest_sweep", schema=schema)
gain = tiny.variable("gain")

with tiny.sweep(gain, qp.Values([0.1, 0.2, 0.3])):
    tiny.set_gain(q[0].readout, gain)

print(qp.dumps(tiny).split("body:")[1].rstrip())

# %% [markdown]
r"""
### The three spellings

Leave the source out and `sweep` hands back a builder whose `from_*` methods make one for you. A bare list in the source position is a third spelling and means `qp.Values`.

An unknown `from_<name>` resolves against the live sweep-source registry rather than a fixed list, so a source registered by a vendor extension gets its builder with no change to the core. All three spellings build the same node and write the same `.qp` line, so pick by what the call site is doing. Reach for `from_*` when you are typing the numbers out, and pass the object when the source is computed or when you want to read its properties.
"""

# %%
fluent = qp.QProgram(label="smallest_sweep", schema=schema)
g_fluent = fluent.variable("gain")
with fluent.sweep(g_fluent).from_values([0.1, 0.2, 0.3]):
    fluent.set_gain(q[0].readout, g_fluent)

bare = qp.QProgram(label="smallest_sweep", schema=schema)
g_bare = bare.variable("gain")
with bare.sweep(g_bare, [0.1, 0.2, 0.3]):  # a bare list means Values
    bare.set_gain(q[0].readout, g_bare)

print("same tree:", tiny.body == fluent.body == bare.body)
print("same text:", qp.dumps(tiny) == qp.dumps(fluent) == qp.dumps(bare))

# %% [markdown]
r"""
### The sources

Eight ship, and every one is reachable both ways.

| Source | What it is |
|---|---|
| `qp.Range(start, stop, step=1)` | a ramp given by its spacing |
| `qp.Linspace(start, stop, num)` | a ramp given by its point count |
| `qp.Values(points)` | an explicit list, anything `numpy.asarray` takes |
| `qp.Logspace(start, stop, num)` | `num` points log spaced between two real bounds, not exponents |
| `qp.File(path)` | the points in a `.npy`, stored as the path and re-read on every access |
| `qp.Repeat(source, times)` | one source, run through `times` times over |
| `qp.Rotate(source, by=1)` | one source, shifted cyclically left |
| `qp.Concat(sources)` | several sources, end to end |

The last three take a source and hand back a source, so they compose with each other and with the five above. The fluent spelling reaches two of them by chaining, so `.rotate(by=...)` and `.repeat(...)` hang off a sweep that already has values.
"""

# %%
base = qp.Values([0.0, 0.5, 1.0])
sources = [
    qp.Range(0.0, 1.0, 0.25),
    qp.Linspace(0.0, 1.0, 5),
    qp.Logspace(0.01, 1.0, 5),
    qp.Repeat(base, 2),
    qp.Rotate(base, by=1),
    qp.Concat([base, qp.Linspace(2.0, 3.0, 3)]),
]

for source in sources:
    print(f"{type(source).__name__:9} {source.length():2d} points  {np.round(source.values(), 3)}")

chained = qp.QProgram(label="chained_source", schema=schema)
g_chain = chained.variable("gain")
with chained.sweep(g_chain).from_values([0.1, 0.2, 0.3]).rotate(by=1).repeat(2):
    chained.set_gain(q[0].readout, g_chain)

print("\nrotated once, then run through twice:")
print(qp.dumps(chained).split("body:")[1].rstrip())

# %% [markdown]
r"""
### Linear and arbitrary

Every source carries two class attributes a platform reads without running anything. `KIND` is either `"linear"` or `"arbitrary"`, and `TOKEN` is the capability name a platform accepts or refuses.

`"linear"` is a promise about the values. Point $i$ is exactly `start + step * i`, and that promise is the whole of what a sequencer register needs to generate the loop on its own. `"arbitrary"` means the values are a list, and a list has to reach the instrument as a table or one point at a time from the host.

`qp.Values` is arbitrary **even when the numbers you pass are evenly spaced**, because a list of floats proves nothing about its own regularity. If your sweep really is a ramp, say `qp.Range` or `qp.Linspace`. The kind also degrades: a combinator is arbitrary whatever it wraps, and it still asks for everything its children ask for. The Advanced notebook is where a rack reads these declarations and decides.

`qp.Range` is worth one more line, because it counts its own points. It holds `round((stop - start) / step) + 1` of them and lands on `stop` only when the step divides the span evenly.
"""

# %%
for source in (qp.Range(0.0, 1.0, 0.25), qp.Linspace(0.0, 1.0, 5), base, qp.Concat([base])):
    print(f"{type(source).__name__:9} {source.KIND:10} {sorted(source.tokens())}")

print("\nRange(0, 10, 2) lands on stop: ", qp.Range(0, 10, 2).values())
print("Range(0, 10, 3) stops short:   ", qp.Range(0, 10, 3).values())

try:
    qp.Range(0, 10, -2)  # a step pointing away from stop
except qp.ValidationError as exc:
    print("\nrefused at construction:", exc)

# %% [markdown]
r"""
## 2.4 The measurement model

The interpreter asks a **measurement model** for one sample per shot per `measure`, and the model is the only source of numbers in a run. It receives the bus being measured and `env`, a mapping of every variable that currently holds a number, keyed by id, plus the platform parameter store keyed as `"bus.parameter"`. A variable that no enclosing loop has bound is absent from `env` rather than zero, so a model reaching for one fails loudly.

`qp.MockMeasurementModel(response=None, p_excited=None, noise=0.0, raw_samples=16, seed=0)` covers most cases, and every default does something. No `response` answers `0j`, no `p_excited` keeps every shot in the ground state, `noise` is the per-quadrature gaussian sigma applied per shot, and `seed` feeds one private generator, so a fresh model at the same seed replays the same numbers where one model reused across two runs does not.

The cell below prints what a model is actually handed, once per shot per point.
"""

# %%
seen = []


def peek(bus, env):
    """A response function that records what it was asked, then returns a flat signal."""
    seen.append((str(bus), dict(env)))
    return 1 + 0j


probe = qp.QProgram(label="env_probe", schema=schema)
p_amp = probe.variable("ro_amp", units="DAC units")
p_freq = probe.variable("ro_freq", units="Hz")

with probe.average(shots=2):
    with probe.sweep(p_amp, qp.Values([0.1, 0.4])):
        with probe.sweep(p_freq, qp.Linspace(7.19e9, 7.21e9, 3)):
            probe.measure(q[0].readout, "readout", "weights")

qp.simulate(probe, model=qp.MockMeasurementModel(response=peek))

print("samples requested:", len(seen), "= 2 shots x 2 amplitudes x 3 frequencies")
print("bus:", seen[0][0])
print("env:", seen[0][1])

# %% [markdown]
r"""
### Writing your own

`qp.MockMeasurementModel` is a convenience over a two-line protocol, and reaching past it takes no ceremony. A model is any object with a `sample(bus, env)` method returning a `qp.MeasurementSample`, which carries `i`, `q`, `state`, and an optional `raw` trace. Set a `raw_samples` attribute when the model simulates an ADC, and the executor reads it once at the start of a run.

Reach for your own class when the response has state in it, when two buses answer from shared bookkeeping, or when the classified outcome and the integrated point have to agree in a way the mock's two independent callbacks cannot express.
"""

# %%
class TwoStateReadout:
    """Two IQ clouds, one per qubit state, with the state drawn first so the two agree."""

    def __init__(self, p_excited, seed=0):
        self.p_excited = p_excited
        self.rng = np.random.default_rng(seed)

    def sample(self, bus, env):
        state = int(self.rng.random() < self.p_excited(bus, env))
        centre_i, centre_q = (0.9, 0.1) if state else (0.2, -0.3)
        spread = self.rng.normal(0.0, 0.08, 2)
        return qp.MeasurementSample(i=centre_i + spread[0], q=centre_q + spread[1], state=state)


one_point = qp.QProgram(label="own_model", schema=schema)
m_own = one_point.measure(q[0].readout, "readout", "weights", fields=(MF.IQ, MF.STATE))
own = qp.simulate(one_point, model=TwoStateReadout(lambda bus, env: 1.0, seed=1))

print("one shot of the excited cloud:", np.round(own.get(m_own).values, 3))
print("and its classified state:     ", float(own.get(m_own, field=MF.STATE)))

# %% [markdown]
r"""
## 2.5 `average(shots)` adds no dimension

`with program.average(shots=N)` wraps a block and repeats it. The integrated point and the raw trace come back as means over the shots, the classified state comes back as the excited-state population, and the shot count appears nowhere in the shape of the result.

Adding no dimension is not the same as costing nothing. `average` declares the same repetition flag a sweep does, so it occupies a repetition level on a sequencer like any other loop, and the Advanced notebook is where that turns into a platform limit.
"""

# %%
def flat_scan(shots):
    """Measure a constant noisy signal 64 times, averaged `shots` deep."""
    program = qp.QProgram(label=f"flat_{shots}", schema=schema)
    index = program.variable("idx")
    with program.average(shots=shots):
        with program.sweep(index, qp.Range(0, 63, 1)):
            handle = program.measure(q[0].readout, "readout", "weights")
    model = qp.MockMeasurementModel(response=lambda bus, env: 1 + 0j, noise=0.5, seed=5)
    return qp.simulate(program, model=model).get(handle)


for shots in (1, 4, 64, 256):
    scan = flat_scan(shots)
    print(f"shots={shots:4d}  dims={scan.dims}  shape={scan.shape}  "
          f"std(I)={scan.sel(IQ='I').values.std():.4f}")

# %% [markdown]
r"""
The shape never changes and only the spread does. Doubling the shots buys a factor of 1.4 in noise for twice the measurement time, so shots are the last knob to turn: fixing a badly placed readout frequency or a lossy cable costs nothing per shot.

Averaging does something different to the classified state. One shot is classified 0 or 1, so one shot gives you a bit. Average five hundred and the same array position holds a population. Nothing about the array shape says which of the two you are holding, because the shot count decides and the shot count is not in the result.
"""

# %%
def population_scan(shots):
    """Five repeats of a measurement on a qubit that is excited 30 percent of the time."""
    program = qp.QProgram(label=f"pop_{shots}", schema=schema)
    rep = program.variable("rep")
    with program.average(shots=shots):
        with program.sweep(rep, qp.Range(0, 4, 1)):
            handle = program.measure(q[0].readout, "readout", "weights", fields=(MF.STATE,))
    biased = qp.MockMeasurementModel(p_excited=lambda bus, env: 0.3, seed=9)
    return qp.simulate(program, model=biased).get(handle, field=MF.STATE)


print("shots=1   ->", population_scan(1).values, "  one classified shot per point")
print("shots=500 ->", population_scan(500).values, "  the same shape, now a population")

# %% [markdown]
r"""
## 2.6 One swept variable

Everything above assembled. The experiment steps the readout frequency across the resonator and records what comes back at every step, which is how the resonator is found on a new chip in the first place. A resonator hung off a feedline shows up as a notch in transmission,

$$ S_{21}(f) = 1 - \frac{0.9}{1 + i\,\delta}, \qquad \delta = \frac{f - f_r}{\kappa / 2} $$

so the model is one line of arithmetic over `F_READOUT` and `KAPPA`. The window is 20 MHz wide in 200 kHz steps, which puts about seven samples across a resonance 1.5 MHz wide.
"""

# %%
def s21(bus, env):
    """Transmission past one resonator: a notch, 90 percent deep on resonance."""
    delta = (env["ro_freq"] - F_READOUT) / (KAPPA / 2)
    return 1.0 - 0.9 / (1.0 + 1j * delta)


spectroscopy = qp.QProgram(
    label="resonator_spectroscopy", description="Find the readout resonator.", schema=schema
)
ro_freq = spectroscopy.variable("ro_freq", label="Readout frequency", units="Hz")

with spectroscopy.average(shots=200):
    with spectroscopy.sweep(ro_freq, qp.Range(7.19e9, 7.21e9, 0.2e6)):
        spectroscopy.set_frequency(q[0].readout, ro_freq)
        m_spec = spectroscopy.measure(q[0].readout, "readout", "weights")

print(qp.dumps(spectroscopy))

# %%
result = qp.simulate(spectroscopy, model=qp.MockMeasurementModel(response=s21, noise=0.02, seed=7))
iq = result.get(m_spec)

print("dims:", iq.dims, "shape:", iq.shape)
print("101 frequencies by two quadratures. The 200 shots are gone, since average collapsed them.")

# %% [markdown]
r"""
### The result model

`qp.simulate` returns a `qp.QProgramResult`, which holds one record per `measure` in the program, in the order they were declared. Each record carries the bus it ran on, the name you gave it, and the fields that measurement asked for.
"""

# %%
print(result)
for record in result.measurements:
    print("  ", record.bus, record.name, sorted(record.fields))

# %% [markdown]
r"""
`result.get(measurement, bus=None, field=MF.IQ)` pulls one array out, and it resolves three spellings of the first argument. A handle says what it means and is the one to prefer. A plain name string selects the same record, and you reach for that after loading a program back from a `.qp` file in a session that never built it. An integer is positional sugar for declaration order. `bus=` narrows the candidates first, so `get(0, bus=q[1].readout)` means the first measurement on that bus, and `result.plot` takes all three spellings too.

`field=` defaults to the integrated point. Ask for a field the measurement never requested and you get a `KeyError`, the default included, so a measurement declared with `fields=(MF.STATE,)` needs `field=MF.STATE` spelled out.

What comes back is an `xarray.DataArray`. Its dimensions are the enclosing sweeps, outermost first, named after your variable ids, with the swept values as coordinates, and an integrated measurement carries one extra `IQ` axis of length two. The label and the units you declared arrive as attributes on the coordinate, which is where every axis label in this notebook comes from.
"""

# %%
print("by handle:", result.get(m_spec).shape,
      "| by name:", result.get("q0/readout/m0").shape,
      "| by position:", result.get(0).shape)
print("what the variable left on the coordinate:", iq.coords["ro_freq"].attrs)

# Label-based selection is the point of xarray: no index arithmetic, no guessing the axis order.
on_resonance = iq.sel(IQ="I").sel(ro_freq=F_READOUT, method="nearest")
print("I at the resonator:", round(float(on_resonance), 4))

try:
    result.get(m_spec, field=MF.STATE)  # this measurement asked for the point and nothing else
except KeyError as exc:
    print("a field that was never requested:", exc)

# %% [markdown]
r"""
### Reading the numbers off

The dip position comes straight out of the array. `argmin` on the magnitude gives the centre to one step of the grid, so a 200 kHz grid gives the resonator to 200 kHz, and a finer answer wants a fit rather than a finer grid.
"""

# %%
freqs = iq.coords["ro_freq"].values
magnitude = np.abs(iq.sel(IQ="I").values + 1j * iq.sel(IQ="Q").values)
f_dip = freqs[magnitude.argmin()]

print(f"dip at   {f_dip / 1e9:.6f} GHz")
print(f"true     {F_READOUT / 1e9:.6f} GHz")
print(f"the sweep steps {(freqs[1] - freqs[0]) / 1e3:.0f} kHz, which bounds what an argmin can say")

# %% [markdown]
r"""
## 2.7 Drawing a result

`result.plot(handle)` looks the array up exactly as `result.get(handle)` does and lets the shape choose the figure. One swept dimension besides `IQ` makes a line, and two make a heatmap. Nothing in the bare call below names an axis: the variable was declared with a label and a unit, both rode out to the coordinate, and the figure reads them off it.

Two lines come back because `channels` defaults to the pair of quadratures. `channels="magnitude"` takes the hypotenuse and draws one curve instead, `channels="phase"` draws the argument, and the y axis renames itself to match. Magnitude flattens out when a dip is shallow and phase stays readable there, so the two are worth having both.
"""

# %%
result.plot(m_spec)
plt.show()

result.plot(m_spec, channels="magnitude")
plt.show()

# %% [markdown]
r"""
Everything past the bare call is a decision about the figure rather than about the data, and each one is either an argument you add or a method on the `Axes` that came back.

`coords=` restates a coordinate for the figure alone and leaves the stored array untouched, and `Quantity(label, units, transform)` reads positionally in that order. A frequency axis wants gigahertz, and the restatement is a pair wherever there is a claim to falsify: on a coordinate that already declares `units="Hz"`, a transform alone would move the numbers under a label that still says hertz, and a unit alone would relabel numbers nobody moved. Both halves or neither.

Because the drawn numbers moved, everything you hand the returned `Axes` afterwards is in the figure's units too, so both reference lines below are divided by `1e9`. `value=` restates the measured quantity the same way, and `style=` carries the choices about the drawing itself, so `Style(markers=True)` puts a marker at every sample.
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
ax.axvline(F_READOUT / 1e9, color="grey", ls=":", label="true resonator")
ax.legend(fontsize=8)
plt.show()

# %%
for half_a_pair in (dict(transform=lambda v: v / 1e9), dict(units="GHz")):
    try:
        result.plot(m_spec, coords={"ro_freq": Quantity(**half_a_pair)})
    except qp.ValidationError as exc:
        print(exc, "\n")

# %% [markdown]
r"""
## 2.8 Two nested sweeps

Two `with` statements nest two loops, and nesting in the file is nesting in the result. The outer sweep becomes the outer dimension, and shots times points is the number to keep an eye on in the simulator and on real hardware alike.

The experiment finds the qubit. A weak tone is parked on the drive line and its frequency stepped, and where it hits the transition the qubit spends part of its time excited, which the readout reports as a population. Repeating that scan at a series of drive amplitudes turns one line into a map, and the map shows two effects at once. A stronger drive lifts the peak toward the ceiling of one half, and it also broadens the line, because the response is a Lorentzian whose width is the rotation rate itself,

$$ P_1(f, a) = \frac{1}{2}\,\frac{\Omega^2}{\Omega^2 + (f - f_{01})^2}, \qquad \Omega = \texttt{RABI\_RATE} \times a $$

The outer variable goes into the pulse rather than into an operation, so section 2.2's expression in a waveform constructor is here doing a real job.
"""

# %%
def p_saturated(bus, env):
    """Excited-state population under a drive of amplitude `drive_amp`, detuned from F01."""
    rabi = RABI_RATE * env["drive_amp"]
    return 0.5 * rabi**2 / (rabi**2 + (env["drive_freq"] - F01) ** 2)


two_tone = qp.QProgram(label="qubit_spectroscopy", description="Find the qubit.", schema=schema)
drive_amp = two_tone.variable("drive_amp", label="Drive amplitude", units="DAC units")
drive_freq = two_tone.variable("drive_freq", label="Drive frequency", units="Hz")

with two_tone.average(shots=200):
    with two_tone.sweep(drive_amp, qp.Linspace(0.05, 0.30, 21)):
        with two_tone.sweep(drive_freq, qp.Linspace(F01 - 20e6, F01 + 20e6, 41)):
            two_tone.set_frequency(q[0].drive, drive_freq)
            two_tone.play(q[0].drive, IQZero(Square(amplitude=drive_amp, duration=20_000)))
            two_tone.sync([q[0].drive, q[0].readout])
            m_two_tone = two_tone.measure(q[0].readout, "readout", "weights", fields=(MF.STATE,))

print("points:", 21 * 41, "at 200 shots =", 21 * 41 * 200, "samples")

# %%
map_result = qp.simulate(two_tone, model=qp.MockMeasurementModel(p_excited=p_saturated, seed=11))
population = map_result.get(m_two_tone, field=MF.STATE)

print("dims:", population.dims, "shape:", population.shape, "(outermost sweep first)")

# %% [markdown]
r"""
Two swept dimensions make a heatmap, with one number per cell on the colour bar. The inner sweep runs along x and the outer up y, matching the loop nesting, so frequency comes out left to right and amplitude upward without either being asked for. `x=` and `y=` override that, and naming one settles the other.
"""

# %%
ax_map = map_result.plot(
    m_two_tone,
    field=MF.STATE,
    coords={"drive_freq": Quantity("Drive frequency", "MHz from $f_{01}$", lambda v: (v - F01) / 1e6)},
    value=Quantity("Excited-state population"),
    title="Qubit spectroscopy against drive amplitude",
)
ax_map.axvline(0.0, color="w", ls=":", lw=1)
plt.show()

# %% [markdown]
r"""
The ridge sits on the transition at every amplitude and widens upward. Turning that into a number is two lines of numpy on the array, and the formula above predicts what the number should be: the response falls to half its peak exactly one rotation rate away from resonance, so the measured full width should come out at twice the rotation rate.
"""

# %%
amps = population.coords["drive_amp"].values
scan = population.coords["drive_freq"].values
rows = population.values

print("amplitude   measured width   2 x rotation rate")
for row in (0, 10, 20):
    above = scan[rows[row] >= 0.25]  # half of the ceiling of one half
    print(f"    {amps[row]:.3f}      {(above[-1] - above[0]) / 1e6:5.1f} MHz"
          f"          {2 * RABI_RATE * amps[row] / 1e6:5.1f} MHz")

# %% [markdown]
r"""
The two upper rows agree exactly and the lowest one reads 3 MHz against a predicted 4. The sweep steps 1 MHz, and a width measured by counting which samples clear a threshold cannot land between two samples, so the narrowest line in the map is the one the grid resolves worst. Choosing a grid is choosing which part of the answer you are willing to quantise.
"""

# %% [markdown]
r"""
## 2.9 Two sweeps in lockstep

The map cost a rectangle of measurements and most of them sat off resonance. Now that the ridge has been found, you can walk along it instead, stepping two variables **together**, one point per row.

`sweep(a, source) | sweep(b, source)` is that lockstep pair. Both loops advance on the same tick over one shared body, so they must have the same length, and every source reports its length without running. The `|` itself computes nothing and modifies nothing, so the check fires when the block opens rather than on the line that composed it. That purity is the point rather than an accident, since it is what lets a list of sweeps be folded together and what lets a third `|` chain a third loop.

In the result the pair shares one dimension whose name joins the ids, carrying one coordinate array per composed variable. Point $k$ of one is always paired with point $k$ of the other, and there is no grid. The block it builds is a `Parallel`, which keeps its loops on `.loops` while `.elements` holds the shared body.
"""

# %%
mismatched = qp.QProgram(label="mismatched", schema=schema)
a = mismatched.variable("a")
b = mismatched.variable("b")

pair_of_loops = mismatched.sweep(a, qp.Linspace(0, 1, 5)) | mismatched.sweep(b, qp.Linspace(0, 1, 6))
print("the | itself:", type(pair_of_loops).__name__, "and no exception yet")

try:
    with pair_of_loops:
        pass
except qp.ValidationError as exc:
    print("caught when the block opens:", exc)

# %% [markdown]
r"""
The ridge below is the peak frequency of each row of the map, read off the array. Walking it takes 21 measurements against 861 for the full rectangle, and a diagonal earns its place whenever the interesting region is a curve rather than a rectangle. The full map comes first, because you cannot walk a ridge you have not found.
"""

# %%
ridge_freqs = scan[rows.argmax(axis=1)]

ridge = qp.QProgram(label="qubit_ridge", schema=schema)
r_amp = ridge.variable("drive_amp", label="Drive amplitude", units="DAC units")
r_freq = ridge.variable("drive_freq", label="Drive frequency", units="Hz")

with ridge.average(shots=100):
    with ridge.sweep(r_amp, qp.Values(amps)) | ridge.sweep(r_freq, qp.Values(ridge_freqs)):
        ridge.set_frequency(q[0].drive, r_freq)
        ridge.play(q[0].drive, IQZero(Square(amplitude=r_amp, duration=20_000)))
        ridge.sync([q[0].drive, q[0].readout])
        m_ridge = ridge.measure(q[0].readout, "readout", "weights", fields=(MF.STATE,))

pair_block = ridge.body.elements[0].elements[0]
print("block:", type(pair_block).__name__, "over", [loop.variable.id for loop in pair_block.loops])

# %%
ridge_result = qp.simulate(ridge, model=qp.MockMeasurementModel(p_excited=p_saturated, seed=11))
ridge_pop = ridge_result.get(m_ridge, field=MF.STATE)

print("dims:  ", ridge_pop.dims, ridge_pop.shape)
print("coords:", list(ridge_pop.coords))
print("measurements:", ridge_pop.sizes["drive_amp|drive_freq"], "against", 21 * 41, "for the full map")
print("lowest population along the ridge:", round(float(ridge_pop.min()), 3), "against a ceiling of 0.5")

# %% [markdown]
r"""
One dimension carrying two coordinates is more than an axis can hold, and `plot` draws both rather than dropping one. The first variable of the pair goes along the bottom and the second on a twin scale across the top, in the order the loops were written, and those top ticks land on samples instead of round numbers because tick $k$ and sample $k$ are the same measurement. The twin takes its own `coords=` restatement, keyed by its own name.

`x=` drops the twin and asks for a bare axis instead, and once dropped, a `coords=` key naming the coordinate that is gone raises rather than doing nothing.
"""

# %%
ridge_result.plot(
    m_ridge,
    field=MF.STATE,
    coords={"drive_freq": Quantity("Peak frequency", "MHz from $f_{01}$", lambda v: (v - F01) / 1e6)},
    value=Quantity("Excited-state population"),
    style=Style(markers=True),
    title="Walking the ridge",
)
plt.show()

try:
    ridge_result.plot(m_ridge, field=MF.STATE, x="drive_amp",
                      coords={"drive_freq": Quantity(units="Hz")})
except qp.ValidationError as exc:
    print(exc)

# %% [markdown]
r"""
### 🧩 Exercise 2.1

Take a cut through the map. Section 2.8 stepped the drive amplitude and the drive frequency together over a rectangle. Park the frequency on the transition instead and step the amplitude alone, far enough to drive the qubit all the way over and back.

A drive left on resonance rotates the qubit at a rate proportional to its amplitude, so the population follows $\sin^2$ rather than the saturated Lorentzian of 2.8. The model below is that curve, peaking at `A_PI` by construction.

1. Build a `qp.QProgram` with `label="rabi"` and the `schema` in scope. Declare `amp` with `label="Drive amplitude"` and `units="DAC units"`.
2. Wrap the experiment in `average(shots=200)` and sweep `amp` with a 41-point `qp.Linspace` from 0.0 to 1.0.
3. Inside the loop, `set_frequency` the drive bus to `F01`, then `play` an `IQDrag(amplitude=amp, duration=40, sigma=10, beta=0.15)` on it. The variable goes inside the waveform, as in section 2.8.
4. `sync` the drive and readout buses, then `measure` the readout bus with the `"readout"` and `"weights"` aliases and `fields=(MF.STATE,)`.
5. Run it with `qp.MockMeasurementModel(p_excited=p_rabi, seed=17)` and print the dims and shape of the state array.
6. Read the calibration off the rising branch rather than off the peak. Restrict to `amps <= 0.5`, find the amplitude whose population sits closest to one half, and double it. Print that beside `A_PI`.
7. Draw it with `style=Style(markers=True)` and `value=Quantity("Excited-state population")`, then put a dashed line on the returned axes at the amplitude you found.

Step 6 is the interesting one. The top of a $\sin^2$ curve is flat, so shot noise moves an `argmax` by several grid points and the answer is worse than the grid. The half-way crossing sits on the steepest part of the same curve, where the same noise moves the answer by a fraction of one step. The amplitude axis needs no `coords=` at all, because DAC units are the units the program already declared.
"""

# %%
def p_rabi(bus, env):
    """A drive on resonance rotates the qubit, so the population follows a sine squared in amplitude."""
    return np.sin(np.pi * env["amp"] / (2 * A_PI)) ** 2


# %% solution
rabi = qp.QProgram(label="rabi", schema=schema)
r_pulse_amp = rabi.variable("amp", label="Drive amplitude", units="DAC units")

with rabi.average(shots=200):
    with rabi.sweep(r_pulse_amp, qp.Linspace(0.0, 1.0, 41)):
        rabi.set_frequency(q[0].drive, F01)
        rabi.play(q[0].drive, IQDrag(amplitude=r_pulse_amp, duration=40, sigma=10, beta=0.15))
        rabi.sync([q[0].drive, q[0].readout])
        m_rabi = rabi.measure(q[0].readout, "readout", "weights", fields=(MF.STATE,))

rabi_result = qp.simulate(rabi, model=qp.MockMeasurementModel(p_excited=p_rabi, seed=17))
rabi_pop = rabi_result.get(m_rabi, field=MF.STATE)
rabi_amps = rabi_pop.coords["amp"].values

rising = rabi_amps <= 0.5  # the first half of the sweep, before the curve turns over
half_amp = float(rabi_amps[rising][np.abs(rabi_pop.values[rising] - 0.5).argmin()])
a_pi_found = 2 * half_amp

print("dims:", rabi_pop.dims, "shape:", rabi_pop.shape)
print(f"half rotation at {half_amp:.3f}, so a full one at {a_pi_found:.3f}")
print(f"true A_PI {A_PI:.3f}, grid step {rabi_amps[1] - rabi_amps[0]:.3f}")

ax_rabi = rabi_result.plot(
    m_rabi,
    field=MF.STATE,
    value=Quantity("Excited-state population"),
    style=Style(markers=True),
    title="A drive on resonance, stepped in amplitude",
)
ax_rabi.axvline(a_pi_found, color="grey", ls="--", lw=1, label=f"full rotation at {a_pi_found:.3f}")
ax_rabi.legend(fontsize=8)
plt.show()

# %% stub
# TODO: sweep the drive amplitude on resonance and find the amplitude of the peak.
# 1) rabi = qp.QProgram(label="rabi", schema=schema); declare amp with label and units
# 2) with rabi.average(shots=200): with rabi.sweep(amp, qp.Linspace(0.0, 1.0, 41)):
# 3)     set_frequency(q[0].drive, F01), then play IQDrag(amplitude=amp, duration=40, sigma=10,
#        beta=0.15) on the drive bus
# 4)     sync([q[0].drive, q[0].readout]), then measure the readout bus with the "readout" and
#        "weights" aliases and fields=(MF.STATE,)
# 5) qp.simulate(rabi, model=qp.MockMeasurementModel(p_excited=p_rabi, seed=17)), then print the
#    dims and shape of the state array
# 6) rising = rabi_amps <= 0.5; take the amplitude whose population is closest to 0.5, double
#    it, and print it beside A_PI
# 7) plot with style=Style(markers=True) and value=Quantity("Excited-state population"), then
#    ax.axvline at the amplitude you found

# %% [markdown]
r"""
## Recap

- A **variable** is a hole in the program, declared with `program.variable(id, label=..., units=...)`. The label and the units follow the data out and name the axes of every figure, so declaring them once is the whole of plot labeling.
- **Arithmetic on a variable builds a tree and computes nothing.** The tree re-evaluates every iteration, it may go anywhere QProgram takes a number, and it reaches a pulse through a waveform's constructor.
- A **sweep source** says how the variable moves, and a sweep has three spellings: a source object, a `from_*` builder, and a bare list meaning `qp.Values`. `qp.Range` and `qp.Linspace` are linear, so a sequencer can run them from a register, and everything else is arbitrary.
- **`average(shots)` adds no dimension.** It shrinks the noise on the integrated point, it turns the classified state from a 0 or a 1 into a population, and it still costs a repetition level on the sequencer.
- The **measurement model** is the only thing in a run that produces a number. `qp.MockMeasurementModel` covers most cases and any object with a `sample(bus, env)` method covers the rest.
- **Results are xarray.** One dimension per enclosing sweep, outermost first, named after your variable ids, plus an `IQ` axis, plus one shared `"a|b"` dimension for a lockstep pair. `get` takes a handle, a name, or an integer, and `result.plot` picks a line for one swept dimension and a heatmap for two, then hands back the `Axes` your reference lines go on.
"""

# %% [markdown]
r"""
## Next

**Advanced.** Six sections, each standing on its own. Two are about writing less: a fragment factors a repeated sequence out, and a conditional lets a measurement decide what the program does next. Two are about adding to the language: your own waveform and sweep source, and your own vendor operation beside the two published extension packages. And two are about the machine: implementing the platform interface, and reading the capability descriptor a platform publishes so a program can be checked and replanned before it is ever uploaded.
"""
