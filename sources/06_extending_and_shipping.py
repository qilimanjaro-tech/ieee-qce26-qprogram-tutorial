# %% [markdown]
r"""
# 06 · Extending the language and shipping the work

Five parts in, every program you wrote used operations, waveforms, and sweep sources that ship with
QProgram. Real labs run out of those on day one. Someone has a pulse shape their vendor's compiler
already knows and the DSL does not. Someone drives a room-temperature attenuator that no core
operation will ever cover. Someone scans a chevron by centre and span instead of start and stop.

A control DSL that cannot be extended gets forked. This part is about the seams that stop that from
happening, and about what you do with the result:

- register a **waveform**, a **sweep source**, and a whole **vendor namespace**, live in this
  notebook
- watch the `require` line appear in the `.qp` text, and watch a rack that lacks the token refuse
  the program
- treat the `.qp` file as an artifact: diff two calibration runs, run the checker from a shell
- the capstone: the whole bring-up in one run, writing a file per step and a calibration summary
  against the true device values
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
import json
import subprocess
import sys
import tempfile
from importlib.metadata import entry_points
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

import qprogram as qp
from qprogram import MeasurementField as MF
from qprogram.buses import BusSchema
from qprogram.operations.operation import Operation
from qprogram.serialization import ParseError
from qprogram.vendor import VendorNamespace
from qprogram.waveforms import IQDrag, IQPair, Square, Waveform

print("imports ready")

# %% [markdown]
r"""
## What we carry in from the earlier parts

The capstone at the end runs the whole bring-up, so the six cells below collect what the earlier
parts built: the device truth, the response models that stand in for the fridge, the pulse sequences
from Part 4, and two helpers that turn "one sweep, one fit" into two lines. Read them once; the
capstone is short because they exist.

The schema is the flux-tunable one this time. The custom waveform in 6.1 is a flux pulse, and a flux
pulse needs a single-channel bus to live on.
"""

# %%
DEVICE = {
    "q0_f01": 4.85e9,  # Hz, at the flux sweet spot
    "q0_fr": 7.20e9,  # Hz, readout resonator
    "q0_kappa": 1.5e6,  # Hz, resonator linewidth (FWHM)
    "q0_a_pi": 0.62,  # drive amplitude of a pi pulse (DAC units)
    "q0_T1": 18_000,  # ns
    "q0_T2star": 9_000,  # ns
    "q0_T2echo": 16_000,  # ns
    "q0_linewidth": 2.0e6,  # Hz, spectroscopy FWHM at low power
    "cz_g": 6.0e6,  # Hz, coupling to the neighbour
    "cz_amp_res": 0.42,  # flux amplitude that brings the pair into resonance
    "cz_slope": 1.2e9,  # Hz per unit flux amplitude
}
DETUNING = 0.5e6  # Hz, the detuning we put into the Ramsey on purpose
P_HOT = 0.22  # residual excited-state population before reset

schema = BusSchema.flux_tunable_transmon()
q = schema.q
PI = IQDrag(amplitude=DEVICE["q0_a_pi"], duration=40, sigma=10, beta=0.1)
X90 = IQDrag(amplitude=DEVICE["q0_a_pi"] / 2, duration=40, sigma=10, beta=0.1)

print("buses on this chip:", [q[0].drive, q[0].readout, q[0].flux])
print(f"pi pulse: IQDrag amplitude {PI.amplitude}, duration {PI.duration} ns")
print(f"pi/2 pulse: IQDrag amplitude {X90.amplitude}, duration {X90.duration} ns")

# %% [markdown]
r"""
The response models are the ones from Parts 2 to 4, unchanged. Each is a plain function of `env`, the
dict of loop variables currently bound. None of them is physics from first principles: they produce
the shapes a real scan produces, so the programs and the fits are the real part.

Active reset needs one that a `response` function cannot express, because the second measurement of a
shot depends on what the first one saw. That is the `ResetModel` in the cell after next. A
`MeasurementModel` is any object with a `sample(bus, env)` method and a `raw_samples` attribute, and
`sample` is called once per shot per measurement, in program order, so a model is free to remember.

