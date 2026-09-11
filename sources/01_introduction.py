# %% [markdown]
r"""
# 01 · Introduction

QProgram is a Python library for writing pulse programs. These programs specify the signals, timing, and measurements used to control quantum hardware. This notebook introduces the QProgram syntax: you will create a program, add operations, define buses and waveforms, save and load programs, and run an example on the reference platform.

The tutorial has three notebooks. **Introduction** covers the main language features. **Basics** introduces variables, loops, and measurement results. **Advanced** covers language extensions and platform definitions.

The examples use QProgram's Python reference platform and run locally without connected instruments, hardware drivers, or a cloud account.
"""

# %% [markdown]
r"""
## Before you start

Run the next two cells to set up the notebook. The first installs QProgram if it is missing, which may be necessary in a fresh Google Colab session. The second displays the installed Python and QProgram versions. QProgram requires Python 3.11 or later; versions 3.11 through 3.14 are tested.
"""

# %%
# Install QProgram if it is not already available in this Python environment.
try:
    import qprogram
except ImportError:
    import subprocess
    import sys

    subprocess.run([sys.executable, "-m", "pip", "install", "qprogram[viz]==0.2.0"], check=True)
    import qprogram

# %%
from importlib.metadata import version
from platform import python_version

print("Python:", python_version())
print("QProgram:", version("qprogram"))

# %%
from pathlib import Path

import matplotlib.pyplot as plt
import qprogram as qp
from qprogram import MeasurementField
from qprogram.buses import BusNaming, BusSchema
from qprogram.waveforms import (
    Arbitrary,
    FlatTop,
    Gaussian,
    IQDrag,
    IQPair,
    IQZero,
    Ramp,
    Square,
    SuddenNetZero,
)

# %% [markdown]
r"""
## 1.1 Creating a program

Create a `qp.QProgram` object, then call its methods to add operations. Each operation is stored as a node in the program's tree structure. Building a program does not execute it, so you can inspect, modify, and save it before running it.

Operations target a bus, which identifies a signal path such as a qubit's drive or readout line. For now, we will identify buses with strings such as `"q0/drive"`. Section 1.3 introduces schemas, which add metadata and validation to bus references.

The optional `label` and `description` arguments provide a name and a description for the program. Both are included when you save it.

The example below sets the drive frequency to 4.85 GHz and adds a 40 ns pulse.
"""

# %%
qprogram = qp.QProgram(label="first_program", description="One drive pulse on qubit 0.")
qprogram.set_frequency("q0/drive", 4.85e9)
qprogram.play("q0/drive", IQDrag(amplitude=0.62, duration=40, sigma=10, beta=0.15))

print(qp.dumps(qprogram))

# %% [markdown]
r"""
`qp.dumps(qprogram)` returns the program as text in the `.qp` format. The header contains its label and description, followed by the operations in the order they were added. Section 1.6 shows how to save this text to a file.

You can also inspect the program directly. `buses` returns the bus names currently used anywhere in the program, and `body.elements` is the list of nodes directly inside its main body.
"""

# %%
print("buses:", qprogram.buses)

# The two calls above added a SetFrequency node and a Play node, in that order.
print(type(qprogram.body.elements[0]))
print(type(qprogram.body.elements[1]))

