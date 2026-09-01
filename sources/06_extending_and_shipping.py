# %% [markdown]
r"""
# 06 · Extending the language and shipping the work

Five parts in, every program you wrote used operations, waveforms, and sweep sources that ship with
QProgram. Real labs run out of those on day one. Someone has a pulse shape their vendor's compiler
already knows and the DSL does not. Someone drives a room-temperature attenuator that no core
operation will ever cover. Someone scans a chevron by centre and span instead of start and stop.

What happens next decides whether any of Part 5 was true. A control DSL that cannot be extended gets
forked, and a forked DSL is not a portable format any more, it is three dialects with the same file
extension. Lab A patches in its attenuator, lab B patches in its pulse shape, and the `.qp` file
that was supposed to move between them now loads in one interpreter and raises in the other, or
worse, loads in both and means different things.

So the extension points are not a convenience feature. They are the thing that keeps the format
worth having.

- register a **waveform**, a **sweep source**, and a whole **vendor namespace**, live in this
  notebook
- watch the `require` line appear in the `.qp` text, and watch a rack that lacks the token refuse
  the program
- treat the `.qp` file as an artifact: diff two calibration runs, run the checker from a shell
- run the whole bring-up as one capstone, writing a file per step and a calibration summary
  against the true device values
"""

# %%
# Run me first. A no-op when qprogram is already installed, an install when it is not
# (a fresh Google Colab runtime, for example).
# Section 6.2 loads a file that requires the qblox vendor, and the point of that cell is the import
# happening on demand. So probe for the distributions rather than importing them here.
from importlib.util import find_spec

if find_spec("qprogram") is None or find_spec("qprogram_qblox") is None:
    import subprocess
    import sys

    subprocess.run(
        [
            sys.executable, "-m", "pip", "install",
            "qprogram[viz]==0.1.0", "qprogram-qblox==0.1.0", "qprogram-qdac==0.1.0", "scipy",
        ],
        check=True,
    )

from importlib.metadata import version

print("qprogram", version("qprogram"))
print("qprogram-qblox", version("qprogram-qblox"), "· qprogram-qdac", version("qprogram-qdac"))

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
The response models are the ones from Parts 2 to 4, unchanged. Each is a plain function of `env`,
the dict of loop variables currently bound. None of them is physics from first principles. They
produce the shapes a real scan produces, so the programs and the fits are the real part.

Active reset needs one that a `response` function cannot express, because the second measurement of
a shot depends on what the first one saw. That is the `ResetModel` in the cell after next. A
`MeasurementModel` is any object with a `sample(bus, env)` method, and `sample` is called once per
shot per measurement, in program order, so a model is free to remember. A model that simulates an
ADC also declares `raw_samples` and fills in the sample's `raw` trace. One that does not, like every
model in this notebook, leaves both out and `MeasurementSample.raw` keeps its empty default.

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
        return qp.MeasurementSample(i=1.0 if state else -1.0, q=0.0, state=state)


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
The fits are one line each. `step` puts everything together: build, save the `.qp` file, run, fit,
and keep the trace so the capstone can plot all six panels at once.
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

The "for free" column is where the design lives, and it is bought with one constraint you should
know up front. Serialization is derived by reading your `__init__` signature, so the constructor
arguments have to *be* the object's state. Store a parameter under a different attribute name, or
compute state that the constructor cannot reproduce, and the round trip breaks in a way nothing
warns you about until a file comes back different from the program that wrote it.

There is a fourth seam this notebook does not need: `qp.register_vendor_block` adds a block keyword
with its own indented suite, for a vendor that ships control flow of its own (a hardware infinite
loop, say). It follows the same pattern one level up.

Registration is global and keyed by class name, so each of the next three cells is a run-once cell.
Re-running one raises a collision error. Restart the kernel if you edit a class.

### A custom waveform

Flux-activated two-qubit gates want a pulse that starts and ends at zero. Part 1 explained why: a
flux line through a fridge is a filter with time constants in the microseconds and longer, so any
step you leave at the end of a pulse comes back as a slow tail, and the next gate in the circuit
runs on a chip the previous gate detuned. A half sine does that with one parameter.

Being precise about what it buys: a half sine is zero at both endpoints, so there is no step. Its
slope at the endpoints is not zero, so it is continuous but not smooth, and labs chasing the last
percent reach for a raised cosine instead. The half sine is the shape you write first, and your
vendor's compiler may well emit it natively. The DSL has no name for it.