What a model cannot do is watch the executor. It never learns which branch of a conditional ran. So
`ResetModel` assumes the program does the obvious thing, a pi pulse when the check reads 1, and
reproduces the outcome of that. The program in the capstone is the one it assumes.
"""

# %%
def s21(bus, env):
    """Resonator transmission: a dip at f_r, kappa wide."""
    detuning = (env["ro_freq"] - DEVICE["q0_fr"]) / (DEVICE["q0_kappa"] / 2)
    return 1.0 - 0.9 / (1.0 + 1j * detuning)


def p_spec(bus, env):
    """Qubit spectroscopy: excited-state population, a Lorentzian peak at f01."""
    hwhm = DEVICE["q0_linewidth"] / 2
    return 0.45 / (1.0 + ((env["drive_freq"] - DEVICE["q0_f01"]) / hwhm) ** 2)


def p_rabi(bus, env):
    return np.sin(np.pi * env["amp"] / (2 * DEVICE["q0_a_pi"])) ** 2


def p_t1(bus, env):
    return np.exp(-env["delay"] / DEVICE["q0_T1"])


def p_ramsey(bus, env):
    t = env["delay"]
    return 0.5 * (1.0 + np.cos(2 * np.pi * DETUNING * t * 1e-9)) * np.exp(-t / DEVICE["q0_T2star"])


def p_echo(bus, env):
    return 0.5 + 0.5 * np.exp(-env["delay"] / DEVICE["q0_T2echo"])


print("p_rabi at the pi amplitude:", round(p_rabi(None, {"amp": DEVICE["q0_a_pi"]}), 4))
print("p_t1 after one T1:", round(p_t1(None, {"delay": DEVICE["q0_T1"]}), 4))

# %%
class ResetModel:
    """Two measurements per shot: the check, then the verify, which remembers the check."""

    raw_samples = 1

    def __init__(self, p_hot, fidelity=0.97, seed=17):
        self.p_hot, self.fidelity = p_hot, fidelity
        self.rng = np.random.default_rng(seed)
        self.pending = None

    def sample(self, bus, env):
        if self.pending is None:  # the check
            state = int(self.rng.random() < self.p_hot)
            self.pending = state
        else:  # the verify: a hot qubit got the pi pulse, a cold one was left alone
            was, self.pending = self.pending, None
            state = int(self.rng.random() > self.fidelity) if was else int(self.rng.random() < 0.01)
        return qp.MeasurementSample(i=1.0 if state else -1.0, q=0.0, state=state, raw=np.zeros((1, 2)))


peek = ResetModel(p_hot=0.5)  # a hot qubit, so the pattern shows up in six shots
pairs = [(peek.sample(q[0].readout, {}).state, peek.sample(q[0].readout, {}).state) for _ in range(6)]
print("(check, verify) per shot:", pairs)

# %% [markdown]
r"""
Every experiment in the bring-up has the same skeleton: average, sweep one variable, do something,
measure. `sweep_program` writes that skeleton and hands back the program and the measurement handle.
`OUT` is where the capstone drops its files.
"""

# %%
OUT = Path("out/bringup")
OUT.mkdir(parents=True, exist_ok=True)


def sweep_program(label, var, source, middle, *, shots, fields):
    """average -> sweep(var) -> middle(program, var) -> measure, the shape of every scan here."""
    program = qp.QProgram(label=label, schema=schema)
    swept = program.variable(var)
    with program.average(shots=shots):
        with program.sweep(swept, source):
            middle(program, swept)
            handle = program.measure(q[0].readout, "readout", "weights", fields=fields)
    return program, handle


def magnitude(data):
    """|S21| from a `(..., IQ)` DataArray."""
    return np.abs(data.sel(IQ="I").values + 1j * data.sel(IQ="Q").values)


demo, _ = sweep_program(
    "smoke_test",
    "amp",
    qp.Linspace(0.0, 1.0, 3),
    lambda program, amp: program.play(q[0].drive, IQDrag(amp, 40, 10, 0.1)),
    shots=10,
    fields=(MF.STATE,),
)
print(qp.dumps(demo))

# %%
# The middles of the four experiments that need one: ordinary functions of the program and the swept
# variable, which is all `sweep_program` asks for.
def spec_tone(program, freq):
    program.set_frequency(q[0].drive, freq)
    program.play(q[0].drive, IQPair(Square(0.05, 2000), Square(0.0, 2000)))
    program.sync()


def t1_pulses(program, delay):
    program.play(q[0].drive, PI)
    program.wait(q[0].drive, delay)
    program.sync()


def ramsey_pulses(program, delay):
    program.play(q[0].drive, X90)
    program.wait(q[0].drive, delay)
    program.play(q[0].drive, X90)
    program.sync()


def echo_pulses(program, delay):
    program.play(q[0].drive, X90)
    program.wait(q[0].drive, delay / 2)
    program.play(q[0].drive, PI)  # the pi pulse that refocuses the detuning
    program.wait(q[0].drive, delay / 2)
    program.play(q[0].drive, X90)
    program.sync()


demo, _ = sweep_program("echo", "delay", qp.Range(0, 2000, 1000), echo_pulses, shots=1, fields=(MF.STATE,))
print("body:" + qp.dumps(demo).split("body:", 1)[1].rstrip())

# %% [markdown]
r"""
The fits are one line each. `step` puts everything together: build, save the `.qp` file, run, fit, and
keep the trace so the capstone can plot all six panels at once.
"""

# %%
def dip(f, f0, width, depth, base):
    return base - depth / (1.0 + ((f - f0) / (width / 2)) ** 2)


def peak(f, f0, hwhm, height, base):
    return base + height / (1.0 + ((f - f0) / hwhm) ** 2)


def rabi(a, a_pi):
    return np.sin(np.pi * a / (2 * a_pi)) ** 2


def decay(t, tau):
    return np.exp(-t / tau)


def fringe(t, t2, det):
    return 0.5 * (1.0 + np.cos(2 * np.pi * det * t * 1e-9)) * np.exp(-t / t2)


def half_decay(t, tau):
    return 0.5 + 0.5 * np.exp(-t / tau)


TRACES = {}


def step(name, var, source, middle, model, curve, p0, *, shots=200, field=MF.STATE):
    """Run one bring-up step, save it as `<name>.qp`, fit `curve`, and return the fitted values."""
    program, handle = sweep_program(name, var, source, middle, shots=shots, fields=(field,))
    qp.save(program, OUT / f"{name}.qp")
    data = qp.simulate(program, model=model).get(handle, field=field)
    x = data.coords[var].values
    y = data.values if field is MF.STATE else magnitude(data)
    popt, _ = curve_fit(curve, x, y, p0=p0, maxfev=40000)
    TRACES[name] = (x, y, curve, popt)
    return popt


print("rabi shape at a_pi/2 and a_pi:", rabi(np.array([0.31, 0.62]), 0.62).round(3))
print("decay shape after one tau:", round(float(decay(np.array([1.0]), 1.0)[0]), 3))

# %% [markdown]
r"""
## 6.1 Three extension points

