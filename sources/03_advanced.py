# %% [markdown]
r"""
# 03 · Advanced

This notebook covers six topics: fragments, conditionals, custom waveforms and sweep sources, vendor extensions, platform implementations, and capability validation. Each section defines its own programs and example parameters, so you can run the sections independently after running the two setup cells below.

You will learn how to reuse pulse sequences, branch on measurement outcomes, extend the language, and describe what a platform supports. The final section shows how to inspect execution plans and apply a program transformation.

The examples use plain string bus names until section 3.5 introduces a schema. Simulation uses the reference platform; the vendor extensions demonstrate language and capability support without connecting to instruments.
"""

# %%
# Install missing tutorial dependencies. Check availability without importing vendor
# modules so section 3.4 can demonstrate automatic extension loading.
from importlib.util import find_spec

if (
    find_spec("qprogram") is None
    or find_spec("qprogram_qblox") is None
    or find_spec("qprogram_qdac") is None
):
    import subprocess
    import sys

    subprocess.run(
        [
            sys.executable, "-m", "pip", "install",
            "qprogram[viz]==0.2.0", "qprogram-qblox==0.2.0", "qprogram-qdac==0.2.0",
        ],
        check=True,
    )

from importlib.metadata import version

print("qprogram", version("qprogram"))
print("qprogram-qblox", version("qprogram-qblox"))
print("qprogram-qdac", version("qprogram-qdac"))

# %%
import sys
import warnings
from dataclasses import replace

import matplotlib.pyplot as plt
import numpy as np
import qprogram as qp
import xarray as xr
from qprogram import MeasurementField
from qprogram.buses import BusSchema
from qprogram.plotting import Quantity, Style
from qprogram.waveforms import IQDrag, IQPair, Square

# %% [markdown]
r"""
## 3.1 Fragments

A `Fragment` is a named, parameterised sequence that you can reuse across programs. Define the sequence once, then add calls to it with `qprogram.call`.

Use `@qp.fragment` to create a fragment from a Python function. Its first argument receives the fragment being built. The remaining arguments become fragment parameters in declaration order. The decorator accepts positional parameters without defaults; default values, `*args`, and keyword-only arguments are rejected when the fragment is defined.
"""

# %%
@qp.fragment
def x_pulse(f, drive, amp):
    """Add a drive pulse to the fragment received as `f`."""
    f.play(drive, IQDrag(amplitude=amp, duration=40, sigma=10, beta=0.1))


qprogram = qp.QProgram(label="one_call")
qprogram.call(x_pulse, "q0/drive", 0.5)  # Pass both parameters positionally.
qprogram.call(x_pulse, "q0/drive", amp=0.5 / 2)  # Pass the amplitude by keyword.

print(qp.dumps(qprogram))

# %% [markdown]
r"""
The `.qp` output contains a separate `fragment` definition and one statement for each call. This preserves the relationship between the reusable sequence and the programs that use it.

Fragment parameters can represent numbers, buses, or waveforms. Their values are supplied at each call. Inside the definition, arithmetic such as `2 * amp` creates an expression using the parameter. Arithmetic on ordinary Python values is evaluated before the call: in the second example above, `0.5 / 2` becomes `0.25`.

The next two cells demonstrate function signatures that the decorator does not support.
"""

# %%
# Fragment parameters cannot have defaults.
try:
    @qp.fragment
    def with_default(f, drive, amp=0.5):
        pass
except qp.ValidationError as exc:
    print(exc)

# %%
# The decorator needs a fixed parameter list, so *args is not supported.
try:
    @qp.fragment
    def with_star_args(f, *args):
        pass
except qp.ValidationError as exc:
    print(exc)

# %% [markdown]
r"""
### Definition time and execution time

The decorator executes the Python function once to build the fragment. Calling the fragment later adds a call node; it does not run that Python function again.

Ordinary Python loops inside the function therefore determine the recorded structure at definition time. Below, `N_PULSES` sets the number of wait-and-play pairs recorded in `pulse_train`. The `spacing` parameter supplies the wait duration separately for each call.
"""

# %%
N_PULSES = 3  # Number of wait-and-play pairs recorded when the fragment is defined.


@qp.fragment
def pulse_train(f, drive, spacing):
    """Wait for `spacing` nanoseconds before each pulse in the train."""
    for _ in range(N_PULSES):
        f.wait(drive, spacing)
        f.play(drive, "pi")


qprogram = qp.QProgram(label="two_calls")
qprogram.call(pulse_train, "q0/drive", 100)
qprogram.call(pulse_train, "q0/drive", 200)

# The fragment definition contains three wait/play pairs; the body contains two calls.
print(qp.dumps(qprogram))

# %% [markdown]
# %% [markdown]
r"""
### Expanding fragment calls

`expand()` returns a new program in which each fragment call becomes a block containing the fragment's operations, with the supplied arguments substituted for its parameters.

The two calls below produce two sets of three wait-and-play pairs: the first uses a spacing of 100 ns, and the second uses 200 ns.

Validation and execution expand fragment calls automatically. You can expand them explicitly to inspect the resulting operations.
"""

# %%
print(qp.dumps(qprogram.expand()))

# %% [markdown]
r"""
### Binding waveforms

`with_waveforms` does not resolve aliases inside fragment calls. Expand the program first, then bind the aliases with `qprogram.expand().with_waveforms(library)`.

The library below defines the waveforms used by these examples. `PULSE_NS` is the duration of the `"pi"` waveform in nanoseconds. The measurement model later uses the same constant to calculate the total sequence duration.
"""

# %%
PULSE_NS = 40  # ns; pulse duration used by both the waveform and the decay model.
READOUT_NS = 2000  # ns; shared duration for the probe waveform and its integration weights.

library = {
    "pi": IQDrag(amplitude=0.5, duration=PULSE_NS, sigma=10, beta=0.1),
    "probe": IQPair(
        I=Square(amplitude=1.0, duration=READOUT_NS),
        Q=Square(amplitude=0.0, duration=READOUT_NS),
    ),
    "weights": IQPair(
        I=Square(amplitude=1.0, duration=READOUT_NS),
        Q=Square(amplitude=1.0, duration=READOUT_NS),
    ),
}

# Binding does not reach the "pi" alias inside the fragment definition.
print(qp.dumps(qprogram.with_waveforms(library)))

# %%
# Expand the calls first, then bind the waveforms in the resulting blocks.
qprogram = qprogram.expand()
qprogram = qprogram.with_waveforms(library)
print(qp.dumps(qprogram))  # Each play now contains an IQDrag waveform.

# %% [markdown]
r"""
### Defining fragments with the builder interface

You can also create a `Fragment` directly and add operations to it, using the same methods as a `QProgram`. Declare its parameters with `parameter()` before using them in operations.

This example defines the same `pulse_train` as the decorated function above. The Python loop records `N_PULSES` wait-and-play pairs when the fragment is built. Each call then supplies its own drive bus and spacing.
"""

# %%
pulse_train_builder = qp.Fragment("pulse_train")
drive = pulse_train_builder.parameter("drive")
spacing = pulse_train_builder.parameter("spacing")

# Record the operations directly on the fragment.
for _ in range(N_PULSES):
    pulse_train_builder.wait(drive, spacing)
    pulse_train_builder.play(drive, "pi")

# Call it in the same way as a fragment defined with the decorator.
qprogram = qp.QProgram(label="two_calls")
qprogram.call(pulse_train_builder, "q0/drive", 100)
qprogram.call(pulse_train_builder, "q0/drive", 200)

print(qp.dumps(qprogram))

# %% [markdown]
r"""
### Using a fragment in an experiment

The next program sweeps the wait duration in `pulse_train` and measures after each call. The measurement is declared directly in the calling program, so its handle is available for retrieving results.

The mock model returns a population that decays exponentially with the sequence duration. Each of the `N_PULSES` repetitions contains a wait and a pulse, giving a total duration of `N_PULSES * (spacing + PULSE_NS)` nanoseconds.

`T_DECAY`, defined beside the model, is the assumed decay time in nanoseconds. Its value of 12,000 ns controls how quickly the synthetic population decreases; the model calculates this response directly from the swept spacing.
"""