A `Waveform` owes two methods. `envelope(resolution)` returns the samples and `get_duration()`
returns the length in nanoseconds. `@qp.register_waveform` puts the class in the serialization
registry under its own name, and `qp.register_waveform_token` gives it a capability token, so a
platform gets to say whether it supports the shape.

One rule travels with those two methods. A parameter you intend to sweep is annotated
`float | qp.Expression` and resolved with `evaluate_or_raise()` at the point of use, because the
program later in this section puts a swept variable in the amplitude position and a bare
multiplication would meet a `Variable` instead of a number. Every shape the core ships is written
this way. Skipping it costs nothing until a real platform calls `envelope()`, and then it fails
inside numpy with a message that names neither the waveform nor the variable.
"""

# %%
@qp.register_waveform
class HalfSine(Waveform):
    """A single half period of a sine: zero at both ends, no ringing on the flux line."""

    def __init__(self, amplitude: float | qp.Expression, duration: int) -> None:
        self.amplitude, self.duration = amplitude, duration

    def envelope(self, resolution: int = 1) -> np.ndarray:
        amplitude = self.amplitude
        if isinstance(amplitude, qp.Expression):  # bound by the sweep this pulse sits in
            amplitude = amplitude.evaluate_or_raise()
        n = self.duration // resolution
        return amplitude * np.sin(np.pi * np.arange(n) / n)

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

A chevron scan is always written the same way in a lab notebook. A centre, a span, and how many
points. `Range` and `Linspace` want endpoints, so every script grows the same two lines of
arithmetic. A sweep source removes them.

The contract is three declarations, and each has a real consumer:

- `length()` is static. A parallel loop checks it before anything runs, and the executor sizes the
  result array with it.
- `KIND` is `"linear"` or `"arbitrary"`. It is a claim about compilability. A sequencer can generate
  a linear ramp in hardware, and everything else has to be uploaded as a table.
- `values()` produces the numbers, for the interpreter, for the xarray coordinate, and for
  `optimize()`.

A source may not wrap a callable, and that restriction is the whole design in one line, so it is
worth the five minutes. Imagine `Callable(lambda i: ...)` as a source. It could not answer
`length()` without running, so a lockstep pair could not be checked at build time and the result
array could not be allocated before the first shot. It could not honestly declare a `KIND`, so every
sweep would fall back to arbitrary and no loop would ever compile into a register. And it could not
serialize, so a `.qp` file holding one would either carry a pickled closure or quietly lose the
sweep. Three properties, all of them load-bearing, all of them gone. The rule looks like a
limitation and it is the reason the format works.
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

The two seams above add vocabulary the core could plausibly have shipped. The third is for things
the core must never ship. Our fridge has a programmable room-temperature attenuator on the drive
line. It is one box in one rack, and `op.set_attenuation` has no business in a vendor-agnostic DSL.

Four calls put it in the language anyway:

1. `QProgram.register_vendor` makes `program.fridge` resolve at runtime, on any `QProgram`.
2. `register_vendor_version` fixes the version that goes into the `require` line.
3. `register_vendor_operation` teaches the writer and the parser about the operation. The default
   parser reads your `__init__` signature, so there is nothing else to write.
4. `register_capability_tokens` puts the token in the registry, so a platform can say yes or no to
   it.

A shipped extension does all four in its package `__init__.py`, and one more besides. A token says
an operation exists. A profile is the bundle a rack points at to say which tokens it has, under a
name and a version that outlive the cell they were declared in. The subsection after next builds
one.

Importing the package is the activation step for all five.
"""

# %%
class SetAttenuation(Operation):
    """Set the room-temperature attenuator on a drive line, in dB."""

    def __init__(self, bus: str, db: float) -> None:
        self.bus, self.db = bus, db

    def required_capabilities(self) -> set[str]:
        return {"vendor.fridge.set_attenuation"}


class FridgeNamespace(qp.VendorNamespace):
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

The program is a chevron scan of a flux-activated swap, and it is worth knowing what that experiment
does before reading the code. Two qubits sitting at different frequencies barely interact. Push one
of them with a flux pulse until it lands on the other and the pair exchanges excitations at a rate
set by their coupling $g$. Sweep the flux amplitude around the resonance point and the swap
probability after a fixed 40 ns pulse follows the detuned Rabi formula,

$$P_{\text{swap}} = \frac{(2g)^2}{\Omega^2}\sin^2(\pi \Omega t),
\qquad \Omega = \sqrt{(2g)^2 + \Delta^2}$$