QProgram has three seams for new vocabulary, and they are orthogonal. Nothing in the core knows any
vendor's name.

| You want | You write | You get for free |
|---|---|---|
| a pulse shape the DSL lacks | a `Waveform` subclass, `@qp.register_waveform` | `.qp` serialization from the constructor signature, structural equality, validation |
| a sweep axis the DSL lacks | a `SweepSource` subclass, `@qp.register_sweep_source` | serialization, a capability token, lockstep length checks, xarray coordinates |
| an operation the DSL will never have | an `Operation` plus a `VendorNamespace`, four registration calls | `program.<vendor>.<op>(...)`, a `require` line, a `vendor.<name>.<op>` token |

There is a fourth seam this notebook does not need: `qp.register_vendor_block` adds a block keyword
with its own indented suite, for a vendor that ships control flow of its own (a hardware infinite
loop, say). It follows the same pattern one level up.

Registration is global and keyed by class name, so each of the next three cells is a run-once cell.
Re-running one raises a collision error. Restart the kernel if you edit a class.

### A custom waveform

Flux-activated two-qubit gates want a pulse that starts and ends at zero, because a flux line that
jumps leaves the coupler ringing. A half sine does that with one parameter. Your vendor's compiler
may well emit it natively; the DSL has no name for it.

A `Waveform` owes two methods: `envelope(resolution)` returns the samples, `get_duration()` returns
the length in nanoseconds. `@qp.register_waveform` puts the class in the serialization registry under
its own name, and `qp.register_waveform_token` gives it a capability token, which is how a platform
gets to say whether it supports the shape.
"""

# %%
@qp.register_waveform
class HalfSine(Waveform):
    """A single half period of a sine: zero at both ends, no ringing on the flux line."""

    def __init__(self, amplitude: float, duration: int) -> None:
        self.amplitude, self.duration = amplitude, duration

    def envelope(self, resolution: int = 1) -> np.ndarray:
        n = self.duration // resolution
        return self.amplitude * np.sin(np.pi * np.arange(n) / n)

    def get_duration(self) -> int:
        return self.duration


qp.register_waveform_token(HalfSine, "waveform.half_sine")

plt.plot(HalfSine(amplitude=0.42, duration=40).envelope(), label="HalfSine(0.42, 40)")
plt.plot(Square(amplitude=0.42, duration=40).envelope(), label="Square(0.42, 40)")
plt.xlabel("Time (ns)")
plt.ylabel("Flux amplitude (DAC units)")
plt.title("A shape the core does not ship")
plt.legend()
plt.show()

# %% [markdown]
r"""
### A custom sweep source

A chevron scan is always written the same way in a lab notebook: a centre, a span, and how many
points. `Range` and `Linspace` want endpoints, so every script grows the same two lines of
arithmetic. A sweep source removes them.

The contract is three declarations, and each has a real consumer:

- `length()` is static. A parallel loop checks it before anything runs, and the executor sizes the
  result array with it.
- `KIND` is `"linear"` or `"arbitrary"`. It is a claim about compilability: a sequencer can generate a
  linear ramp in hardware, and everything else has to be uploaded as a table.
- `values()` produces the numbers, for the interpreter, for the xarray coordinate, and for
  `optimize()`.

A source may not wrap a callable. If it did, it could answer none of those three before the program
runs, and it could not serialize.
"""

# %%
@qp.register_sweep_source
class Chevron(qp.SweepSource):
    """A symmetric scan around a centre, the way a chevron gets written on a whiteboard."""

    KIND = "arbitrary"
    TOKEN = "sweep.chevron"

    def __init__(self, center: float, span: float, num: int) -> None:
        self.center, self.span, self.num = center, span, num

    def length(self) -> int:
        return self.num

    def values(self):
        return np.linspace(self.center - self.span / 2, self.center + self.span / 2, self.num)


scan = Chevron(center=0.42, span=0.20, num=21)
print("length:", scan.length(), " kind:", scan.KIND)
print("tokens it asks a platform for:", sorted(scan.tokens()))
print("first three values:", scan.values()[:3].round(3))
# A combinator unions its child's tokens with its own, so a platform missing `sweep.chevron`
# refuses the rotation too.
print("wrapped in Rotate:", sorted(qp.Rotate(scan, 5).tokens()))

# %% [markdown]
r"""
### A whole vendor namespace