# %%
T_DECAY = 12_000.0  # ns; decay time assumed by the mock measurement model.


def decay(bus, env):
    """Return an exponential population decay based on the pulse-train duration."""
    total_ns = N_PULSES * (env["spacing"] + PULSE_NS)
    return 0.5 * np.exp(-total_ns / T_DECAY)


qprogram = qp.QProgram(label="pulse_train_scan")
spacing = qprogram.variable("spacing", label="Pulse spacing", units="ns")

with qprogram.average(shots=400):
    with qprogram.sweep(spacing, qp.Linspace(50, 2000, 21)):
        qprogram.call(pulse_train, "q0/drive", spacing)
        m_train = qprogram.measure("q0/readout", "probe", "weights", fields=(MeasurementField.STATE,))

qprogram = qprogram.expand()
qprogram = qprogram.with_waveforms(library)
result = qp.simulate(qprogram, model=qp.MockMeasurementModel(p_excited=decay, seed=3))

result.plot(
    m_train,
    field=MeasurementField.STATE,
    value=Quantity("Excited-state population"),
    style=Style(markers=True),
    title="Pulse-train spacing sweep",
)
plt.show()

# %% [markdown]
r"""
## 3.2 Conditionals

Conditionals choose which operations to execute based on a measurement taken earlier in the same run. Use `qprogram.if_(condition)`, `qprogram.elif_(condition)`, and `qprogram.else_()` as context managers to build a `Conditional` node.

The condition reads a classified measurement state, so the measurement must request `MeasurementField.STATE`. A handle's `state` proxy supports symbolic comparisons such as `handle.state == 1`. You can also write `qp.eq(handle.state, 1)`.

The example below plays a corrective pulse for state 1 and waits for state 0. `PI_NS` specifies the assumed corrective-pulse duration, so the wait represents the same duration in the other branch. The `else_` branch is included to demonstrate the complete syntax.
"""

# %%
PI_NS = 40  # ns; assumed corrective-pulse duration used for the alternative wait.

qprogram = qp.QProgram(label="one_chain")
m_chain = qprogram.measure("q0/readout", "probe", "weights", fields=(MeasurementField.STATE,))

with qprogram.if_(m_chain.state == 1):
    qprogram.play("q0/drive", "pi")
with qprogram.elif_(m_chain.state == 0):
    qprogram.wait("q0/drive", PI_NS)
with qprogram.else_():
    qprogram.sync()

print(qp.dumps(qprogram))

# %% [markdown]
r"""
### Supported conditions

A condition must be a single equality or inequality comparison between a classified state and an integer, or between two classified states. Combined logical conditions, ordinary variables, floating-point values, and ordered comparisons are not supported yet. Each example below shows one unsupported condition.
"""

# %%
qprogram = qp.QProgram(label="refusals")
m_scratch = qprogram.measure("q0/readout", "probe", "weights", fields=(MeasurementField.STATE,))
counter = qprogram.variable("counter")

# A conditional accepts one state comparison, not a combination of comparisons.
try:
    qprogram.if_((m_scratch.state == 1) & (m_scratch.state == 0))
except (qp.ValidationError, TypeError) as exc:
    print(exc)

# %%
# Ordinary variables cannot be used as the source of a conditional state comparison.
try:
    qprogram.if_(qp.eq(counter, 1))
except (qp.ValidationError, TypeError) as exc:
    print(exc)

# %%
# Compare the state with an integer, such as 1, rather than a float.
try:
    qprogram.if_(m_scratch.state == 1.0)
except (qp.ValidationError, TypeError) as exc:
    print(exc)

# %%
# Ordered comparisons such as < are not supported for classified states.
try:
    qprogram.if_(m_scratch.state < 1)
except (qp.ValidationError, TypeError) as exc:
    print(exc)

# %% [markdown]
r"""
Branches must be adjacent at the same nesting level. An `else_` must immediately follow an `if_` or `elif_`; placing another operation between them breaks the chain.

Other checks require the complete program. Referencing a measurement that did not request a state produces a `missing-classification` diagnostic. Referencing a measurement that is absent from the program produces `unknown-measurement`. `qp.validate` returns these diagnostics, while execution reports the errors as exceptions. Section 3.6 explains how to inspect diagnostics and execution plans.
"""

# %%
qprogram = qp.QProgram(label="no_classification")
m_iq = qprogram.measure("q0/readout", "probe", "weights")  # The default fields include I/Q, but not the classified state.
with qprogram.if_(m_iq.state == 1):
    qprogram.play("q0/drive", "pi")

diagnostics, plan = qp.validate(qprogram, qp.reference_capabilities())
for diagnostic in diagnostics:
    print(diagnostic)  # Explains that the measurement did not request a classified state.

# %% [markdown]
r"""
### Results from conditional branches

A conditional does not add a result dimension. Measurements inside its branches retain the dimensions of their enclosing sweeps. Result positions where a branch was not executed contain `NaN`.

In the example below, the first measurement deterministically selects one branch for each sweep point. The two branch results therefore have complementary missing values, and `combine_first` combines them into one array.

This combination is appropriate for the deterministic example. If averaging includes shots that take different branches at the same point, both arrays may contain values there. `combine_first` selects the first available value; it does not calculate a combined average.
"""

# %%
qprogram = qp.QProgram(label="two_arms")
level = qprogram.variable("level", label="Herald level", units="DAC units")

with qprogram.sweep(level, qp.Linspace(0.0, 1.0, 4)):
    herald = qprogram.measure("q0/readout", "probe", "weights", name="herald", fields=(MeasurementField.STATE,))
    with qprogram.if_(herald.state == 1):
        m_up = qprogram.measure("q0/readout", "probe", "weights", name="up", fields=(MeasurementField.STATE,))
    with qprogram.else_():
        m_down = qprogram.measure(
            "q0/readout", "probe", "weights", name="down", fields=(MeasurementField.STATE,)
        )

# The model reports state 1 for level >= 0.5, selecting each branch at two points.
heralded = qp.MockMeasurementModel(p_excited=lambda bus, env: float(env["level"] >= 0.5))
arms = qp.simulate(qprogram, model=heralded)

up_arm = arms.get(m_up, field=MeasurementField.STATE)
down_arm = arms.get(m_down, field=MeasurementField.STATE)

print("level:", up_arm.coords["level"].values)
print("if branch:", up_arm.values)  # NaN where the if branch was skipped.
print("else branch:", down_arm.values)  # NaN where the else branch was skipped.

combined = up_arm.combine_first(down_arm)  # Fill the missing values from the other branch.
print("combined:", combined.values)
print("dims:", combined.dims)  # The conditional adds no extra dimension.

# %% [markdown]
r"""
## 3.3 Custom waveforms

To define a waveform, subclass `qp.waveforms.Waveform` and implement two methods:

- `envelope(resolution=1)` returns the samples at the requested spacing in nanoseconds.
- `get_duration()` returns the waveform duration in nanoseconds.

The base class provides analysis and plotting methods, notebook display, structural equality, and concatenation with `+`.

The `HalfSine` example samples a positive half-period of a sine wave. Its sample grid includes the starting zero but excludes the final endpoint.
"""

# %%
class HalfSine(qp.waveforms.Waveform):
    """Sample a positive sine half-period, excluding the final endpoint."""

    def __init__(self, amplitude: float, duration: int) -> None:
        self.amplitude = amplitude
        self.duration = duration

    def envelope(self, resolution: int = 1) -> np.ndarray:
        sample_count = self.duration // resolution
        phase = np.linspace(0.0, np.pi, sample_count, endpoint=False)
        return self.amplitude * np.sin(phase)

    def get_duration(self) -> int:
        return self.duration


shape = HalfSine(amplitude=0.42, duration=40)

print("duration:", shape.get_duration(), "ns")
print("samples:", shape.envelope())
print("area:", shape.area())
print("peak:", shape.peak_amplitude())
print("structurally equal:", shape == HalfSine(amplitude=0.42, duration=40))

shape.plot()
plt.show()