# %% [markdown]
r"""
## 1.2 Operations

Use the methods below to add operations to the program. Each call adds one node and returns `None`, except for `measure` and `get_parameter`, which return objects used to access their results.

Durations are expressed in nanoseconds, frequencies in hertz, and phases in radians. Gain and offset are dimensionless. Numeric arguments can also use variables and expressions, which are introduced in **Basics**.

| Method | Node added | Purpose |
|---|---|---|
| `play(bus, waveform)` | `Play` | Play a waveform on a bus. |
| `measure(bus, waveform, weights, *, name=None, fields=(MeasurementField.IQ,))` | `Measure` | Play a readout waveform and acquire a measurement. Returns a `MeasurementHandle`. |
| `wait(bus, duration)` | `Wait` | Wait for the specified duration on one bus. |
| `sync(buses=None)` | `Sync` | Align the selected buses at the latest of their current times. |
| `set_frequency(bus, frequency)` | `SetFrequency` | Set the carrier frequency of a bus. |
| `set_phase(bus, phase)`, `reset_phase(bus)` | `SetPhase`, `ResetPhase` | Set the oscillator phase or reset it to zero. |
| `set_gain(bus, gain)` | `SetGain` | Set the gain applied to the bus output. |
| `set_offset(bus, offset_path0, offset_path1=None)` | `SetOffset` | Set a DC offset for one or both signal paths. |
| `set_parameter(bus, parameter, value)` | `SetParameter` | Set a platform configuration parameter. |
| `get_parameter(bus, parameter)` | `GetParameter` | Read a platform configuration parameter. Returns a `Variable` populated during execution. |
| `call(fragment, *args, **kwargs)` | `Call` | Call a reusable program fragment, covered in **Advanced**. |

These operations provide a common interface for functions supported by control instruments. **Advanced** shows how vendor namespaces can expose additional operations.

Use `average(shots)` to repeat operations for averaging and `sweep(variable, source)` to iterate over values. **Basics** covers loops and how to combine them with `|`. Conditional blocks using `if_`, `elif_`, and `else_` are covered in **Advanced**.
"""

# %% [markdown]
r"""
### Building a pulse sequence

The example below plays a drive pulse, waits for 400 ns, and then performs a readout. The readout waveform uses `IQZero`, which places the supplied waveform on the in-phase (I) path and sets the quadrature (Q) path to zero. The `fields` argument selects the measurement outputs to return.

`set_gain` controls the gain applied to the bus output, while a waveform's `amplitude` controls the amplitude of that waveform. `reset_phase` resets the oscillator phase to zero, providing a consistent phase reference.

`play`, `measure`, and `wait` advance the time on their target bus. A platform may require durations to be multiples of a particular interval, such as 4 ns. QProgram preserves the values you provide; the platform determines whether those durations are supported.
"""

# %%
READOUT_NS = 2000  # Use the same duration for the readout pulse and integration weights.

readout_pulse = IQZero(Square(amplitude=0.2, duration=READOUT_NS))  # I envelope with Q set to zero.
weights = IQPair(
    I=Square(amplitude=1.0, duration=READOUT_NS),
    Q=Square(amplitude=1.0, duration=READOUT_NS),
)
pi_pulse = IQDrag(amplitude=0.62, duration=40, sigma=10, beta=0.15)

qprogram = qp.QProgram(label="prepare_and_read", description="A pi pulse on qubit 0, then a readout.")
qprogram.set_frequency("q0/drive", 4.85e9)
qprogram.set_gain("q0/drive", 1.0)
qprogram.reset_phase("q0/drive")
qprogram.play("q0/drive", pi_pulse)
qprogram.wait("q0/drive", 400)  # Wait 400 ns before synchronising with the readout bus.
qprogram.set_frequency("q0/readout", 7.20e9)
qprogram.sync(["q0/drive", "q0/readout"])
m0 = qprogram.measure(
    "q0/readout", readout_pulse, weights, fields=(MeasurementField.IQ, MeasurementField.STATE)
)

print(qp.dumps(qprogram))

# %% [markdown]
r"""
### Synchronising buses

Each bus has its own timeline. A pulse, measurement, or wait advances the time on the bus it targets. Operations on different buses therefore do not automatically run one after another, even if their calls appear on consecutive lines of Python.

Use `sync(buses)` when an operation must wait for work on other buses to finish. It advances each selected bus to the latest current time among them. In `qprogram`, this makes the readout wait until the drive pulse and the 400 ns delay have finished.

Calling `sync()` without an argument synchronises every bus in the program. An empty list, `sync([])`, raises `qp.ValidationError`. Specify the buses explicitly when only those buses need to be synchronised; **Advanced** shows how this choice affects program transformations.
"""

# %%
# The earlier qprogram.sync(["q0/drive", "q0/readout"]) appears in .qp as:
# sync "q0/drive" "q0/readout"

qprogram = qp.QProgram(label="broadcast_sync")
qprogram.sync()  # Synchronise all buses in the program.

# Inspect the sync instruction below: no individual buses are listed.
print(qp.dumps(qprogram))

# %%
# An empty list is invalid; omit the argument to synchronise all buses.
try:
    qprogram.sync([])
except qp.ValidationError as exc:
    print(exc)