The two seams above add vocabulary the core could plausibly have shipped. The third is for things the
core must never ship. Our fridge has a programmable room-temperature attenuator on the drive line. It
is one box in one rack, and `op.set_attenuation` has no business in a vendor-agnostic DSL.

Four calls put it in the language anyway:

1. `QProgram.register_vendor` makes `program.fridge` resolve at runtime, on any `QProgram`.
2. `register_vendor_version` fixes the version that goes into the `require` line.
3. `register_vendor_operation` teaches the writer and the parser about the operation. The default
   parser reads your `__init__` signature, so there is nothing else to write.
4. `register_capability_tokens` puts the token in the registry, which is what lets a platform say yes
   or no to it.

A shipped extension does all four in its package `__init__.py`. Importing the package is the
activation step.
"""

# %%
class SetAttenuation(Operation):
    """Set the room-temperature attenuator on a drive line, in dB."""

    def __init__(self, bus: str, db: float) -> None:
        self.bus, self.db = bus, db

    def required_capabilities(self) -> set[str]:
        return {"vendor.fridge.set_attenuation"}


class FridgeNamespace(VendorNamespace):
    def set_attenuation(self, bus: str, db: float) -> None:
        self._append(SetAttenuation(bus=bus, db=db))


qp.QProgram.register_vendor("fridge", FridgeNamespace)
qp.register_vendor_version("fridge", "0.1.0")
qp.register_vendor_operation("fridge", "set_attenuation", SetAttenuation)
qp.register_capability_tokens("vendor.fridge.set_attenuation")

# `_vendor_registry` is private and there is no public accessor for it yet. Reading it here is a
# look behind the curtain, not an API to build on.
print("vendor namespaces registered:", sorted(qp.QProgram._vendor_registry))
print("SetAttenuation asks for:", SetAttenuation(q[0].drive, 20.0).required_capabilities())

# %% [markdown]
r"""
### All three in one program

A chevron scan of a flux-activated swap: attenuate the drive line, then step the flux amplitude
around the resonance point and read the qubit out. The custom waveform, the custom sweep source,
and the vendor operation all appear in the `.qp` text, and the file grew a `require fridge 0.1` line
under the header.

That line is the contract. A lab without the extension installed gets a `ParseError` naming the
vendor it is missing, instead of a file that loads with an operation silently dropped.

The file also round-trips. The parser rebuilds `HalfSine`, `Chevron`, and `fridge.set_attenuation`
from the text with no help from you, because each is registered under its class name and serialized
from its constructor signature. And the reference platform accepts every token in the registry, so
the program validates and runs: the swap probability peaks where the two qubits come into resonance,
which is the number a chevron scan exists to find.
"""

# %%
program = qp.QProgram(label="cz_chevron", description="flux-activated swap on the fridge rack", schema=schema)
flux_amp = program.variable("flux_amp", label="Flux amplitude", units="V")

program.fridge.set_attenuation(q[0].drive, 20.0)
with program.average(shots=200):
    with program.sweep(flux_amp, Chevron(center=0.42, span=0.20, num=21)):
        program.play(q[0].flux, HalfSine(amplitude=flux_amp, duration=40))
        program.sync()
        swap = program.measure(q[0].readout, "readout", "weights", fields=(MF.STATE,))

text = qp.dumps(program)
print(text)
print("round-trips:", qp.loads(text).body == program.body)
print("diagnostics from the reference platform:", qp.validate(program, qp.reference_capabilities())[0])


def p_swap(bus, env):
    """Swap probability after a 40 ns half-sine flux pulse of the given amplitude."""
    delta = (env["flux_amp"] - DEVICE["cz_amp_res"]) * DEVICE["cz_slope"]
    omega = np.sqrt((2 * DEVICE["cz_g"]) ** 2 + delta**2)
    contrast = (2 * DEVICE["cz_g"]) ** 2 / omega**2
    return contrast * np.sin(np.pi * omega * 40 * 1e-9) ** 2


data = qp.simulate(program, model=qp.MockMeasurementModel(p_excited=p_swap, seed=21)).get(swap, field=MF.STATE)
amps = data.coords["flux_amp"].values
print(f"swap peaks at {amps[data.values.argmax()]:.3f}, resonance is at {DEVICE['cz_amp_res']:.3f}")

# %% [markdown]
r"""
### The token is the whole point

Registering a token does not mean every rack has the box. Build a platform descriptor that knows
everything except our attenuator, and the validator says what is missing and where.

This is the difference between an extension and a fork. The program stays legal QProgram, the file
stays loadable, and the machine that cannot run it says so before anything is uploaded.
"""

# %%
from qprogram.protocol import CAPABILITY_REGISTRY

no_fridge = frozenset(CAPABILITY_REGISTRY) - {"vendor.fridge.set_attenuation"}
profile = qp.CompilerCapabilities(
    profile="no-fridge", version=(0, 1, 0), capabilities=no_fridge, limits={}, predicates=(), vendor_versions={}
)
plain_rack = qp.BusCapabilities(rt=profile, host=profile)
caps = qp.PlatformCapabilities(bus={}, platform=plain_rack, default_bus_profile=plain_rack)

for d in qp.validate(program, caps)[0]:
    print(f"[{d.severity}] {d.code}: {d.message}")
    print("  at path:", qp.format_path(d.path))
print()
print(qp.explain(program, caps))

# %% [markdown]
r"""
## 6.2 Vendor packages for real