with $\Delta$ the residual detuning, proportional to how far the flux amplitude sits from resonance.
On resonance the prefactor is 1 and the pair swaps completely. Off resonance the oscillation goes
faster and reaches less far, which is the pattern that gives a chevron its name once you add the
duration axis. `p_swap` below is that formula, and the amplitude at the peak is the number the scan
exists to find.

The program attenuates the drive line, then steps the flux amplitude and reads the qubit out. The
custom waveform, the custom sweep source, and the vendor operation all appear in the `.qp` text, and
the file grew a `require fridge 0.1` line under the header.

That line is the contract. A lab without the extension installed gets a `ParseError` naming the
vendor it is missing, instead of a file that loads with an operation silently dropped.

The file also round-trips. The parser rebuilds `HalfSine`, `Chevron`, and `fridge.set_attenuation`
from the text with no help from you, because each is registered under its class name and serialized
from its constructor signature. And the reference platform accepts every token in the registry, so
the program validates and runs.
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
stays loadable, and the machine that cannot run it says so before anything is uploaded. A fork would
have given you the same working program on your own rack and a syntax error on everybody else's.
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
### Publishing the token set instead of the tokens

The descriptor above was assembled by subtracting one token from the live registry, and so was every
rack in Part 5. That works in a notebook and is useless as a way to describe a real machine, because
"everything the installed language knows about, minus one" is a claim that changes every time
somebody installs a package.

A shipped extension publishes a `qp.Profile` instead: a named and versioned bundle of tokens,
limits, and predicates. From then on any rack reaches it by name through
`CompilerCapabilities.from_profile`, which is how section 5.6 got `qblox-default-v1` and
`qdac-default-v1` without either package being mentioned in the call.

`extends` names a parent, and the child accumulates the parent's capabilities and predicates while
overriding its limits and vendor versions. `qprogram-base-v1` ships with the core and carries the 33
block, expression, and sweep tokens, no `op.*` among them, so a platform profile that needs one more
sweep shape declares only the difference. Registration is idempotent for an equal `Profile`, so a
re-executed notebook cell or a reloaded module is not an error.
"""

# %%
FRIDGE_BUS_V1 = qp.Profile(
    name="fridge-bus-v1",
    version=(0, 1, 0),
    extends=None,
    capabilities=frozenset(t for t in CAPABILITY_REGISTRY if t.startswith(("op.", "waveform.", "measure.")))
    | {"vendor.fridge.set_attenuation"},
    limits={"min_wait_duration_ns": 4},
    predicates=(),
    vendor_versions={"fridge": (0, 1, 0)},
)

FRIDGE_PLATFORM_V1 = qp.Profile(
    name="fridge-platform-v1",
    version=(0, 1, 0),
    extends="qprogram-base-v1",  # the core bundle, plus the one sweep shape we registered above
    capabilities=frozenset({"sweep.chevron"}),
    limits={},
    predicates=(),
    vendor_versions={},
)

qp.register_profile(FRIDGE_BUS_V1)
qp.register_profile(FRIDGE_PLATFORM_V1)
qp.register_profile(FRIDGE_BUS_V1)  # idempotent for an equal profile, so a re-run is safe

bus_half = qp.CompilerCapabilities.from_profile("fridge-bus-v1")
platform_half = qp.CompilerCapabilities.from_profile("fridge-platform-v1")

print("qprogram-base-v1   ->", len(qp.CompilerCapabilities.from_profile("qprogram-base-v1").capabilities), "tokens")
print("fridge-platform-v1 ->", len(platform_half.capabilities), "tokens, the parent plus sweep.chevron")
print("fridge-bus-v1      ->", len(bus_half.capabilities), "tokens")

fridge_rack = qp.PlatformCapabilities(
    bus={},
    platform=qp.BusCapabilities(rt=platform_half, host=platform_half),
    default_bus_profile=qp.BusCapabilities(rt=bus_half, host=bus_half),
)
print("\ndiagnostics from the rack we just published:", qp.validate(program, fridge_rack)[0])

# %% [markdown]
r"""
## 6.2 Vendor packages for real

Everything above lived in a notebook cell. A shipped extension is a separate Python package that
depends on `qprogram` and makes the same registration calls at import time. Two of them are
published, each in a repository of its own, and Part 5 already used both. `qprogram-qblox` adds six
operations, four of them sequencer instructions and two host-side parameter writes that a platform
realizes as slow-control settings. `qprogram-qdac` adds four, and is the rack B of Part 5 as a
package rather than as a cell.