# %% [markdown]
r"""
### Selecting measurement outputs

`measure(bus, waveform, weights)` plays the readout waveform and acquires the response. You do not need a separate `play` call for that readout pulse. The `weights` waveform defines the integration weights applied to the acquired signal. These examples use constant weights of 1.0 for both quadratures.

Use `fields` to request one or more outputs:

- `MeasurementField.IQ`: the integrated I and Q values, returned by default.
- `MeasurementField.STATE`: the state classified by the platform as 0 or 1.
- `MeasurementField.RAW`: the raw ADC trace.

An invalid field raises a validation error when you call `measure`.

The call returns a `MeasurementHandle`, which identifies the measurement by name. Keep this handle to retrieve the corresponding data after execution, as shown in section 1.7. You can choose a name with `name=`; otherwise, QProgram generates one. Names must be unique within the program, and handles with the same name compare equal.
"""

# %%
print("measurement name:", m0.name)

# "bogus" is not a supported measurement field.
try:
    qprogram.measure("q0/readout", readout_pulse, weights, fields=("iq", "bogus"))
except qp.ValidationError as exc:
    print(exc)

# %% [markdown]
r"""
### Setting bus properties

Methods such as `set_frequency` and `set_gain` describe settings that a platform can change within a pulse sequence. Use `set_parameter(bus, name, value)` for platform configuration, such as an external attenuator setting or a local oscillator frequency. Changing these settings may require host communication between runs, so sweeping them can involve additional work for each point.

Parameter names are defined by the platform and are not validated by QProgram's core. Use the platform's `get_parameters(bus)` method to find the available parameters.

`get_parameter(bus, name)` adds a read operation and returns a `Variable` that receives the value during execution. In the output below, the `var` declaration belongs to the variable returned by `get_parameter`. Its identifier is derived from the bus and parameter names. **Basics** explains how to work with variables.

`set_offset` sets the DC level of a signal path, while `set_gain` scales the waveforms played on that bus. Neither specifies a duration. Use `play` when you want to add a waveform with a defined duration to the bus timeline.
"""

# %%
qprogram = qp.QProgram(label="settings")
qprogram.set_parameter("q0/drive", "attenuation", 20.0)
q0_drive_attenuation = qprogram.get_parameter("q0/drive", "attenuation")
qprogram.set_offset("q0/flux", 0.05)

# The output includes the variable declaration created by get_parameter.
print(qp.dumps(qprogram))

# %% [markdown]
r"""
## 1.3 Buses and schemas

Plain string bus names do not provide validation. For example, QProgram will accept `"q0/raedout"` while building a program, even if you intended `"q0/readout"`.

A `BusSchema` defines the bus types available for each kind of device element. It provides structured references such as `q[0].drive`, so you can select a bus through attributes. A schema describes element types without specifying how many elements exist, so it accepts any index.

Each reference is a `BusRef`, a subclass of `str` that also carries bus metadata. You can use it wherever a QProgram method accepts a bus name. Two attributes determine the main validation checks:

- `channel` specifies whether the bus accepts an `IQ` waveform or a `single` waveform. In the schema below, drive and readout buses use IQ waveforms, while flux buses use single-channel waveforms.
- `acquires` indicates whether the bus supports acquisition. A `measure` operation requires this capability.

QProgram uses this metadata to validate operations as you add them.
"""

# %%
schema = BusSchema.flux_tunable_transmon()
q = schema.q

# Drive and readout buses accept IQ waveforms; only readout supports acquisition.
print("drive channel:", q[0].drive.channel)
print("drive acquires:", q[0].drive.acquires)
print("readout channel:", q[0].readout.channel)
print("readout acquires:", q[0].readout.acquires)

# The flux bus accepts a single-channel waveform and does not support acquisition.
print("flux channel:", q[0].flux.channel)
print("flux acquires:", q[0].flux.acquires)

print("BusRef is a string:", isinstance(q[0].drive, str))
print(q[7].drive)  # The schema accepts any index; it does not define the device size.

# %% [markdown]
r"""
QProgram includes schemas for transmons, flux-tunable transmons, and fluxonium qubits. Each also has a `_coupled` variant that adds a `c` element for tunable couplers.

`BusSchema.transmon()` provides drive and readout buses. `BusSchema.flux_tunable_transmon()` also provides a flux bus. To define a custom schema, start with `BusSchema()` and register element types with `add_element`.
"""