# %%
# This implementation only handles numbers; it does not evaluate expressions.
qprogram = qp.QProgram(label="unbound")
amp = qprogram.variable("amp")
try:
    HalfSine(amplitude=amp, duration=40).envelope()
except TypeError as exc:
    print("expression handling error:", exc)

# %% [markdown]
r"""
### Supporting variables and expressions

To accept a swept parameter, a waveform must handle a `qp.Expression` as well as a numeric value. Update the type annotations to describe both forms, then evaluate expressions when their values are needed. Changing the annotation alone does not change the calculation.

The implementation below checks each parameter with `isinstance(..., qp.Expression)` and evaluates expressions with `evaluate_or_raise()`. An unassigned variable then produces `qp.UnassignedVariableError`.

Both `envelope()` and `get_duration()` resolve the parameters they use. Duration must be available independently because other waveform objects may request it without first generating the samples.
"""

# %%
class HalfSine(qp.waveforms.Waveform):
    """A sine half-period with numeric or symbolic amplitude and duration."""

    def __init__(self, amplitude: float | qp.Expression, duration: int | qp.Expression) -> None:
        self.amplitude = amplitude
        self.duration = duration

    def envelope(self, resolution: int = 1) -> np.ndarray:
        amplitude = self.amplitude
        if isinstance(amplitude, qp.Expression):
            amplitude = amplitude.evaluate_or_raise()

        # get_duration() handles a numeric or symbolic duration.
        sample_count = self.get_duration() // resolution
        phase = np.linspace(0.0, np.pi, sample_count, endpoint=False)
        return amplitude * np.sin(phase)

    def get_duration(self) -> int:
        duration = self.duration
        if isinstance(duration, qp.Expression):
            duration = duration.evaluate_or_raise()
        return int(duration)


qprogram = qp.QProgram(label="unbound")
amp = qprogram.variable("amp")
symbolic_shape = HalfSine(amplitude=amp, duration=40)

# The waveform can handle the expression, but the variable still needs a value.
try:
    symbolic_shape.envelope()
except qp.UnassignedVariableError as exc:
    print(exc)

amp.set_value(0.42)
print(symbolic_shape.envelope())  # Assigning the value makes sampling possible.

# %% [markdown]
r"""
### Registering a waveform

The class can already generate samples and plots. Register it to support `.qp` serialisation and capability validation.

`qp.register_waveform(HalfSine)` registers the constructor name used by `qp.dumps` and `qp.loads`. Public attributes are written to the file and passed back to `__init__` when loading. Their names and values must therefore match the constructor arguments. Keep derived or cached attributes private by prefixing their names with an underscore.

`qp.register_waveform_token(HalfSine, "waveform.half_sine")` adds a specific capability requirement. Without that token, the waveform requests only the general `waveform.single` capability.

The serialisation registry is global and keyed by class name. Redefining the class creates a new Python class object, so registering that name again raises `ValueError`. The guard below catches an existing registration; it does not replace the registered class. Restart the kernel before testing a changed implementation under the same name. Waveform-token registration is idempotent.
"""

# %%
try:
    qp.register_waveform(HalfSine)
except ValueError as exc:
    print("already registered in this kernel:", exc)

qp.register_waveform_token(HalfSine, "waveform.half_sine")

qprogram = qp.QProgram(label="half_sine_scan")
flux_amp = qprogram.variable("flux_amp", label="Flux amplitude", units="DAC units")
with qprogram.sweep(flux_amp, qp.Linspace(0.0, 0.5, 5)):
    qprogram.play("q0/flux", HalfSine(amplitude=flux_amp, duration=40))

text = qp.dumps(qprogram)
print(text)
qprogram = qp.loads(text)
print("serialised text preserved after loading:", qp.dumps(qprogram) == text)

one_play = qp.operations.Play("q0/flux", HalfSine(amplitude=0.42, duration=40))
print("required capabilities:", one_play.required_capabilities())

# %% [markdown]
r"""
### Custom sweep sources

A custom sweep source follows a similar pattern. Subclass `qp.SweepSource`, declare `KIND` and `TOKEN`, and implement `length()` and `values()`. Store constructor parameters as matching public attributes so the source can be serialised.

`KIND="linear"` declares a sequence of the form `start + step * i`. A supporting platform can use that structure to generate values with an incrementing loop. Use `KIND="arbitrary"` when the values are supplied as a table. `TOKEN` identifies the source's capability requirement.

`qp.register_sweep_source` registers both serialisation support and the capability token. The `Chebyshev` source below generates values concentrated near the interval's endpoints, demonstrating a source with nonuniform spacing.
"""

# %%
class Chebyshev(qp.SweepSource):
    """Generate Chebyshev nodes concentrated near the interval endpoints."""

    KIND = "arbitrary"
    TOKEN = "sweep.chebyshev"

    def __init__(self, start: float, stop: float, num: int) -> None:
        self.start = start
        self.stop = stop
        self.num = num

    def length(self) -> int:
        return self.num

    def values(self) -> np.ndarray:
        k = np.arange(self.num)
        angles = np.pi * (2 * k + 1) / (2 * self.num)
        unit = -np.cos(angles)  # Nodes between -1 and 1, ordered from left to right.
        # Scale the normalised nodes into the requested interval.
        return self.start + (unit + 1) / 2 * (self.stop - self.start)


try:
    qp.register_sweep_source(Chebyshev)
except ValueError as exc:
    print("already registered in this kernel:", exc)

nodes = Chebyshev(start=4.80e9, stop=4.90e9, num=7)
print("frequencies in GHz:", nodes.values() / 1e9)
print("required capabilities:", nodes.tokens())
print("under Repeat:", qp.Repeat(nodes, times=2).tokens())  # Includes the custom source's token.

qprogram = qp.QProgram(label="chebyshev_scan")
freq = qprogram.variable("freq", label="Drive frequency", units="Hz")
with qprogram.sweep(freq, nodes):
    qprogram.set_frequency("q0/drive", freq)

print(qp.dumps(qprogram))

# %% [markdown]
r"""
## 3.4 Vendor extensions

A vendor extension adds operations for a particular instrument. It is a separate Python package that depends on `qprogram` and registers its additions when imported.

This tutorial uses `qprogram-qblox`, which describes a Qblox sequencer, and `qprogram-qdac`, which describes a QDevil QDAC channel. These packages provide language extensions without connecting to hardware.

An extension can declare an entry point so QProgram can discover it automatically:

```toml
[project.entry-points."qprogram.vendors"]
qblox = "qprogram_qblox"
```

The entry-point name identifies the vendor namespace, and its value names the module to import. When a `.qp` header requires that vendor, QProgram looks in the `qprogram.vendors` entry-point group and activates the extension.

The next cell loads a program that requires `qblox`. In a fresh kernel, the first check should report that `qprogram_qblox` has not been imported; loading the program imports it. Rerunning the cell reports the module as already imported.
"""

# %%
FROM_A_COLLEAGUE = """#!QProgram 0.2

require qblox 0.2

body:
  qblox.set_markers "q0/drive" "0001"
"""

print("qprogram_qblox imported before the load:", "qprogram_qblox" in sys.modules)
qprogram = qp.loads(FROM_A_COLLEAGUE)
print("qprogram_qblox imported after the load:", "qprogram_qblox" in sys.modules)
print(qp.dumps(qprogram))

# %% [markdown]
r"""
### Namespaces

Each extension registers a namespace on `QProgram` through which you call its operations.
"""

# %%
import qprogram_qblox  # noqa: F401  Register the Qblox namespace.
import qprogram_qdac  # noqa: F401  Register the QDAC namespace.

# The imports make both namespaces available on a regular QProgram.
qprogram = qp.QProgram(label="vendor_operations")
qprogram.qblox.set_markers("q0/drive", "0001")
qprogram.qdac.set_offset("q0/flux", 0.42)
print(qp.dumps(qprogram))

# %% [markdown]
r"""
Call vendor operations through their namespace, such as `qprogram.qdac.set_offset(...)`. The serialised header includes a sorted `require` line for each vendor used by the program. These requirements use major and minor versions; patch versions are omitted.

Mixins provide static typing and editor completion for these namespaces. The namespaces also resolve dynamically without a mixin. The example below combines both mixins in one program class, then adds operations from both extensions.
"""