A shipped package takes one step a notebook cell cannot. It declares an entry point:

```toml
[project.entry-points."qprogram.vendors"]
qblox = "qprogram_qblox"
```

Now `loads()` can activate the extension on demand. When it reaches a `require qblox 0.1` line for a
vendor that is not registered yet, it looks up that entry-point group, imports the module, and the
registration side effects run.

Which sounds like a small convenience and is the thing that makes an archived file usable. A `.qp`
file from six months ago names the extensions it needs, in its own header, and a fresh interpreter
finds and loads them without the reader knowing what to import. Compare the alternative, where
opening an old file means guessing which packages the author had installed.

Watch the namespace list below cross the load. Nothing in this notebook has imported
`qprogram_qblox`, so `qblox` is absent before the call and present after it. The import happened
because the file asked for it.
"""

# %%
installed = {ep.name: ep.value for ep in entry_points(group="qprogram.vendors")}
print("vendor entry points installed in this environment:", installed or "none")
print("vendor namespaces registered before the load:", sorted(qp.QProgram._vendor_registry))

needs_qblox = '#!QProgram 1.0\n\nrequire qblox 0.1\n\nbody:\n  qblox.acquire "readout" "weights" name="m0"\n'
loaded = qp.loads(needs_qblox)

print("vendor namespaces registered after the load: ", sorted(qp.QProgram._vendor_registry))
print("the operation it rebuilt:", type(loaded.body.elements[0]).__name__,
      "from", version("qprogram-qblox"))

# %% [markdown]
r"""
Two ways for that to fail, and both name the problem rather than dropping an operation on the floor.

A vendor nobody claims has no entry point to find. Version compatibility is checked at major.minor,
where the file's major must equal the installed extension's major and the file's minor must be less
than or equal to the installed minor. Patch is informational, and the writer truncates it. The
asymmetry is deliberate. A file written against an older minor loads under a newer extension,
because a minor bump adds vocabulary rather than removing it, and a file written against a newer one
does not, because the operation it needs may not exist yet.
"""

# %%
print("auto-activation of a vendor nobody claims:", qp.try_activate_vendor("acme_rack"))

for label, text in (
    ("a vendor nobody claims", 'require acme_rack 0.1\n\nbody:\n  wait "drive" 100\n'),
    ("a version this install cannot satisfy", 'require qdac 9.9\n\nbody:\n  wait "drive" 100\n'),
):
    try:
        qp.loads("#!QProgram 1.0\n\n" + text)
    except qp.ParseError as error:
        print(f"\n{label}:")
        print(" ", error)

# %% [markdown]
r"""
### 🧩 Exercise 6.1: a vendor measurement field

A photon-counting readout does not return an IQ point. It returns counts. The measurement field
vocabulary extends through the same registry. Register `measure.fields.counts` and
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

A calibration is not a plot. It is the program that produced the plot, and the numbers that came
out. QProgram writes the program as line-oriented text, so the ordinary tools work on it: `diff`,
code review, `git blame`, and a checker you can run in CI.

Here are two runs of the same Rabi experiment, a Monday and a Friday. Somebody changed three things,
and the diff names all three in the language of the experiment rather than in sequencer opcodes.
Read the output and you can reconstruct the week: the amplitude sweep now stops at 0.8 instead of
1.0, so the pi pulse came in lower than expected and the top of the range was wasted. The readout
frequency moved by 400 kHz, so the resonator drifted or somebody re-ran the punchout. And the shot
count doubled, so the contrast was worse than they wanted.

None of that is in a plot, and all of it is in a text file that costs nothing to keep.
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

Break the Friday file the way a hand edit breaks a file. Misspell a bus. The message comes back with
the line number, the path that failed to resolve, and the buses the chip does have, because the
`.qp` file declares its own schema. A checker that knows the layout can tell a typo from a bus that
genuinely does not exist, and the difference matters: one is a five-second fix and the other means
the file was written for a different chip.

The same module has two more modes. `explain` prints the execution plan as a tree straight from a
shell, the fastest way to answer "why is this loop running host-side". `serve` speaks LSP over stdio
and needs the `qprogram[lsp]` extra. The VS Code extension lives in the `qprogram-editors`
repository and is published as `qilimanjaro.qprogram`. It is a thin front-end over that same
`qprogram.lsp` module, deliberately, so an editor squiggle cannot drift from what the parser accepts
at load time. It highlights `.qp`, runs `check` on open, on save, and debounced while you type, and
adds a `qp: Explain execution plan` command.
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