# %%
# Printing a schema shows its element types and bus definitions.
print(BusSchema.transmon())
print(BusSchema.flux_tunable_transmon())
print(BusSchema.fluxonium())
print(BusSchema.flux_tunable_transmon_coupled())  # Adds the coupler element c.

# %% [markdown]
r"""
### Validating operations with a schema

A schema allows QProgram to check three requirements when you add an operation:

1. The waveform must match the bus channel type. For a measurement, this applies to both the readout waveform and the integration weights.
2. A measurement bus must support acquisition.
3. Every `BusRef` must belong to the program's schema. A reference from a separate schema is rejected even if its bus name and properties match.

Each invalid operation below raises `qp.ValidationError`. Read the messages to see which requirement was violated.
"""

# %%
qprogram = qp.QProgram(label="deliberate_mistakes", schema=schema)

# A drive bus requires an IQ waveform, but Square is single-channel.
try:
    qprogram.play(q[0].drive, Square(amplitude=0.5, duration=40))
except qp.ValidationError as exc:
    print(exc)

# %%
# A flux bus requires a single-channel waveform, but readout_pulse is IQ.
try:
    qprogram.play(q[0].flux, readout_pulse)
except qp.ValidationError as exc:
    print(exc)

# %%
# The waveform types match, but the drive bus does not support acquisition.
try:
    qprogram.measure(q[0].drive, readout_pulse, weights)
except qp.ValidationError as exc:
    print(exc)

# %%
# This bus belongs to a different schema, even though its name is also q0/drive.
separate_schema = BusSchema.transmon()
try:
    qprogram.play(separate_schema.q[0].drive, pi_pulse)
except qp.ValidationError as exc:
    print(exc)

# %% [markdown]
r"""
You can use both `BusRef` objects and plain strings in the same program. Schema validation applies to the `BusRef` objects; a plain string does not provide the metadata needed for these checks.

The choice also affects automatically generated measurement names. With a `BusRef`, names are generated per bus, such as `q0/readout/m0`. With a plain string, names use a program-wide counter, such as `m0` in section 1.2.

`BusNaming` controls how structured references become bus names. Its pattern uses the placeholders `{element}`, `{index}`, and `{kind}`. In the example below, `rebind(schema=...)` returns a program using a different naming pattern. The resolved bus name changes, while the structural reference in the `.qp` body remains `q[0].drive`. The naming pattern is also stored when the program is saved.
"""

# %%
qprogram = qp.QProgram(label="prepare_and_read", schema=schema)
qprogram.set_frequency(q[0].drive, 4.85e9)
qprogram.play(q[0].drive, pi_pulse)
qprogram.sync([q[0].drive, q[0].readout])
m_checked = qprogram.measure(
    q[0].readout, readout_pulse, weights, fields=(MeasurementField.IQ, MeasurementField.STATE)
)
prepare_and_read_text = qp.dumps(qprogram)

print("handle with a BusRef:", m_checked.name)  # Named per bus.
print("handle with a string:", m0.name)  # Named per program.

# %%
other_rack = BusSchema.flux_tunable_transmon(naming=BusNaming("{kind}_{element}{index}"))
original_buses = qprogram.buses
qprogram = qprogram.rebind(schema=other_rack)

print("original bus names:", original_buses)
print("rebound bus names:", qprogram.buses)

# The naming pattern changes, but the body still refers to q[0].drive.
print(qp.dumps(qprogram))

# %% [markdown]
r"""
## 1.4 Waveforms

A waveform describes the envelope of a pulse. Waveform objects are independent of programs and hardware, so you can create, inspect, compare, and plot them on their own.

For a single-channel waveform, `envelope(resolution=1)` returns its samples as a NumPy array, and `get_duration()` returns its duration in nanoseconds. An IQ waveform provides `get_I()` and `get_Q()` to access its two component waveforms, along with `get_duration()`.

The waveform base class provides methods such as `area()`, `peak_amplitude()`, `rms_amplitude()`, `spectrum()`, and `plot()`. These methods are also available to custom waveforms that implement the interface described in **Advanced**.
"""