Everything above lived in a notebook cell. A shipped extension is a separate Python package that
depends on `qprogram` and makes the same registration calls at import time. Two of them live in the
QProgram repository as worked examples: `qprogram-qblox` (six sequencer operations, `qblox.acquire`
with its own weights among them) and `qprogram-qdac` (a slow DC source, whose profile ships a
predicate that pushes any qdac operation reading a swept variable to host-side dispatch, one
iteration at a time). Neither is needed for this tutorial and neither is installed here.

A real package takes one extra step. It declares an entry point:

```toml
[project.entry-points."qprogram.vendors"]
qblox = "qprogram_qblox"
```

Now `loads()` can activate the extension on demand. When it reaches a `require qblox 0.1` line for a
vendor that is not registered yet, it looks up that entry-point group, imports the module, and the
registration side effects run. A six-month-old `.qp` file loads in a fresh interpreter without the
reader knowing which extensions it needs. If nothing claims the vendor, the error names it.

Version compatibility is checked at major.minor: the file's major must equal the installed
extension's major, and the file's minor must be less than or equal to the installed minor. Patch is
informational, and the writer truncates it.
"""

# %%
installed = {ep.name: ep.value for ep in entry_points(group="qprogram.vendors")}
print("vendor entry points installed in this environment:", installed or "none")
print("vendor namespaces registered right now:", sorted(qp.QProgram._vendor_registry))
print("auto-activation of a vendor nobody claims:", qp.try_activate_vendor("qblox"))

needs_qblox = '#!QProgram 1.0\n\nrequire qblox 0.1\n\nbody:\n  qblox.acquire "readout" "weights" name="m0"\n'
try:
    qp.loads(needs_qblox)
except ParseError as error:
    print("\nloading a file that requires an absent vendor:")
    print(" ", error)
else:
    print("\nqprogram-qblox is installed here, so the file loaded.")

# %% [markdown]
r"""
### 🧩 Exercise 6.1: a vendor measurement field

A photon-counting readout does not return an IQ point. It returns counts. The measurement field
vocabulary extends through the same registry: register `measure.fields.counts` and
`fields=("counts",)` becomes legal at the call site, in the `.qp` text, and in validation.

Your job:

1. Register the token `measure.fields.counts`.
2. Build a small program that measures with `fields=("counts", MF.STATE)` and print the body of its
   `.qp` text.
3. Validate it against `qp.reference_capabilities()` and show there are no diagnostics.
4. Validate it against a profile that lacks the token and print the error.
5. Run it, read the `counts` field back, and explain in a comment why it is zero.
"""

# %% solution
qp.register_capability_tokens("measure.fields.counts")

counting = qp.QProgram(label="photon_counting", schema=schema)
with counting.average(shots=8):
    clicks = counting.measure(q[0].readout, "readout", "weights", fields=("counts", MF.STATE))
print("body:" + qp.dumps(counting).split("body:", 1)[1].rstrip())

print("\nreference platform:", qp.validate(counting, qp.reference_capabilities())[0])

no_counts = frozenset(CAPABILITY_REGISTRY) - {"measure.fields.counts"}
strict = qp.CompilerCapabilities(
    profile="iq-only", version=(0, 1, 0), capabilities=no_counts, limits={}, predicates=(), vendor_versions={}
)
strict_bus = qp.BusCapabilities(rt=strict, host=strict)
strict_caps = qp.PlatformCapabilities(bus={}, platform=strict_bus, default_bus_profile=strict_bus)
for d in qp.validate(counting, strict_caps)[0]:
    print("iq-only rack:", d.code, "-", d.message)

counted = qp.simulate(counting, model=qp.MockMeasurementModel(p_excited=lambda bus, env: 0.3, seed=5))
# The token makes the field legal and the executor allocates the array, but the reference platform
# has no idea how to produce counts, so it leaves them at zero. A real compiler is what fills it in.
print("counts:", counted.get(clicks, field="counts").values)
print("state: ", counted.get(clicks, field=MF.STATE).values)

# %% stub
# TODO: add a vendor measurement field and prove it is legal on one rack and not on another.
# 1) qp.register_capability_tokens("measure.fields.counts")
# 2) Build a program with fields=("counts", MF.STATE) and print the body of its .qp text.
# 3) qp.validate(program, qp.reference_capabilities()) should return no diagnostics.
# 4) Build a CompilerCapabilities whose capabilities are the registry minus that one token, wrap it
#    in BusCapabilities / PlatformCapabilities, validate again, and print the error.
# 5) Simulate it, print the counts field, and say in a comment why it is zero.

# %% [markdown]
r"""
## 6.3 The `.qp` file is the artifact