Somebody hand-edited a `.qp` file and broke it in two places. Find and fix both using nothing but
the checker output, then prove the repaired file is the program you started from.

Your job:

1. Take the `cz_chevron` program from 6.1, serialize it, and break it twice, turning `average` into
   `avarage` and `q[0].flux` into `q[0].flx`.
2. Loop. Call `qprogram.lsp.check_text` on the current text, print the first diagnostic with its
   1-based line number, use the reported line to decide which repair applies, and apply it.
3. Stop when the checker returns nothing, then check that the reparsed program's `body` equals the
   original.

The parser stops at the first error, so it takes one round per break plus one more to see a clean
file. That is what the loop is for, and it is also what a CI job looks like from the inside.
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

Six members is a small interface for a large job, and the size is the claim. What a real platform
does between `execute` and the result is deliberately unspecified: lower the AST to its sequencer
language, allocate registers and waveform memory, upload, arm the triggers, start the acquisition,
stream partial results back, and assemble the same xarray shapes. That work is where a vendor's
expertise lives and QProgram has no business specifying it.

What QProgram does specify is the last step, and the reference executor is how. It defines what the
result of a program *means*, in code, so a vendor compiler can be tested by running the same program
both ways and comparing the arrays. Without an oracle, "does this compiler produce the right answer"
has no operational definition. With one, it is a test suite. The reference executor models no timing
and no waveform physics, and that is deliberate. It is the semantics of the language, not a
simulator of your fridge.
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
notebook. Feeding each step into the next is the reason to run a bring-up as one script. Do it by
hand, one notebook cell at a time, and the number in step 5 came from whichever version of step 3
you last happened to run.

Runtime is worth a number, because it explains why anybody automates this. Here the whole thing
takes a few seconds of interpreter time. On hardware, with passive reset, the shot counts and point
counts below come to roughly ten minutes of fridge time, and the day is spent on the scans that fail
and get repeated rather than on the ones in this list. A bring-up that runs unattended and writes
its own files is the difference between measuring one qubit and measuring fifty.

The delays in steps 4 to 6 change the result only because the measurement model reads
`env["delay"]`. The reference executor has no timing model. On hardware the delay is the physics;
here it is an argument.

Three cells, two to run it and one to report. Short because `step` does the repetitive part.
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
Now the report. The calibration table is the deliverable, and putting the measured column next to
the true one is a habit worth keeping even when there is no true column to put there. On hardware
you compare against last week instead, and a number that moved by more than its error bar is either
physics or a bug, and either way you want to know today rather than in the paper.

The fitted pulses go out beside it in a `.wfl` library, so tomorrow's run loads today's numbers from
a file instead of from a literal somebody pasted into a script.
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
  `register_vendor_block`, does the same for a vendor's own control flow. A fifth,
  `register_profile`, publishes the token bundle a rack reaches by name.
- The token is what makes an extension safe. A rack that lacks it refuses the program with a named
  diagnostic and a path, before anything reaches an instrument. A fork would have given you the same
  working program locally and a syntax error everywhere else.
- Entry points make a `.qp` file self-describing. The `require` line names the vendor, and `loads()`
  imports the extension that claims it, so an archived file does not depend on the reader knowing
  what the author had installed.
- The `.qp` file is the artifact you keep. It diffs, it reviews, and `python -m qprogram.lsp check`
  turns it into a CI job.
- The capstone recovered f_r, f01, the pi amplitude, T1, T2\*, the detuning, and T2 from simulated
  data, wrote a file per step, and put the fitted pulses in a `.wfl` library. That directory is a
  calibration another lab could load.

Where to read more. The published documentation at qilimanjaro-tech.github.io/qprogram carries the
normative material in its Reference section, `docs/reference/qp-format.md` covers the text format,
and `src/qprogram/grammar/qp.lark` is the machine-readable grammar.
`docs/developer/vendor-extensions.md` walks a vendor package end to end, and `qprogram-qdac` is the
smallest complete one worth copying, at four operations and one profile.

One idea to carry forward. The program, the plan, and the calibration are all data, and everything
this tutorial did followed from that. A program you can serialize is a program you can diff, review,
check in CI, and hand to a different machine. A plan you can print is a performance question you can
answer before you spend fridge time on it. A calibration in a file is a number with a date on it
rather than a literal somebody remembers typing. None of that is available to a string builder, and
all of it is the reason to write the extra layer.
"""