# %%
drive_envelope = Gaussian(amplitude=0.5, duration=40, sigma=8)

print("duration:", drive_envelope.get_duration(), "ns")
print("samples:", drive_envelope.envelope())  # The default resolution is 1 ns.
print("peak:", drive_envelope.peak_amplitude())
print("area:", drive_envelope.area(), "amplitude × ns")

# %% [markdown]
r"""
QProgram provides twelve single-channel waveform types:

- `Square`, `FlatTop`, and `Tukey` for constant or smoothly varying envelopes.
- `Gaussian`, `Sech`, and `GaussianDragCorrection` for shaped envelopes and a DRAG correction.
- `Sine` and `Cosine` for periodic envelopes.
- `Ramp` and `SuddenNetZero` for shapes commonly used in flux control.
- `Chained` for concatenating waveforms.
- `Arbitrary` for a waveform defined by an array of samples.

The five IQ waveform types combine or transform single-channel waveforms:

- `IQPair` takes separate I and Q waveforms.
- `IQZero` takes an I waveform and sets Q to zero.
- `IQDrag` constructs a drive envelope with a quadrature correction controlled by `beta`.
- `IQRotation` rotates an existing IQ pair in the IQ plane.
- `Modulated` modulates a real envelope onto a carrier.

When choosing parameters, keep the following sampling and duration details in mind:

- `sigma` and `smooth_duration` are widths in nanoseconds, not fractions of the total duration.
- `duration` defines the sampling window. For a centred shape, the samples may not include its exact centre, so the sampled peak can be slightly lower than the requested amplitude.
- `area()` uses trapezoidal integration. At the default resolution, `Square(0.5, 100).area()` returns 49.5.
- `FlatTop` adds its `buffer` outside the specified `duration`, increasing the total waveform duration.

Waveforms compare and hash by their structure and parameter values. Two separately created `Gaussian(0.5, 40, 8)` objects therefore compare equal. You can concatenate compatible shapes with `a + b`, which creates a `Chained` waveform.

A waveform is not tied to a particular bus. For example, you can play a `Square` directly on a flux bus or wrap it in `IQZero` to use it on an IQ bus.
"""

# %%
# Trapezoidal integration gives 49.5 at the default 1 ns resolution.
print(Square(amplitude=0.5, duration=100).area())

# FlatTop adds its buffer outside the specified duration.
padded = FlatTop(amplitude=0.5, duration=200, smooth_duration=20, buffer=10)
print("duration including buffer:", padded.get_duration(), "ns")

# Waveforms with the same type and parameters compare equal.
same_envelope = Gaussian(amplitude=0.5, duration=40, sigma=8)
print(drive_envelope == same_envelope)

# Adding compatible waveforms joins them in time.
joined = Square(amplitude=0.2, duration=10) + Square(amplitude=0.1, duration=10)
print("concatenated duration:", joined.get_duration(), "ns")

# %% [markdown]
r"""
### Using waveform aliases

You can pass a string alias to `play` or `measure` instead of supplying the waveform immediately. This lets you define the sequence first and supply its waveforms later.

Use `with_waveforms` to resolve aliases. It returns a new program and leaves the original unchanged. A dictionary maps each alias to a waveform. `body.waveforms()` returns the program's waveform references. In this example, all references start as string aliases. Aliases without a matching entry remain unresolved, and mapping entries that are not used by the program are ignored.

When a waveform is supplied, QProgram checks that it matches the bus channel type. The last example below deliberately binds a single-channel `Gaussian` to an IQ drive bus to demonstrate this validation.

For more flexible lookup, `qp.WaveformLibrary` can supply different waveforms for the same alias on different buses. It also has a text format for storing waveform definitions separately from the program.
"""

# %%
qprogram = qp.QProgram(label="prepare_and_read", schema=schema)
qprogram.play(q[0].drive, "pi")
qprogram.sync([q[0].drive, q[0].readout])
qprogram.measure(q[0].readout, "readout", "weights", fields=(MeasurementField.IQ, MeasurementField.STATE))

print(qprogram.body.waveforms())  # The three aliases: "pi", "readout", and "weights".
print(qp.dumps(qprogram))  # The play and measure operations refer to those aliases.