# %%
from qprogram.waveforms import Ramp
from qprogram_qblox import QbloxMixin
from qprogram_qdac import QdacMixin

class RackProgram(QbloxMixin, QdacMixin, qp.QProgram):
    """Expose typed builder methods from both vendor extensions."""


qprogram = RackProgram(label="bias_then_acquire")
qprogram.qdac.set_offset("q0/flux", 0.42)
qprogram.qdac.play("q0/flux", Ramp(from_amplitude=0.0, to_amplitude=0.3, duration=400), dwell=200)
qprogram.qblox.acquire("q0/readout", "weights")

print(qp.dumps(qprogram))

# %% [markdown]
r"""
A `require` line is validated during loading. The next three cells demonstrate an unavailable vendor, a required version newer than the installed extension, and a version containing a patch component. Each produces a `qp.ParseError` with an explanation.
"""

# %%
# This vendor is not installed or registered.
try:
    qp.loads("""#!QProgram 0.2

require acme_rack 0.1

body:
""")
except qp.ParseError as exc:
    print(exc)

# %%
# The installed QDAC extension is version 0.2, below the required version.
try:
    qp.loads("""#!QProgram 0.2

require qdac 0.9

body:
""")
except qp.ParseError as exc:
    print(exc)

# %%
# A require line accepts major.minor, without a patch version.
try:
    qp.loads("""#!QProgram 0.2

require qdac 0.2.0

body:
""")
except qp.ParseError as exc:
    print(exc)

# %% [markdown]
r"""
When loading an older format version, QProgram applies registered migrations in version order. Migrations transform the text in memory; loading does not modify the source file. Serialising the loaded program writes the current format version.

Use `qp.serialization.known_migrations` to inspect registered migrations. With the versions used in this tutorial, the example below loads its `0.1` header and vendor requirement, then serialises both as `0.2`.
"""

# %%
FROM_LAST_YEAR = """#!QProgram 0.1

require qdac 0.1

body:
  qdac.set_offset "q0/flux" 0.42
"""

print("registered migrations:", qp.serialization.known_migrations("qp"))
qprogram = qp.loads(FROM_LAST_YEAR)
print(qp.dumps(qprogram))  # The format header and vendor requirement now use version 0.2.

# %% [markdown]
r"""
## 3.5 Implementing a platform

A platform implements the interface used to inspect resources, validate programs, and execute them. `qp.PlatformProtocol` requires six members:

| Member | Purpose |
|---|---|
| `get_bus_schema()` | Return the bus schema. |
| `get_buses()` | List the available buses. |
| `get_parameters(bus)` | List configuration parameters for one bus. |
| `get_global_parameters()` | List parameters that are not associated with a bus. |
| `capabilities` | Return the platform's capability descriptor. |
| `execute(qprogram)` | Execute a program and return a `QProgramResult`. |

The base class implements `validate`, `plan`, and `explain` using the capability descriptor. Streaming is optional; the default `stream` implementation raises an error.

An `execute` implementation should validate the program first, raise `qp.UnsupportedOperationError` for error diagnostics, and report warnings without treating them as errors. This is an implementation convention, so the platform must include that logic explicitly.
"""

# %% [markdown]
r"""
### A minimal platform implementation

`BenchtopRack` implements all six required members. This example exposes one flux-tunable qubit and a `dac_range` parameter on its flux bus. It stores the schema, capabilities, and parameter values, and checks diagnostics before running a program.

For this example, execution delegates to `ReferencePlatform`. A hardware platform would instead compile the program, send it to the instruments, run it, and assemble the results. The protocol leaves those steps to the implementation.
"""

# %%
schema = BusSchema.flux_tunable_transmon()
q = schema.q


class BenchtopRack(qp.PlatformProtocol):
    """Demonstrate the platform interface with a configurable capability descriptor."""

    def __init__(self, schema, capabilities, parameters=None):
        self._schema = schema
        self._capabilities = capabilities
        self.parameters = dict(parameters or {})

    def get_bus_schema(self):
        return self._schema

    def get_buses(self):
        q = self._schema.q
        return [q[0].drive, q[0].readout, q[0].flux]

    def get_parameters(self, bus):
        if bus == self._schema.q[0].flux:
            return ["dac_range"]
        return []

    def get_global_parameters(self):
        return ["fridge_temperature"]

    @property
    def capabilities(self):
        return self._capabilities

    def execute(self, qprogram):
        diagnostics = self.validate(qprogram)
        for diagnostic in diagnostics:
            if diagnostic.severity == "error":
                raise qp.UnsupportedOperationError(str(diagnostic))
            if diagnostic.severity == "warning":
                warnings.warn(str(diagnostic), qp.ExecutionWarning, stacklevel=2)
        # Delegate execution to the reference platform for this tutorial.
        platform = qp.ReferencePlatform(self._schema, parameters=self.parameters)
        return platform.execute(qprogram)

# %% [markdown]
r"""
The next program sweeps a flux bias and measures at each point. We describe a platform where flux operations can execute only through the host.

Each bus profile contains an `rt` component for real-time execution and a `host` component for host execution. Setting `rt=None` on the flux profile removes real-time support for that bus. Section 3.6 explains how these components affect the execution plan.

The capability descriptors are immutable, so `dataclasses.replace` creates modified copies. Here, we start from the reference descriptor and change only the flux profile.
"""

# %%
qprogram = qp.QProgram(label="flux_sweep", schema=schema)
bias = qprogram.variable("bias", label="Flux bias", units="V")
bias_source = qp.Linspace(-0.05, 0.15, 41)

with qprogram.average(shots=200):
    with qprogram.sweep(bias, bias_source):
        qprogram.set_offset(q[0].flux, bias)
        qprogram.set_frequency(q[0].drive, 4.85e9)
        qprogram.play(q[0].drive, "pi")
        qprogram.sync([q[0].drive, q[0].readout])
        qprogram.measure(
            q[0].readout, "probe", "weights", name="m0", fields=(MeasurementField.STATE,)
        )

# %%
reference = qp.reference_capabilities()
slow_dac = replace(reference.default_bus_profile, rt=None)  # Support flux operations in the host domain only.
rack_caps = replace(reference, bus={("q", "flux"): slow_dac})

rack = BenchtopRack(schema, rack_caps, parameters={"q0/flux.dac_range": 0.5})

print("buses:", rack.get_buses())
print("parameters on q0/flux:", rack.get_parameters(q[0].flux))
print("global parameters:", rack.get_global_parameters())

# Execution emits a warning because the flux sweep must run through the host.
run = rack.execute(qprogram)

print("result:", run)
population = run.get("m0", field=MeasurementField.STATE)
print("array:", population.dims, population.shape)

# %% [markdown]
r"""
The platform returns a result containing a population array and reports an `ExecutionWarning` about host execution. The warning appears in the notebook output.

The next example removes support for `op.set_offset` from the flux bus entirely. Validation then produces an error, and `execute` rejects the program before execution.
"""

# %%
host_half = reference.default_bus_profile.host
dc_source = replace(
    host_half,
    profile="dc-source-v1",
    capabilities=host_half.capabilities - {"op.set_offset"},
)
fixed_flux = qp.BusCapabilities(rt=None, host=dc_source)
fixed_caps = replace(reference, bus={("q", "flux"): fixed_flux})

unsupported_rack = BenchtopRack(schema, fixed_caps)
try:
    unsupported_rack.execute(qprogram)
except qp.UnsupportedOperationError as exc:
    print(exc)

# %% [markdown]
r"""
### Inherited methods and result construction

`BenchtopRack` inherits `validate`, `plan`, and `explain` from `PlatformProtocol`. The next cell calls the first two without any additional implementation in the subclass.
"""

# %%
diagnostics = rack.validate(qprogram)
for diagnostic in diagnostics:
    print(diagnostic)

plan = rack.plan(qprogram)
print("plan entries:", len(plan))