A calibration is not a plot. It is the program that produced the plot, and the numbers that came out.
QProgram writes the program as line-oriented text, so the ordinary tools work on it: `diff`, code
review, `git blame`, and a checker you can run in CI.

Here are two runs of the same Rabi experiment, a Monday and a Friday. Somebody changed three things.
A diff of the two `.qp` files says which three, in the language of the experiment rather than in
sequencer opcodes.
"""

# %%
scratch = Path(tempfile.mkdtemp(prefix="qp-artifacts-"))


def rabi_run(label, a_stop, ro_freq, shots):
    program = qp.QProgram(label=label, schema=schema)
    amp = program.variable("amp", label="Drive amplitude")
    program.set_frequency(q[0].readout, ro_freq)
    with program.average(shots=shots):
        with program.sweep(amp, qp.Linspace(0.0, a_stop, 41)):
            program.play(q[0].drive, IQDrag(amplitude=amp, duration=40, sigma=10, beta=0.1))
            program.sync()
            program.measure(q[0].readout, "readout", "weights", fields=(MF.STATE,))
    return program


qp.save(rabi_run("rabi", 1.0, 7.2000e9, 200), scratch / "rabi_monday.qp")
qp.save(rabi_run("rabi", 0.8, 7.2004e9, 400), scratch / "rabi_friday.qp")

monday = (scratch / "rabi_monday.qp").read_text().splitlines(keepends=True)
friday = (scratch / "rabi_friday.qp").read_text().splitlines(keepends=True)
print("".join(difflib.unified_diff(monday, friday, "rabi_monday.qp", "rabi_friday.qp", n=1)))

# %% [markdown]
r"""
### A checker you can run in CI

`python -m qprogram.lsp check <file>` parses the file with the production parser, validates the
result against the reference platform, and prints JSON diagnostics. It exits 1 when it finds any, so
it drops into a pre-commit hook or a CI job. No extra dependencies.

Break the Friday file the way a hand edit breaks a file: misspell a bus. The message comes back with
the line number, the path that failed to resolve, and the buses the chip does have, because the `.qp`
file declares its own schema. A checker that knows the layout can tell a typo from a bus that
genuinely does not exist.

The same module has two more modes. `explain` prints the execution plan as a tree straight from a
shell, which is the fastest way to answer "why is this loop running host-side". `serve` speaks LSP
over stdio and needs the `qprogram[lsp]` extra. The VS Code extension that ships in the QProgram
repository (`editors/vscode-qp/`) is plain JavaScript with no build step: it highlights `.qp`, runs
`check` on open, on save, and debounced while you type, and adds a `qp: Explain execution plan`
command.
"""

# %%
broken = scratch / "rabi_broken.qp"
broken.write_text((scratch / "rabi_friday.qp").read_text().replace("q[0].drive", "q[0].drve"))

for mode, target in (("check", broken), ("explain", scratch / "rabi_friday.qp")):
    done = subprocess.run(
        [sys.executable, "-m", "qprogram.lsp", mode, str(target)],
        capture_output=True, text=True, check=False,
    )
    print(f"$ python -m qprogram.lsp {mode} {target.name}   (exit {done.returncode})")
    if mode == "check":
        for d in json.loads(done.stdout):
            print(f"  line {d['line'] + 1}: [{d['severity']}] {d['code']}: {d['message']}")
    else:
        print(done.stdout)

# %% [markdown]
r"""
### 🧩 Exercise 6.2: fix a file with the checker

Somebody hand-edited a `.qp` file and broke it in two places. Find and fix both using nothing but the
checker output, then prove the repaired file is the program you started from.

Your job:

1. Take the `cz_chevron` program from 6.1, serialize it, and break it twice: turn `average` into
   `avarage` and `q[0].flux` into `q[0].flx`.
2. Loop: call `qprogram.lsp.check_text` on the current text, print the first diagnostic with its
   1-based line number, use the reported line to decide which repair applies, and apply it.
3. Stop when the checker returns nothing, then check that the reparsed program's `body` equals the
   original.

The parser stops at the first error, so it takes one round per break plus one more to see a clean
file. That is what the loop is for.
"""

# %% solution
from qprogram.lsp import check_text

repairs = {"avarage": "average", "flx": "flux"}
edited = qp.dumps(program).replace("average", "avarage").replace("q[0].flux", "q[0].flx")

for attempt in range(1, 5):
    found = check_text(edited)
    if not found:
        print(f"round {attempt}: clean")
        break
    first = found[0]
    print(f"round {attempt}: line {first.line + 1}: {first.message}")
    culprit = edited.splitlines()[first.line]
    for wrong, right in repairs.items():
        if wrong in culprit:
            edited = edited.replace(wrong, right, 1)

print("repaired file matches the original:", qp.loads(edited).body == program.body)

# %% stub
# TODO: break a .qp file twice and repair it from the checker output alone.
# 1) edited = qp.dumps(program), with "average" -> "avarage" and "q[0].flux" -> "q[0].flx"
# 2) from qprogram.lsp import check_text
# 3) Loop up to four times: call check_text(edited); if it returns nothing, print "clean" and stop.
#    Otherwise print the first diagnostic's 1-based line and message, look at that line of `edited`,
#    and apply whichever repair matches ({"avarage": "average", "flx": "flux"}).
# 4) Print whether qp.loads(edited).body == program.body.

# %% [markdown]
r"""
## 6.4 Toward hardware