# %%
# Supply a waveform for each alias to create a new, resolved program.
print(qp.dumps(qprogram.with_waveforms({
    "pi": pi_pulse,
    "readout": readout_pulse,
    "weights": weights,
})))  # The output now contains the waveform definitions.
print(qprogram.body.waveforms())  # The original program still contains the aliases.

# %%
# "pi" is used on an IQ bus, so a single-channel Gaussian is not a valid replacement.
try:
    qprogram.with_waveforms({"pi": Gaussian(amplitude=0.62, duration=40, sigma=10)})
except qp.ValidationError as exc:
    print(exc)

# %% [markdown]
r"""
## 1.5 Plotting

QProgram provides built-in plotting methods for waveforms. `waveform.plot()` creates a plot and returns the Matplotlib `Axes`, which you can use to add a title, reference lines, or annotations. Measurement results provide a similar plotting interface, shown in section 1.7.

For a quick preview, place a waveform object on the last line of a notebook cell. Its HTML representation displays the envelope automatically and supports both light and dark notebook themes.
"""

# %%
drive_envelope

# %% [markdown]
r"""
Call `plot()` explicitly when you want to customise the figure. Assign the returned axes to a variable, as below. This also prevents the notebook from displaying the axes' text representation, such as `<Axes: ...>`. If you do not need the returned axes, end the call with a semicolon.
"""

# %%
ax = drive_envelope.plot()
ax.set_title("Gaussian envelope", loc="left")
ax.axhline(drive_envelope.peak_amplitude(), color="grey", linestyle=":", linewidth=0.8)
plt.show()

# %% [markdown]
r"""
To arrange several waveform plots in one figure, create the subplots with Matplotlib and pass each axes object through `target=`. The example below displays six waveforms side by side. For `Arbitrary`, supply the sample values directly as a list.
"""

# %%
fig, panels = plt.subplots(1, 6, figsize=(17, 2.4))

# target selects the subplot; plot() adds the waveform's title and axis labels.
Square(amplitude=0.2, duration=2000).plot(target=panels[0])

Gaussian(amplitude=0.5, duration=40, sigma=8).plot(target=panels[1])

FlatTop(amplitude=0.5, duration=200, smooth_duration=20).plot(target=panels[2])

# Explicit sample values define an Arbitrary waveform.
Arbitrary([0.0, 0.1, 0.3, 0.5, 0.3, 0.1, 0.0]).plot(target=panels[3])

Ramp(from_amplitude=0.0, to_amplitude=0.4, duration=200).plot(target=panels[4])

SuddenNetZero(amplitude=0.4, duration=100, b=1.0, t_phi=20).plot(target=panels[5])

fig.tight_layout()
plt.show()

# %% [markdown]
r"""
Plotting an IQ waveform returns two axes, one for I and one for Q. To draw into existing subplots, pass a pair of axes through `target=`.

The two components use separate vertical scales so that a small quadrature component remains visible. For `pi_pulse`, the peak magnitudes are approximately 0.6192 for I and 0.0056 for Q. The Q component is the DRAG correction, whose scale is controlled by `beta`.
"""

# %%
ax_i, ax_q = pi_pulse.plot()
ax_i.set_title("IQDrag: the I component of the pi pulse", loc="left")
ax_q.axhline(0.0, color="grey", linewidth=0.6)
plt.show()

in_phase = pi_pulse.get_I()
quadrature = pi_pulse.get_Q()

print("peak I:", in_phase.peak_amplitude())
print("peak |Q|:", quadrature.peak_amplitude())  # The smaller DRAG correction.
print("readout peak Q:", readout_pulse.get_Q().peak_amplitude())  # IQZero supplies a zero Q component.

# %% [markdown]
r"""
## 1.6 Saving and loading programs

Use `qp.dumps` and `qp.loads` to convert between a program and `.qp` text. Use `qp.save` and `qp.load` to write and read files.

Waveform samples are stored in full. For example, an `Arbitrary` waveform containing 4000 samples stores all 4000 values in the text, without compression or an external array file. If a value or operation cannot be represented, `qp.dumps` raises `qp.SerializationError`.

To check that a program was preserved after saving and loading, compare its body with the original: `loaded_body == qprogram.body`. `QProgram` itself does not define structural equality, so comparing the two program objects directly does not perform this check.

There are two details to consider when saving. A schema loads as a plain `BusSchema` with the same bus definitions, rather than its original typed form. Also, symbolic expressions inside waveform constructors are not supported for a complete save-and-load cycle; resolve them to numeric values before saving.
"""