# %% [markdown]
r"""
A platform can construct results directly by creating a `qp.QProgramResult` and calling `append_measurement(bus=..., name=..., data=...)`. The `data` argument is an `xarray.DataArray` assembled by the platform. Without an explicit `fields` mapping, the array is recorded as the integrated I/Q field returned by default from `result.get`.

The next cell constructs a state result using the same bias coordinates as the program above. Zeros stand in for acquired values so we can focus on the array dimensions, coordinates, and measurement name.

In a hardware platform, this construction belongs in `execute` after acquisition. Each measurement's data and coordinates must match its requested fields and enclosing sweeps.
"""

# %%
# One value per bias point, with the variable identifier naming the dimension.
bias_values = bias_source.values()
data = xr.DataArray(
    np.zeros(len(bias_values)),
    dims=[bias.id],
    coords={bias.id: bias_values},
)

own = qp.QProgramResult()
own.append_measurement(
    bus=q[0].readout,
    name="m0",  # Match the name used by measure() in the program.
    data=data,
    fields={"state": data},  # Store the array as the classified-state output.
)
state = own.get("m0", field=MeasurementField.STATE)

print("result:", own)
print(state)  # Shows the values, dimension, and bias coordinates.

# %% [markdown]
r"""
`qp.ReferencePlatform` exposes four configuration arguments:

- `schema` supplies the schema returned by `get_bus_schema`.
- `model` supplies simulated measurement values. The default mock model reports state 0 for every shot.
- `parameters` initialises a dictionary keyed as `"bus.parameter"`. `get_parameter` reads it and `set_parameter` updates it. Updates persist across executions on the same platform instance.
- `vendor_op_handlers` maps vendor operation classes to callbacks that implement their effects during execution.

`qp.simulate` is a convenience wrapper that creates a reference platform and executes one program. Use a platform instance directly when you want to retain state between executions.
"""

# %%
bench = qp.ReferencePlatform(schema=schema, parameters={"q0/drive.attenuation": 20.0})

qprogram = qp.QProgram(label="parameter_store", schema=schema)
qprogram.set_parameter(q[0].flux, "bias", 0.05)
q0_drive_attenuation = qprogram.get_parameter(q[0].drive, "attenuation")
bench.execute(qprogram)

print("parameter store after execution:", bench.parameters)
print("value read into the variable:", q0_drive_attenuation.id, "=", q0_drive_attenuation.value)

# %% [markdown]
r"""
## 3.6 Capabilities, plans, and transformations

A capability descriptor declares which parts of a program a platform can execute. The validator uses it to report unsupported features and determine the available execution domains.

A capability token is a string identifying a feature, such as `op.set_offset` for a flux offset operation or `waveform.iq` for an IQ waveform. Program nodes report the tokens they require, and capability profiles list the tokens they support.

`qp.PlatformCapabilities` contains three fields:

- `bus` maps an element kind and bus kind to a profile. For example, `("q", "flux")` selects the qubit flux profile.
- `platform` describes support for features that are not tied to a bus, such as blocks and expressions.
- `default_bus_profile` applies when no specific bus entry matches. It also applies to plain string bus names, which do not carry schema metadata for selecting an entry.

The `bus` mapping values, `platform`, and `default_bus_profile` are `qp.BusCapabilities` objects. Each has an `rt` component for real-time execution and a `host` component for execution through the control computer. Either component may be `None`.

Each available component is a `qp.CompilerCapabilities` object containing a profile name, version, capability tokens, limits, predicates, and supported vendor versions.
"""

# %%
schema = BusSchema.flux_tunable_transmon()
q = schema.q
reference = qp.reference_capabilities()

print("bus profiles:", reference.bus)  # Unlisted buses use the default profile.
print("platform profile:", reference.platform.rt.profile)
print("platform version:", reference.platform.rt.version)
print("default bus profile:", reference.default_bus_profile.rt.profile)
print("supported domains:", reference.default_bus_profile.supported_domains())
bus_slot = reference.default_bus_profile
host_only_tokens = bus_slot.host.capabilities - bus_slot.rt.capabilities
print("capabilities available only on the host:", host_only_tokens)

# %% [markdown]
r"""
The reference descriptor supports parameter reads and writes in the host domain. These operations access platform configuration through `get_parameter` and `set_parameter`.

The validator selects profiles from the node's context. Blocks use the platform profile. An operation targeting a bus uses that bus's profile; operations involving several buses must be supported by all relevant profiles. Expression tokens beginning with `expr.` are checked against the platform profile, including when an expression appears in a bus operation.

Use `node.required_capabilities()` to inspect requirements and `CompilerCapabilities.supports(token)` to check whether a profile supplies a capability. The next cells demonstrate both sides of this check.
"""

# %%
qprogram = qp.QProgram(label="flux_sweep", schema=schema)
bias = qprogram.variable("bias", label="Flux bias", units="V")
with qprogram.average(shots=200):
    with qprogram.sweep(bias, qp.Linspace(-0.05, 0.15, 41)):
        qprogram.set_offset(q[0].flux, bias)
        qprogram.set_frequency(q[0].drive, 4.85e9)
        qprogram.play(q[0].drive, "pi")
        qprogram.sync([q[0].drive, q[0].readout])
        qprogram.measure(q[0].readout, "probe", "weights", name="m0", fields=(MeasurementField.STATE,))

for node in qprogram.body.walk():
    if node is not qprogram.body:  # Skip the root block returned by walk().
        print(type(node).__name__, node.required_capabilities())

# %%
flux_slot = reference.for_bus(q[0].flux)

# Check the same operation in each execution domain.
print("set_offset in real time:", flux_slot.rt.supports("op.set_offset"))
print("set_offset on the host:", flux_slot.host.supports("op.set_offset"))
print("set_parameter in real time:", flux_slot.rt.supports("op.set_parameter"))
print("set_parameter on the host:", flux_slot.host.supports("op.set_parameter"))

# %% [markdown]
r"""
### Named capability profiles

The reference descriptor is useful for examples. An extension can publish a named `qp.Profile` to describe its own supported features, and `qp.CompilerCapabilities.from_profile(name)` resolves it.

A profile can use `extends` to inherit another profile. It adds to the parent's capability tokens and predicates while overriding limits with the same keys. `qprogram-base-v1` provides core blocks, expressions, and sweeps without bus operations, so it can serve as a starting point for other profiles.

Registering an equal profile again is allowed. Predicate equality depends on the callable objects, so keep their identities stable when reusing a registration. Defining a new lambda or re-executing a function definition creates a different object.
"""

# %%
qp.register_capability_tokens("vendor.benchtop.dac_ramp")
BENCHTOP_FLUX = qp.Profile(
    name="benchtop-flux-v1",
    version=(1, 0, 0),
    extends="qprogram-base-v1",
    capabilities=frozenset({"op.set_offset", "op.wait", "vendor.benchtop.dac_ramp"}),
    limits={"max_loop_nesting": 2},
)
qp.register_profile(BENCHTOP_FLUX)

merged = qp.CompilerCapabilities.from_profile("benchtop-flux-v1")

print("inherited sweep support:", merged.supports("block.sweep"))
print("added offset support:", merged.supports("op.set_offset"))
print("limits:", merged.limits)

# %% [markdown]
r"""
The vendor extensions from section 3.4 also publish named profiles. The two profiles distinguish different kinds of offset control. `qblox-default-v1` supports the core `op.set_offset` token for offset changes within a sequence. `qdac-default-v1` provides `vendor.qdac.set_offset` for changes dispatched through the host. The separate operation names allow the capability system to distinguish their execution requirements.
"""

# %%
import qprogram_qblox  # noqa: F401  Register the Qblox profile.
import qprogram_qdac  # noqa: F401  Register the QDAC profile.

qblox_half = qp.CompilerCapabilities.from_profile("qblox-default-v1")
qdac_half = qp.CompilerCapabilities.from_profile("qdac-default-v1")

print("Qblox limits:", qblox_half.limits)
print("QDAC limits:", qdac_half.limits)