Everything you ran today went through `ReferencePlatform`. A vendor platform is the same interface
with a compiler behind it. `PlatformProtocol` has six abstract members and asks for nothing else:

| member | what it answers |
|---|---|
| `get_bus_schema()` | which chip this rack is wired to |
| `get_buses()` | the bus names it exposes |
| `get_parameters(bus)` | the knobs on one bus |
| `get_global_parameters()` | the knobs that belong to no bus |
| `capabilities` | what it can and cannot do, as tokens, limits, and predicates |
| `execute(program)` | run it and return a `QProgramResult` |

`validate`, `plan`, and `explain` come with default implementations that delegate to the core
validator, so a platform gets structured diagnostics without writing any. `stream` is optional.

What a real platform does between `execute` and the result is the part QProgram deliberately does not
specify: lower the AST to its sequencer language, allocate registers and waveform memory, upload, arm
the triggers, start the acquisition, stream partial results back, and assemble the same xarray
shapes. The reference executor is the oracle for that last step. It defines what the result of a
program means, so a vendor compiler can be tested by running the same program both ways and comparing
the arrays. It models no timing and no waveform physics, and that is deliberate: it is the semantics
of the language, not a simulator of your fridge.
"""

# %%
print("must implement:", sorted(qp.PlatformProtocol.__abstractmethods__))
print("provided by default: validate, plan, explain; optional: stream")

reference = qp.ReferencePlatform(schema=schema, parameters={"q0/drive.attenuation": 20.0})
print("\nbuses:", reference.get_buses())
print("parameters on q0/drive:", reference.get_parameters(q[0].drive))
print("tokens in its platform slot:", len(reference.capabilities.platform.rt.capabilities))
print("errors from validate on the chevron program:", reference.validate(program))

# %% [markdown]
r"""
## 6.5 Capstone: the whole bring-up in one run

Seven steps, in the order a real chip gets brought up, each one a program saved as a `.qp` file:

1. **Resonator spectroscopy.** Find the readout frequency. Nothing else works without it.
2. **Qubit spectroscopy.** A long saturation tone, and the population tells you where f01 is.
3. **Rabi.** Sweep the drive amplitude and read the pi amplitude off the fit.
4. **T1.** Invert, wait, measure.
5. **Ramsey.** Two pi/2 pulses with a deliberate detuning, which gives T2\* and the frequency error.
6. **Hahn echo.** A pi pulse in the middle refocuses the detuning, which gives T2.
7. **Active reset.** Measure, and play a pi pulse only if the qubit came back excited.

Steps 4 to 6 drive with the pi pulse step 3 just fitted, not with the seed pulse from the top of the
notebook. Feeding each step into the next is the reason to run a bring-up as one script.

The delays in steps 4 to 6 change the result only because the measurement model reads
`env["delay"]`. The reference executor has no timing model. On hardware the delay is the physics;
here it is an argument.