# %%
out = Path("out")
out.mkdir(exist_ok=True)
path = out / "prepare_and_read.qp"

qprogram = qp.loads(prepare_and_read_text)
qp.save(qprogram, path)
loaded_body = qp.load(path).body

print("saved file:", path)
# Compare the bodies, since QProgram itself does not define structural equality.
print("same body structure:", loaded_body == qprogram.body)

# %% [markdown]
r"""
Saving the `.qp` file alongside your results preserves the program structure and measurement names without requiring the notebook that created it. Because the format is text, you can compare saved programs to identify changes to operations or waveform parameters.
"""

# %% [markdown]
r"""
## 1.7 Running a program

`qp.simulate(qprogram, model=...)` executes a program on QProgram's Python reference platform. The platform interprets the program's structure, including loops and measurements. It does not simulate pulse dynamics or hardware timing, so adding a `wait` does not change the generated measurement values.

A measurement model supplies a sample for each shot. `qp.MockMeasurementModel` provides a configurable model with the following arguments:

- `response`: a function returning the noiseless complex measurement value.
- `noise`: the standard deviation of the Gaussian noise added to each quadrature.
- `raw_samples`: the number of samples in the simulated ADC trace.
- `seed`: a random seed for reproducible results.

The example below contains one measurement without loops or averaging, so it produces one measurement record. `MEAN_IQ` sets the assumed noiseless response to I = 0.62 and Q = 0.18. The response is fixed and does not depend on the pulse sequence. **Basics** shows how the response can depend on a swept variable.

Use `result.get(handle, field=...)` to retrieve an output as an `xarray.DataArray`. This array has named dimensions and coordinates. The integrated result has an `IQ` dimension of length two, with coordinates `"I"` and `"Q"`. Select a quadrature by name with `.sel(IQ="I")` or `.sel(IQ="Q")`.
"""

# %%
qprogram = qp.QProgram(label="one_measurement", schema=schema)
qprogram.set_frequency(q[0].readout, 7.20e9)
m_single = qprogram.measure(
    q[0].readout,
    readout_pulse,
    weights,
    fields=(MeasurementField.IQ, MeasurementField.STATE, MeasurementField.RAW),
)

MEAN_IQ = 0.62 + 0.18j  # Assumed noiseless readout response: I=0.62, Q=0.18.

model = qp.MockMeasurementModel(
    response=lambda bus, env: MEAN_IQ,  # The callback returns the same response for every sample.
    noise=0.02,  # Gaussian noise added to each quadrature.
    raw_samples=64,  # Number of samples in the raw trace.
    seed=4,  # Reproduce the same random noise when the cell is rerun.
)
result = qp.simulate(qprogram, model=model)

# %%
# Inspect the DataArray directly to see its values, dimensions, and coordinates.
point = result.get(m_single, field=MeasurementField.IQ)
print(point)

# Select each quadrature by name. item() extracts its single numeric value.
print("I:", point.sel(IQ="I").item())
print("Q:", point.sel(IQ="Q").item())

state = result.get(m_single, field=MeasurementField.STATE)
print("classified state:", state.item())

trace = result.get(m_single, field=MeasurementField.RAW)
print("raw trace shape:", trace.shape)  # 64 samples, with I and Q for each sample.

# %% [markdown]
r"""
The raw trace contains a sequence of time samples, which can be displayed as a line plot. `result.plot` chooses a plot based on the result's dimensions. **Basics** uses the same method to display results with sweep dimensions, including heatmaps.
"""

# %%
ax_raw = result.plot(
    m_single, field=MeasurementField.RAW, title="Simulated raw readout trace"
)
ax_raw.axhline(0.0, color="grey", linewidth=0.6)
plt.show()

# %% [markdown]
r"""
The integrated result contains just one I/Q point, without a time or sweep dimension for `result.plot` to use. Attempting to plot it with this method raises a validation error, shown below. **Basics** introduces repeated measurements and sweeps, which produce arrays of results.
"""