# These profiles distinguish sequencer offsets from QDAC offsets sent through the host.
print("Qblox supports core set_offset:", qblox_half.supports("op.set_offset"))
print("QDAC supports core set_offset:", qdac_half.supports("op.set_offset"))
print("Qblox supports qdac.set_offset:", qblox_half.supports("vendor.qdac.set_offset"))
print("QDAC supports qdac.set_offset:", qdac_half.supports("vendor.qdac.set_offset"))
print("Qblox supports IQ waveforms:", qblox_half.supports("waveform.iq"))
print("QDAC supports IQ waveforms:", qdac_half.supports("waveform.iq"))

# %% [markdown]
r"""
### Validating a program

`qp.validate(qprogram, capabilities)` returns a pair containing diagnostics and an execution plan. Validation failures are returned as diagnostics rather than raised as execution exceptions. This lets a caller display all findings and decide how to handle them.

The plan maps nodes to their supported execution domains. Each diagnostic includes a severity, code, message, and information about the affected node. Inspect `severity` to distinguish errors from warnings and use `code` for programmatic handling.

For readable output, print a diagnostic directly or select its fields. Printing an entire list can include node representations that are less useful than the formatted messages.
"""

# %%
clean, plan = qp.validate(qprogram, reference)
print("diagnostics:", clean)  # An empty list means no issues were reported.
print("plan entries:", len(plan))

reference_bus = reference.default_bus_profile
slow_dac = replace(reference_bus, rt=None)  # Support flux operations in the host domain only.
rack_caps = replace(reference, bus={("q", "flux"): slow_dac})

diagnostics, host_plan = qp.validate(qprogram, rack_caps)
for diagnostic in diagnostics:
    print(diagnostic)

# %%
host_half = reference_bus.host
dc_source = replace(
    host_half,
    profile="dc-source-v1",
    capabilities=host_half.capabilities - {"op.set_offset"},
)
fixed_flux = qp.BusCapabilities(rt=None, host=dc_source)
fixed_caps = replace(reference, bus={("q", "flux"): fixed_flux})

diagnostics, fixed_plan = qp.validate(qprogram, fixed_caps)
refusal = diagnostics[0]  # Inspect the diagnostic for the unsupported offset operation.
print("severity:", refusal.severity)
print("code:", refusal.code)
print("message:", refusal.message)
print("node type:", type(refusal.node).__name__)
print("path:", refusal.path)
print("formatted path:", qp.format_path(refusal.path))
print("capability:", refusal.capability)
print("domain:    ", refusal.domain)

# %% [markdown]
r"""
A diagnostic's `message` explains the issue, its `code` identifies the type of problem, and its `path` locates the affected node.

Use `qp.format_path` to format a path, `qp.node_path` to find a node's path, and `qp.resolve_path` to look up a node from a path. For a program loaded with `qp.loads`, `qprogram.source_map` connects paths to source lines.

### Explaining an execution plan

`qp.explain` displays the program with its execution domains and diagnostics. Each row shows a node and indicates support in both domains, only `rt`, only `host`, or neither. Diagnostics and transformation hints appear beside the relevant rows.
"""

# %%
print(qp.explain(qprogram, reference))

# %% [markdown]
r"""
For this program, the reference descriptor allows every operation in both domains. The next cell uses the same program with the descriptor whose flux bus supports only host execution, so the plan changes without changing the program.
"""

# %%
print(qp.explain(qprogram, rack_caps))

# %% [markdown]
r"""
`set_offset` uses the flux profile and is restricted to the host domain. That restriction also moves its enclosing sweep and averaging block to the host. The `forced-host` warning identifies the affected block and the operation responsible.

The program is still executable, but the host performs the flux updates during each of the 200 passes over the sweep. The additional hint identifies a possible transformation that can reduce those updates, shown later in this section.

If the flux profile does not support `set_offset` in either domain, the operation has no valid execution domain. The following plan shows this error.
"""

# %%
print(qp.explain(qprogram, fixed_caps))

# %% [markdown]
r"""
The unsupported `set_offset` has an error diagnostic and no execution domain. Its enclosing sweep also has no available domain, so inspect the child operation to find the cause. In this plan, the empty domain set propagates one level; the outer averaging row still shows support in both domains. An outer row's domains alone therefore do not establish that the whole program is valid.

### Limits

Limits constrain numeric properties of a program. The core validator reads four keys:

| Limit | Profile used |
|---|---|
| `max_loop_nesting` | Platform profile. |
| `max_parallel_loops` | Platform profile. |
| `max_measurements` | Platform profile. |
| `min_wait_duration_ns` | Profile of the bus targeted by `wait`. |

Profiles can contain additional limits, but declaring a key does not make the core validator enforce it.

For each profile, these limits are read from the `rt` component when it exists, otherwise from `host`. A limit added only to `host` is therefore not checked when the same profile also has an `rt` component. The following cells demonstrate the limits and this distinction.
"""

# %%
# Change the rt component, then place it in copies of the enclosing descriptors.
limited_rt = replace(reference.platform.rt, limits={"max_loop_nesting": 1})
limited_platform = replace(reference.platform, rt=limited_rt)
limited_caps = replace(reference, platform=limited_platform)

diagnostics, plan = qp.validate(qprogram, limited_caps)
print(diagnostics[0])  # average() plus sweep() requires two nesting levels.

# %%
# This platform permits no measurements, so the readout is rejected.
no_measurements_rt = replace(reference.platform.rt, limits={"max_measurements": 0})
no_measurements_platform = replace(reference.platform, rt=no_measurements_rt)
no_measurements_caps = replace(reference, platform=no_measurements_platform)

diagnostics, plan = qp.validate(qprogram, no_measurements_caps)
print(diagnostics[0])

# %%
# A limit set only on host is not read while an rt component is present.
limited_host = replace(reference.platform.host, limits={"max_loop_nesting": 1})
host_limited_platform = replace(reference.platform, host=limited_host)
on_the_wrong_half = replace(reference, platform=host_limited_platform)

diagnostics, plan = qp.validate(qprogram, on_the_wrong_half)
print("diagnostics:", diagnostics)  # Empty: the validator read the unchanged rt limits.

# %% [markdown]
r"""
### Predicates

Predicates add validation rules beyond capability tokens and numeric limits. Each receives a node and a `qp.ValidationContext`. It yields nothing when the node meets the rule, or yields a diagnostic or domain constraint when action is needed.

The rule below yields an error diagnostic when a flux sweep exceeds the example DAC's supported range. `BIAS_LIMIT`, defined beside the predicate, is the maximum absolute offset in volts. It is set to 0.1 V and is used both in the comparison and in the diagnostic message.

The offset operation contains a variable, so the predicate needs its sweep values. `ctx.binding_loop_of(variable)` finds the loop that assigns the variable, and `loop.source.values()` provides the values to check.

`ctx.sweep_kind_of(variable)` identifies whether the variable has a linear or arbitrary source, or no sweep binding. Other context queries provide loop depth, parallel-loop count, measurement count, requested fields, measurement names, and bus usage.
"""

# %%
BIAS_LIMIT = 0.1  # V; maximum absolute offset supported by the example flux DAC.


def flux_within_range(node, ctx):
    """Reject swept offsets whose magnitude exceeds the example DAC limit."""
    if not isinstance(node, qp.operations.SetOffset):
        return  # This rule only checks offset operations.
    if not isinstance(node.offset_path0, qp.Variable):
        return  # This example checks offsets supplied by a swept variable.

    loop = ctx.binding_loop_of(node.offset_path0)
    if loop is None:
        return

    values = loop.source.values()
    reach = max(abs(values))  # Largest absolute offset in the sweep.
    if reach > BIAS_LIMIT:
        yield qp.Diagnostic(
            severity="error",
            code="benchtop.flux-out-of-range",
            message=f"Flux sweep reaches {reach:.2f} V, exceeding the DAC limit of {BIAS_LIMIT} V.",
            node=node,
        )


# Apply the rule in both domains, preserving any predicates already present.
guarded_rt = replace(reference_bus.rt, predicates=reference_bus.rt.predicates + (flux_within_range,))
guarded_host = replace(reference_bus.host, predicates=reference_bus.host.predicates + (flux_within_range,))
guarded_bus = qp.BusCapabilities(rt=guarded_rt, host=guarded_host)
guarded = replace(reference, bus={("q", "flux"): guarded_bus})