Three cells: two to run it, one to report. Short because `step` does the repetitive part.
"""

# %%
CAL = {}

f_r, _, _, _ = step(
    "01_resonator", "ro_freq", qp.Linspace(7.19e9, 7.21e9, 81),
    lambda program, freq: program.set_frequency(q[0].readout, freq),
    qp.MockMeasurementModel(response=s21, noise=0.01, seed=11),
    dip, p0=(7.2e9, 1e6, 0.9, 1.0), field=MF.IQ,
)
CAL["f_r (GHz)"] = (f_r / 1e9, DEVICE["q0_fr"] / 1e9)

f_01, _, _, _ = step(
    "02_qubit", "drive_freq", qp.Linspace(4.84e9, 4.86e9, 81), spec_tone,
    qp.MockMeasurementModel(p_excited=p_spec, seed=12), peak, p0=(4.85e9, 1e6, 0.45, 0.0),
)
CAL["f_01 (GHz)"] = (f_01 / 1e9, DEVICE["q0_f01"] / 1e9)

(a_pi,) = step(
    "03_rabi", "amp", qp.Linspace(0.0, 1.0, 41),
    lambda program, amp: program.play(q[0].drive, IQDrag(amp, 40, 10, 0.1)),
    qp.MockMeasurementModel(p_excited=p_rabi, seed=13), rabi, p0=(0.5,),
)
CAL["a_pi (DAC)"] = (a_pi, DEVICE["q0_a_pi"])
print(f"resonator {f_r / 1e9:.5f} GHz, qubit {f_01 / 1e9:.5f} GHz, pi amplitude {a_pi:.4f}")

# %%
PI = IQDrag(round(a_pi, 4), 40, 10, 0.1)  # the pulse step 3 fitted, replacing the seed pulse
X90 = IQDrag(round(a_pi / 2, 4), 40, 10, 0.1)

(T1,) = step("04_t1", "delay", qp.Range(0, 45000, 1500), t1_pulses,
             qp.MockMeasurementModel(p_excited=p_t1, seed=14), decay, p0=(10_000.0,))
T2star, detuning = step("05_ramsey", "delay", qp.Range(0, 12000, 200), ramsey_pulses,
                        qp.MockMeasurementModel(p_excited=p_ramsey, seed=15), fringe, p0=(8000.0, 0.5e6))
(T2echo,) = step("06_echo", "delay", qp.Range(0, 32000, 1000), echo_pulses,
                 qp.MockMeasurementModel(p_excited=p_echo, seed=16), half_decay, p0=(10_000.0,))
CAL["T1 (us)"] = (T1 / 1000, DEVICE["q0_T1"] / 1000)
CAL["T2* (us)"] = (T2star / 1000, DEVICE["q0_T2star"] / 1000)
CAL["detuning (MHz)"] = (abs(detuning) / 1e6, DETUNING / 1e6)
CAL["T2 echo (us)"] = (T2echo / 1000, DEVICE["q0_T2echo"] / 1000)
print(f"T1 {T1 / 1000:.2f} us, T2* {T2star / 1000:.2f} us, T2 echo {T2echo / 1000:.2f} us")

reset = qp.QProgram(label="07_reset", schema=schema)
with reset.average(shots=1000):
    checked = reset.measure(q[0].readout, "readout", "weights", name="check", fields=(MF.STATE,))
    with reset.if_(checked.state == 1):
        reset.play(q[0].drive, PI)
    reset.sync()
    verified = reset.measure(q[0].readout, "readout", "weights", name="verify", fields=(MF.STATE,))
qp.save(reset, OUT / "07_reset.qp")

outcome = qp.simulate(reset, model=ResetModel(p_hot=P_HOT, seed=7))
before = float(outcome.get(checked, field=MF.STATE).values)
after = float(outcome.get(verified, field=MF.STATE).values)
print(f"excited population: {before:.3f} before reset ({P_HOT} in the model), {after:.3f} after")

# %% [markdown]
r"""
Now the report. The calibration table is the deliverable: what you measured next to what the device
actually is, so you can see which numbers to trust. The fitted pulses go out beside it in a `.wfl`
library, so tomorrow's run loads today's numbers from a file instead of from a literal somebody
pasted into a script.
"""

# %%
library = qp.WaveformLibrary()
library.set("pi", PI, element="q", idx=0, kind="drive")  # exactly what steps 4 to 6 played
library.set("x90", X90, element="q", idx=0, kind="drive")
library.set("readout", IQPair(Square(0.2, 2000), Square(0.0, 2000)), element="q", kind="readout")
library.set("weights", IQPair(Square(1.0, 2000), Square(1.0, 2000)))
library.save(OUT / "calibration.wfl")

print(f"{'quantity':<18}{'measured':>12}{'true':>12}{'error':>9}")
for name, (measured, truth) in CAL.items():
    print(f"{name:<18}{measured:>12.4f}{truth:>12.4f}{100 * abs(measured - truth) / abs(truth):>8.1f}%")
print(f"\nartifacts in {OUT.resolve()}:")
print(" ", sorted(p.name for p in OUT.iterdir()))

fig, axes = plt.subplots(2, 3, figsize=(12, 5.5))
for ax, (name, (x, y, curve, popt)) in zip(axes.ravel(), TRACES.items(), strict=False):
    ax.plot(x, y, ".", ms=4, label="measured")
    ax.plot(x, curve(x, *popt), "-", lw=1.5, label="fit")
    ax.set_title(name, fontsize=9)
axes[0, 0].legend(fontsize=8)
fig.tight_layout()
plt.show()

# %% [markdown]
r"""
## Recap and what is next

- Three extension seams cover new vocabulary: a `Waveform`, a `SweepSource`, and a vendor
  `Operation` behind a `VendorNamespace`. Each is a class plus a registration call, and each gets
  serialization, validation, and a capability token without any change to the core. A fourth,
  `register_vendor_block`, does the same for a vendor's own control flow.
- The token is what makes an extension safe. A rack that lacks it refuses the program with a named
  diagnostic and a path, before anything reaches an instrument.
- Entry points make a `.qp` file self-describing. The `require` line names the vendor, and `loads()`
  imports the extension that claims it.
- The `.qp` file is the artifact you keep. It diffs, it reviews, and `python -m qprogram.lsp check`
  turns it into a CI job.
- The capstone recovered f_r, f01, the pi amplitude, T1, T2\*, the detuning, and T2 from simulated
  data, wrote a file per step, and put the fitted pulses in a `.wfl` library. That directory is a
  calibration another lab could load.

Where to read more, all in the QProgram repository: `.specs/qprogram-dsl.md` is the normative
specification, `.specs/qp-file-format.md` covers the text format, `grammar/qp.lark` is the
machine-readable grammar, and `qprogram-qblox` is the smallest complete vendor extension worth
copying.

One idea to carry forward: the program, the plan, and the calibration are all data. Anything you can
serialize, you can diff, review, check in CI, and hand to a different machine. That is the argument
for a pulse-level DSL that is not a string builder.
"""