# %%
try:
    result.plot(m_single, field=MeasurementField.IQ)
except qp.ValidationError as exc:
    print(exc)

# %% [markdown]
r"""
### 🧩 Exercise 1.1

Define a schema for a flux-tunable transmon, then create a program that sets a flux offset, plays a drive pulse, and performs a readout. Save and load the program, then try an invalid operation to see how schema validation works. Reuse `pi_pulse`, `readout_pulse`, and `weights` from the earlier examples.

1. Create a new flux-tunable transmon schema using `BusSchema.flux_tunable_transmon()`. Assign it to `schema` and use `q = schema.q` to access its qubit buses.
2. Create a `QProgram` with the label `exercise-1.1` and your new schema.
3. Set the offset of `q[0].flux` to `0.05`. Set the drive frequency to `4.85e9` Hz and the readout frequency to `7.20e9` Hz.
4. Play `pi_pulse` on `q[0].drive`, then wait for 400 ns on the same bus.
5. Synchronise the drive and readout buses. Measure `q[0].readout` using `readout_pulse` and `weights`, requesting both `MeasurementField.IQ` and `MeasurementField.STATE`. Store the returned handle.
6. Print the `.qp` text, save the program to `out/exercise_1_1.qp`, and load it back. Compare the original and loaded program bodies.
7. Try to measure `q[0].flux`. Catch `qp.ValidationError` with a `try`/`except` block and print the message.

The schema declares that the flux bus does not support acquisition, so QProgram rejects the measurement when you add it.

Uncomment the hints below and replace each `...` with the missing code. Some gaps need several operations.
"""

# %% solution
schema = BusSchema.flux_tunable_transmon()
q = schema.q

qprogram = qp.QProgram(label="exercise-1.1", schema=schema)
qprogram.set_offset(q[0].flux, 0.05)
qprogram.set_frequency(q[0].drive, 4.85e9)
qprogram.set_frequency(q[0].readout, 7.20e9)
qprogram.play(q[0].drive, pi_pulse)
qprogram.wait(q[0].drive, 400)  # Durations are in nanoseconds.
qprogram.sync([q[0].drive, q[0].readout])
m_exercise = qprogram.measure(
    q[0].readout, readout_pulse, weights, fields=(MeasurementField.IQ, MeasurementField.STATE)
)

print(qp.dumps(qprogram))

exercise_path = out / "exercise_1_1.qp"
qp.save(qprogram, exercise_path)
print("handle:", m_exercise.name)
loaded_body = qp.load(exercise_path).body
print("same body after loading:", loaded_body == qprogram.body)

# The flux bus does not support acquisition.
try:
    qprogram.measure(q[0].flux, readout_pulse, weights)
except qp.ValidationError as exc:
    print(exc)

# %% stub
# schema = ...
# q = ...
#
# qprogram = qp.QProgram(label="exercise-1.1", schema=...)
# ...
# qprogram.wait(q[0].drive, 400)
# ...
# m_exercise = qprogram.measure(...)
#
# ...
# exercise_path = out / "exercise_1_1.qp"
# qp.save(qprogram, exercise_path)
# loaded_body = ...
# ...
#
# try:
#     ...
# except qp.ValidationError as exc:
#     print(exc)


# %% [markdown]
r"""
## Recap

- Create a `qp.QProgram` and call its methods to add operations. Inspect the resulting structure with `qp.dumps`, `qprogram.buses`, or `body.elements`.
- Identify buses with strings or use `BusSchema` references to validate waveform compatibility, acquisition support, and schema ownership.
- Use `play`, `measure`, and `wait` to add timed operations. Use `sync` to coordinate the timelines of different buses.
- Create waveforms independently, inspect their properties, and plot them. Use string aliases and `with_waveforms` to supply waveform definitions later.
- Save and load programs in the `.qp` format. Compare their bodies to check structural equality.
- Execute examples with `qp.simulate` and a measurement model. Retrieve requested fields using measurement handles, and plot results that have a time or sweep dimension.
"""

# %% [markdown]
r"""
## Next

In **Basics**, you will use variables to parameterise operations, sweeps to vary their values, and `average(shots)` to repeat measurements. You will then inspect and plot the resulting arrays using their named dimensions and coordinates.
"""