diagnostics, plan = qp.validate(qprogram, guarded)
print(diagnostics[0])  # The sweep reaches 0.15 V, above BIAS_LIMIT.
flux_sweep_text = qp.dumps(qprogram)
flux_sweep_body = qprogram.body

# %%
qprogram = qp.QProgram(label="narrow_scan", schema=schema)
bias = qprogram.variable("bias", label="Flux bias", units="V")
with qprogram.sweep(bias, qp.Linspace(-0.05, 0.05, 11)):
    qprogram.set_offset(q[0].flux, bias)
diagnostics, plan = qp.validate(qprogram, guarded)
print("diagnostics:", diagnostics)  # Empty: all offsets are within the supported range.

# %% [markdown]
r"""
A predicate can yield `qp.DomainConstraint` to restrict a block's execution domains without rejecting the program. The constraint names the block, the domains to exclude, and a reason that can appear in a warning.

The example below restricts the loop that steps a network-controlled DAC to host execution. The constraint must target a block; targeting an operation produces a validation error. `ctx.binding_loop_of` identifies the sweep block to restrict.

This differs from removing real-time support from a bus profile. A domain constraint restricts the loop while leaving the operation's declared capabilities unchanged. Removing the bus's `rt` component also restricts the operation itself. This distinction affects whether the transformation below applies.
"""

# %%
def dac_on_the_network(node, ctx):
    """Restrict the DAC sweep to host execution without rejecting the program."""
    if not isinstance(node, qp.operations.SetOffset):
        return
    if not isinstance(node.offset_path0, qp.Variable):
        return

    loop = ctx.binding_loop_of(node.offset_path0)
    if loop is not None:
        yield qp.DomainConstraint(
            node=loop,  # Restrict the sweep block, not the offset operation.
            exclude=frozenset({"rt"}),
            reason="flux DAC updates require host network communication",
        )


networked_rt = replace(reference_bus.rt, predicates=reference_bus.rt.predicates + (dac_on_the_network,))
networked_host = replace(reference_bus.host, predicates=reference_bus.host.predicates + (dac_on_the_network,))
networked_bus = qp.BusCapabilities(rt=networked_rt, host=networked_host)
networked = replace(reference, bus={("q", "flux"): networked_bus})
qprogram = qp.loads(flux_sweep_text)
print(qp.explain(qprogram, networked))

# %% [markdown]
r"""
### Optimising the loop arrangement

In the platform with a host-only flux bus, the averaging block executes through the host because it contains the flux sweep. `qp.optimize(qprogram, capabilities)` can transform this supported pattern by moving the sweep outside the averaging block and moving the flux update before averaging.

The function returns a new program. Use `qp.explain` on that program to inspect the resulting plan.
"""

# %%
qprogram = qp.optimize(qprogram, rack_caps)
print(qp.explain(qprogram, rack_caps))

# %% [markdown]
r"""
The transformed program sweeps the bias in the outer block, updates the offset once per point, and averages the remaining sequence in real time.

This changes the measurement order. The original program makes 200 passes over the full sweep; the transformed program completes 200 shots at one bias before moving to the next. These arrangements can produce different results when the device drifts over time. Apply the transformation when collecting shots by bias point is appropriate for the experiment.

Moving an operation outside the averaging block also changes how often it executes. This is appropriate for a persistent DC setting, but an operation with other side effects may require a different arrangement. The transformation only moves supported leading host-only operations and does not move them past other operations.

The `reorderable-averaging` hint uses the same applicability check as the transformation. If the hint is absent, this rewrite is not applied.
"""

# %%
# The earlier host-only flux example is rewritten.
print("host-only flux changes the body:", qprogram.body != flux_sweep_body)

# With reference capabilities, no operation needs to move to the host.
qprogram = qp.loads(flux_sweep_text)
qprogram = qp.optimize(qprogram, reference)
print("reference capabilities change the body:", qprogram.body != flux_sweep_body)

# %%
# An additional nested sweep falls outside this transformation's supported pattern.
qprogram = qp.QProgram(label="two_sweeps", schema=schema)
bias = qprogram.variable("bias", label="Flux bias", units="V")
freq = qprogram.variable("freq", label="Drive frequency", units="Hz")
with qprogram.average(shots=200):
    with qprogram.sweep(bias, qp.Linspace(-0.05, 0.15, 11)):
        qprogram.set_offset(q[0].flux, bias)
        with qprogram.sweep(freq, qp.Linspace(4.85e9 - 50e6, 4.85e9 + 50e6, 11)):
            qprogram.set_frequency(q[0].drive, freq)
            qprogram.play(q[0].drive, "pi")
            qprogram.measure(q[0].readout, "probe", "weights", name="m0", fields=(MeasurementField.STATE,))

original_body = qprogram.body
qprogram = qp.optimize(qprogram, rack_caps)
print("additional nested sweep changes the body:", qprogram.body != original_body)

# %%
# A broadcast sync includes the host-only flux bus in the middle of the sequence.
qprogram = qp.QProgram(label="bare_sync", schema=schema)
bias = qprogram.variable("bias", label="Flux bias", units="V")
with qprogram.average(shots=200):
    with qprogram.sweep(bias, qp.Linspace(-0.05, 0.15, 41)):
        qprogram.set_offset(q[0].flux, bias)
        qprogram.play(q[0].drive, "pi")
        qprogram.sync()  # Include every bus, including the host-only flux bus.
        qprogram.measure(q[0].readout, "probe", "weights", name="m0", fields=(MeasurementField.STATE,))

original_body = qprogram.body
qprogram = qp.optimize(qprogram, rack_caps)
print("broadcast sync changes the body:", qprogram.body != original_body)

# %%
# A loop constraint leaves the operations' own real-time support unchanged.
network_optimized_body = qp.optimize(qp.loads(flux_sweep_text), networked).body
print("loop constraint changes the body:", network_optimized_body != flux_sweep_body)

# %% [markdown]
r"""
The examples compare program bodies before and after optimisation. An additional nested sweep is outside the supported pattern. Calling `sync()` without explicit buses includes the host-only flux bus, which restricts the synchronisation in the middle of the sequence and prevents the reordering.

A `DomainConstraint` on the loop also does not produce the hint. In that case, the operations retain real-time support, so there is no leading group of host-only operations to move. Use the execution plan to understand why a particular program is unchanged.
"""

# %%
print(qp.explain(qprogram, rack_caps))

# %% [markdown]
r"""
### Defining a vendor namespace

To add a vendor operation, define an `Operation` subclass for the program node and a `qp.VendorNamespace` subclass for the builder methods.

The operation implements `required_capabilities()`. The base class provides methods for finding variables, buses, and waveforms, along with traversal and structural equality. A namespace method calls `self._append(...)` to add an operation to the program.

The example adds `twpa.set_pump`, an illustrative operation for setting an amplifier's pump frequency. Four registration calls make the namespace, operation syntax, capability token, and vendor version available to QProgram.

`register_vendor_version` is called last because it marks the vendor as active. The `qp.try_activate_vendor` guard then allows the cell to reuse an existing registration. Keeping the class definitions inside the guard avoids creating new class objects while the registry still refers to the earlier definitions.
"""

# %%
# Register once per kernel. Rerunning the cell reuses the existing classes and registrations.
if not qp.try_activate_vendor("twpa"):

    class SetPump(qp.operations.Operation):
        """Represent an amplifier pump-frequency setting associated with a readout bus."""

        def __init__(self, bus: str, frequency: float | qp.Expression) -> None:
            self.bus = bus
            self.frequency = frequency

        def required_capabilities(self) -> set[str]:
            return {"vendor.twpa.set_pump"} | qp.protocol.expression_tokens(self.frequency)

    class TwpaNamespace(qp.VendorNamespace):
        """Provide builder methods in the qprogram.twpa namespace."""

        def set_pump(self, bus: str, frequency: float | qp.Expression) -> None:
            self._append(SetPump(bus=bus, frequency=frequency))

    qp.QProgram.register_vendor("twpa", TwpaNamespace)  # Register the namespace on QProgram itself.
    qp.register_vendor_operation("twpa", "set_pump", SetPump)
    qp.register_capability_tokens("vendor.twpa.set_pump")
    qp.register_vendor_version("twpa", "0.1.0")  # Mark the vendor active after completing registration.

qprogram = qp.QProgram(label="pump_then_read")
qprogram.twpa.set_pump("q0/readout", 7.9e9)
pump_text = qp.dumps(qprogram)

print(pump_text)
qprogram = qp.loads(pump_text)
print("serialised text preserved after loading:", qp.dumps(qprogram) == pump_text)

# %% [markdown]
r"""
### 🧩 Exercise 3.1

Create a program that chooses the amplitude of a custom drive pulse based on a classified readout. Combine a custom waveform, a parameterised fragment, a QDAC operation, and an `if_`/`else_` conditional.

Use a simple waveform called `TwoStepPulse`: its first half has the requested amplitude, and its second half has half that amplitude. This keeps the sample calculation short so you can focus on using the waveform within a program.

1. Define `TwoStepPulse` as a subclass of `qp.waveforms.Waveform`. Its constructor should store `amplitude` and `duration` as public attributes. Accept a number or `qp.Expression` for the amplitude and an integer duration in nanoseconds.
2. Implement `envelope(resolution=1)` and `get_duration()`. In `envelope`, evaluate a symbolic amplitude with `evaluate_or_raise()`. Create `duration // resolution` samples with `np.full`, then halve the samples from the midpoint onwards. `get_duration()` should return the stored duration.
3. Register the class with `qp.register_waveform`. Plot a pulse with amplitude `0.4` and duration `40` ns to check its shape.
4. Define a fragment called `shaped_drive` with parameters `drive` and `amplitude`. Inside it, create a 40 ns `TwoStepPulse` using the amplitude parameter, wrap it in `IQZero`, and play it on the supplied drive bus. Import `IQZero` from `qprogram.waveforms`.
5. Create a new flux-tunable transmon schema, assign `q = schema.q`, and create a program labelled `exercise-3.1`. Import `qprogram_qdac` to register the vendor namespace. Use `qprogram.qdac.set_offset` to set `q[0].flux` to `0.05` V. Set the drive frequency to `4.85e9` Hz and the readout frequency to `7.20e9` Hz.
6. Measure `q[0].readout` using the aliases `"probe"` and `"weights"`, requesting `MeasurementField.STATE`. Store the handle, then synchronise the drive and readout buses.
7. If the measured state is 1, call `shaped_drive` with amplitude `0.4`. Otherwise, call the same fragment with amplitude `0.2`.
8. Print the program's `.qp` text and its expanded form. Find the QDAC offset, the fragment definition, and the two branches. In the expanded form, check that each waveform contains the amplitude supplied by its fragment call.

The QDAC operation sets a static flux bias before the readout, so both branches use the same bias. `IQZero` puts the custom waveform on the drive bus's I path and sets its Q path to zero.

Uncomment the hints below and replace each `...` with the missing code. Some gaps need several operations.
"""

# %% solution
import qprogram_qdac  # Register the QDAC namespace.
from qprogram.waveforms import IQZero


class TwoStepPulse(qp.waveforms.Waveform):
    """Use the requested amplitude for the first half, then half that amplitude."""

    def __init__(self, amplitude: float | qp.Expression, duration: int) -> None:
        self.amplitude = amplitude
        self.duration = duration

    def envelope(self, resolution: int = 1) -> np.ndarray:
        amplitude = self.amplitude
        if isinstance(amplitude, qp.Expression):
            amplitude = amplitude.evaluate_or_raise()

        sample_count = self.duration // resolution
        samples = np.full(sample_count, amplitude, dtype=float)
        samples[sample_count // 2:] *= 0.5  # Lower the second half of the pulse.
        return samples

    def get_duration(self) -> int:
        return self.duration


qp.register_waveform(TwoStepPulse)

TwoStepPulse(amplitude=0.4, duration=40).plot()
plt.show()


@qp.fragment
def shaped_drive(f, drive, amplitude):
    # The fragment parameter becomes the waveform's amplitude.
    pulse = TwoStepPulse(amplitude=amplitude, duration=40)
    f.play(drive, IQZero(pulse))


schema = BusSchema.flux_tunable_transmon()
q = schema.q

qprogram = qp.QProgram(label="exercise-3.1", schema=schema)
qprogram.qdac.set_offset(q[0].flux, 0.05)  # QDAC offsets are expressed in volts.
qprogram.set_frequency(q[0].drive, 4.85e9)
qprogram.set_frequency(q[0].readout, 7.20e9)

m_initial = qprogram.measure(
    q[0].readout, "probe", "weights", fields=(MeasurementField.STATE,)
)
qprogram.sync([q[0].drive, q[0].readout])  # The readout finishes before either drive pulse.

with qprogram.if_(m_initial.state == 1):
    qprogram.call(shaped_drive, q[0].drive, amplitude=0.4)
with qprogram.else_():
    qprogram.call(shaped_drive, q[0].drive, amplitude=0.2)

# The fragment is defined once and called with a different amplitude in each branch.
print(qp.dumps(qprogram))

# Expansion substitutes the arguments into each waveform.
qprogram = qprogram.expand()
print(qp.dumps(qprogram))

# %% stub
# import qprogram_qdac
# from qprogram.waveforms import IQZero
#
# class TwoStepPulse(qp.waveforms.Waveform):
#     def __init__(self, amplitude, duration):
#         ...
#
#     def envelope(self, resolution=1):
#         ...
#
#     def get_duration(self):
#         ...
#
# qp.register_waveform(...)
# ...
#
# @qp.fragment
# def shaped_drive(f, drive, amplitude):
#     pulse = TwoStepPulse(amplitude=..., duration=...)
#     f.play(..., IQZero(...))
#
# schema = ...
# q = ...
# qprogram = qp.QProgram(label="exercise-3.1", schema=...)
# qprogram.qdac.set_offset(...)
# ...
# m_initial = qprogram.measure(...)
# qprogram.sync(...)
#
# with qprogram.if_(...):
#     qprogram.call(shaped_drive, ..., amplitude=...)
# with qprogram.else_():
#     ...
#
# print(qp.dumps(...))
# qprogram = ...
# ...

# %% [markdown]
r"""
## Recap

- Define reusable sequences with `@qp.fragment`. The Python function runs at definition time, while fragment calls supply parameter values. Use `expand()` to inspect substituted operations and expand before binding waveform aliases inside fragments.
- Use conditionals to branch on a classified measurement state. Request `MeasurementField.STATE` and use a supported equality or inequality comparison. Skipped measurements contain `NaN`; combine branch arrays only when their missing-value patterns make that appropriate.
- Implement custom waveforms with `envelope()` and `get_duration()`. Resolve symbolic parameters when needed, then register serialisation support and a capability token. Custom sweep sources implement `length()` and `values()` and declare `KIND` and `TOKEN`.
- Package vendor operations with a namespace, operation classes, capability tokens, and a version. A `qprogram.vendors` entry point enables automatic loading from `.qp` requirements.
- Implement the six required platform members. Validate before execution, report diagnostics, and assemble measurements in a `QProgramResult`. The base class provides validation, planning, and explanation methods.
- Describe support through bus and platform profiles with real-time and host components. Use tokens, limits, and predicates to express requirements. Inspect plans with `qp.explain` and review changes in measurement order before applying `qp.optimize`.
"""

# %% [markdown]
r"""
## Where to go next

The [QProgram reference documentation](https://qilimanjaro-tech.github.io/qprogram) covers the API and extension interfaces in more detail. Its developer section is the next place to look when implementing a waveform, source, vendor extension, or platform.

You can also inspect `.qp` files from the command line:

- `python -m qprogram.lsp check file.qp` parses and validates a file, returning JSON.
- `python -m qprogram.lsp explain file.qp` displays its execution plan.
- `python -m qprogram.lsp serve` starts a Language Server Protocol service over standard input and output for editor integration.

The `qprogram-qblox` and `qprogram-qdac` packages provide further examples of vendor namespaces, operations, capability profiles, and predicates.
"""
