# %% [markdown]
r"""
# 05 · One program, many machines

The flux sweep from Part 3 works. It found the sweet spot, and the numbers agreed with the device.
Now someone in the lab next door wants to run it on their rack, and their rack is not your rack.

Here is the asymmetry this part is about. A Ramsey experiment is a Ramsey experiment in every lab on
earth. The physics moved between institutions decades ago and moves freely today. You read a paper,
you reproduce the measurement, and nobody has to ship you a machine. The *code* that runs it has
never moved at all. It is written against one vendor's sequencer, in one vendor's dialect, with the
hardware-loop and software-loop split hard-coded on line one, and porting it means rewriting an
experiment that was already correct and then spending a month re-earning the trust you had in it.

Closing that gap needs two things. The program has to stop encoding decisions that belong to the
machine, and the machine has to be able to state what it can do in a form a program can be checked
against. This part is both halves:

- **5.1** What has to be checked before a program reaches an instrument.
- **5.2** Capability tokens, limits, and predicates: how a platform states what it can do.
- **5.3** Build a platform descriptor by hand and validate the flux sweep against it.
- **5.4** `qp.optimize`, and the one broadcast operation that silently blocks the rewrite.
- **5.5** Diagnostics as a contract: a missing operation, a limit, and a data-flow rule.
- **5.6** The same rack again, built from two published vendor profiles instead of by hand.
- **5.7** Porting: `rebind` for bus names, `WaveformLibrary` for the numbers.
"""

# %%
# Run me first. A no-op when qprogram is already installed, an install when it is not
# (a fresh Google Colab runtime, for example).
# Section 5.6 needs the two vendor extension packages as well. Importing either one registers a
# namespace, so probe for the distribution instead and leave the import to the cell that explains it.
from importlib.util import find_spec

if find_spec("qprogram") is None or find_spec("qprogram_qdac") is None:
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

# %% [markdown]
r"""
## 5.1 The same experiment, a different rack

Everything so far ran on `qp.simulate`, which accepts the whole language. A real rack does not.
Take two racks that both call themselves "a transmon control setup":

| | Rack A (yours) | Rack B (next door) |
|---|---|---|
| drive line | fast AWG with a sequencer | fast AWG with a sequencer |
| readout line | same box, shared clock | same box, shared clock |
| flux line | the same AWG, a DC-coupled output | a 20-bit DC source over Ethernet |
| bus names | `q0/drive` | `drive_q0` |
| pulse shapes | your calibration | their calibration |

The flux line is the interesting difference, and it is not a matter of taste. Part 4 established
that $1/f$ flux noise is the main thing dephasing this qubit, and Part 3 established that the
qubit's frequency tracks the flux bias directly. Put those together and a flux line is the one path
into the chip where broadband noise turns straight into decoherence. An AWG output is broadband by
construction; it has to be, or it could not make a 40 ns pulse. A purpose-built DC source has twenty
bits, a quiet reference, and a heavily filtered output, so it is the right instrument for a line
whose job is to hold still.

The consequence is the whole of this part. Those filters have time constants in the milliseconds,
and the instrument reaching them is on Ethernet with no FPGA behind it. A loop that steps that
voltage cannot be a sequencer loop, and it cannot be made into one, because the same filtering that
keeps the line quiet also keeps it slow. It has to be driven from the lab server, one point at a
time, with the fast part of the experiment nested inside it.

Notice what you did *not* write in Part 3. You never said which loop was a hardware loop and which
was a software loop, because that is not a property of your experiment. It is a property of the
rack. So three questions have to be answered before the program reaches an instrument:

1. Does the rack implement every operation, waveform, and sweep shape the program uses?
2. Does the program stay inside the rack's numeric limits?
3. Which loops run inside the sequencer, and which run on the host?

QProgram answers all three from the AST, before anything is uploaded.
"""

# %%
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

import qprogram as qp
from qprogram import MeasurementField as MF
from qprogram.buses import BusNaming, BusSchema
from qprogram.waveforms import IQPair, Square

# The same simulated device as the earlier parts, trimmed to the four numbers this notebook reads.
DEVICE = {
    "q0_f01": 4.85e9,  # Hz, at the flux sweet spot
    "q0_linewidth": 2.0e6,  # Hz, spectroscopy FWHM at low power
    "flux_period": 1.0,  # V
    "flux_offset": 0.05,  # V, where the sweet spot actually sits
}


def f01_of_bias(bias):
    """Qubit frequency against flux bias: the arc every flux-tunable transmon has."""
    phase = np.pi * (bias - DEVICE["flux_offset"]) / DEVICE["flux_period"]
    return DEVICE["q0_f01"] * np.sqrt(np.abs(np.cos(phase)))


DRIVE_FREQ = DEVICE["q0_f01"]  # park the drive tone on the sweet-spot frequency

schema = BusSchema.flux_tunable_transmon()
q = schema.q

print("drive parked at:", DRIVE_FREQ / 1e9, "GHz")
print("f01 at 0 V bias:", round(f01_of_bias(0.0) / 1e9, 4), "GHz")
print("buses on this chip:", [q[0].drive, q[0].readout, q[0].flux])

# %% [markdown]
r"""
### The experiment we are porting

One slice of the Part 3 flux arc, kept in one dimension so the execution plans below stay readable.
Park the drive tone at 4.85 GHz, step the flux bias, and record the excited-state population. The
qubit is only in resonance with the parked tone when the flux puts it at the sweet spot, so the
population peaks there.

Two details in the program matter later:

- `set_offset` is the only operation that touches the flux bus. On rack B it is the only operation
  that cannot run in the sequencer.
- `sync` is written with an explicit target list. Section 5.4 is about what happens when it is not.
"""

# %%
def flux_sweep(sync_targets):
    """Flux spectroscopy at a fixed drive frequency.

    `sync_targets=None` gives a bare `program.sync()`, which broadcasts across every bus in the
    program. Section 5.4 uses that to show what a broadcast costs.
    """
    program = qp.QProgram(label="flux_sweep", schema=schema)
    bias = program.variable("bias", label="Flux bias", units="V")

    with program.average(shots=200):  # 101 points x 200 shots, about 0.2 s in the interpreter
        with program.sweep(bias, qp.Linspace(-0.05, 0.15, 101)):
            program.set_offset(q[0].flux, bias)
            program.set_frequency(q[0].drive, DRIVE_FREQ)
            program.play(q[0].drive, "saturation")
            program.sync(sync_targets)
            handle = program.measure(q[0].readout, "readout", "weights", fields=(MF.STATE,))
    return program, handle


program, m0 = flux_sweep([q[0].drive, q[0].readout])
print(qp.dumps(program))

# %% [markdown]
r"""
### Run it on rack A

The reference platform supports the whole language, so this is the "it works on my rack" baseline.
The measurement model is the qubit-spectroscopy Lorentzian from Part 3 with the peak moved along
the arc, the whole physical content of the experiment. This one uses the natural 2 MHz line rather
than the broadened survey line. The bias steps are 2 mV, and near the sweet spot that puts nine
points across the peak.

The line shape in bias is worth a second, because it is the sweet spot showing up in the data rather
than in an argument. Near the top of the arc the frequency is flat against bias, so the detuning
grows as the *square* of the bias offset instead of linearly, and a Lorentzian in detuning becomes a
quartic in bias:

$$p(V) = \mathrm{floor} + \frac{A}{1 + \left(\frac{V - V_0}{w}\right)^4}$$

A quartic has flatter shoulders and steeper flanks than a Lorentzian, and the flat top is the reason
you park a qubit here. First-order flux noise does nothing at $V_0$. It is also what makes $V_0$
easy to fit, because the steep flanks on either side both constrain the centre.
"""

# %%
def p_flux(bus, env):
    """Excited-state population: the Part 3 spectroscopy peak, moved by the flux bias."""
    hwhm = DEVICE["q0_linewidth"] / 2
    return 0.45 / (1.0 + ((DRIVE_FREQ - f01_of_bias(env["bias"])) / hwhm) ** 2)


def sweet_spot_line(bias, amp, centre, width, floor):
    """Quartic line shape: Lorentzian in detuning, and detuning goes as (bias - centre)^2."""
    return floor + amp / (1.0 + ((bias - centre) / width) ** 4)


def fit_sweet_spot(result, handle):
    """Fit one flux-sweep result and return (bias axis, population, fitted parameters)."""
    pop = result.get(handle, field=MF.STATE)
    bias_v = pop.coords["bias"].values
    guess = [0.45, bias_v[pop.values.argmax()], 0.01, 0.0]
    fit, _ = curve_fit(sweet_spot_line, bias_v, pop.values, p0=guess)
    return bias_v, pop.values, fit


model = qp.MockMeasurementModel(p_excited=p_flux, seed=11)
result = qp.simulate(program, model=model)
bias_v, pop, fit = fit_sweet_spot(result, m0)

print("dims:", result.get(m0, field=MF.STATE).dims)
print(f"sweet spot from the fit: {fit[1] * 1e3:.2f} mV")
print(f"device truth:            {DEVICE['flux_offset'] * 1e3:.2f} mV")
print(f"half width:              {fit[2] * 1e3:.2f} mV")

# %%
plt.plot(bias_v * 1e3, pop, ".", label="measured")
plt.plot(bias_v * 1e3, sweet_spot_line(bias_v, *fit), label="quartic fit")
plt.axvline(DEVICE["flux_offset"] * 1e3, color="grey", linestyle=":", label="true sweet spot")
plt.xlabel("Flux bias (mV)")
plt.ylabel("Excited-state population")
plt.title("Flux spectroscopy with the drive parked at 4.85 GHz")
plt.legend()
plt.show()

# %% [markdown]
r"""
## 5.2 What a platform has to agree to

A platform declares its surface as three separate things. Each axis is the cheapest mechanism that
can express its class of constraint, and collapsing them would cost something real.

| Axis | What it holds | Example |
|---|---|---|
| Capabilities | flat dotted **tokens**, flags | `op.play`, `waveform.iq_drag`, `sweep.linear` |
| Limits | numeric thresholds | `max_loop_nesting: 4`, `min_wait_duration_ns: 8` |
| Predicates | callables that walk the AST | "no arbitrary sweep at `Wait.duration`" |

A **token** is set membership. Checking one is a hash lookup, a set of them serializes into a
profile a vendor can publish and a user can read, and two racks can be compared by subtracting one
set from the other. All of which is worth a great deal, and none of which works for a question whose
answer depends on anything else in the program.

A **limit** is a number, so it needs a comparison rather than a lookup, and it can be tightened for
one device without republishing the profile it came from.

A **predicate** is code, and code is the only thing that can answer a question about how two nodes
interact. Section 5.5 has the canonical example. You could express all three as predicates and the
protocol would still work, and you would have lost the ability to publish a machine-readable
description of a rack, giving up most of the point.

Every node in the tree declares the tokens it needs through `required_capabilities()`. The set is
**instance-aware**: it depends on the node's data, not just its class. A `play` of a `Square` asks
for different tokens than a `play` of an `IQPair`, and a `play` of a string alias asks for almost
nothing, because the alias has not been resolved to a shape yet.

The token prefix says where it is checked. `op.*` and `waveform.*` go to the bus the operation
touches, or to the platform when the operation touches no bus at all. `block.*`, `sweep.*`, and
`expr.*` always go to the platform, even when they show up on an operation that does touch a bus:
the `expr.variable` on the `set_offset` below is a claim about the expression language, not about
the flux line.
"""

# %%
from qprogram.operations import Play  # only to show the tokens; you never build ops by hand

for node in program.body.walk():
    print(f"{type(node).__name__:14s} {sorted(node.required_capabilities())}")

print()
# Same class, same bus, three different demands. The waveform decides two of the three tokens.
pair = IQPair(Square(0.2, 100), Square(0.0, 100))
print("Square:  ", sorted(Play(q[0].drive, Square(0.2, 100)).required_capabilities()))
print("IQPair:  ", sorted(Play(q[0].drive, pair).required_capabilities()))
print("an alias:", sorted(Play(q[0].drive, "saturation").required_capabilities()))

# %% [markdown]
r"""
## 5.3 Describing rack B

A `PlatformCapabilities` has three parts:

- `bus`: a profile per `(element_kind, bus_kind)` slot, so `("q", "flux")` can differ from
  `("q", "drive")`.
- `platform`: the bus-less half. Blocks, sweep shapes, and expression kinds live here.
- `default_bus_profile`: the fallback for a raw-string bus, which carries no schema metadata to
  route on, and for a schema-backed bus whose slot the platform did not list.

Each of those is a `BusCapabilities`, which splits into two halves: `rt` for what the hardware
sequencer can do in real time, and `host` for what the lab server can do one iteration at a time.
Either half may be `None`, and that is how rack B says what it is. The flux slot has **no `rt`
half at all**, and that single missing field carries the entire story from 5.1 about filtered lines
and slow instruments.

Real vendor code builds these from registered profiles (`CompilerCapabilities.from_profile(...)`).
Here we build them by hand from the live token registry, because seeing the set subtraction is the
point.
"""

# %%
from qprogram.protocol import CAPABILITY_REGISTRY

everything = frozenset(CAPABILITY_REGISTRY)  # every token the installed language knows about


def profile(name, tokens, limits=None, predicates=()):
    """One half of one slot: a token set, numeric limits, and predicates."""
    return qp.CompilerCapabilities(
        profile=name, version=(0, 1, 0), capabilities=tokens,
        limits=limits or {}, predicates=predicates, vendor_versions={},
    )


# Instrument settings, not sequencer opcodes. Part 2 wrote one with set_parameter.
param_ops = {"op.set_parameter", "op.get_parameter"}
fast = qp.BusCapabilities(rt=profile("fast-awg", everything - param_ops),
                          host=profile("fast-awg", everything))
slow = qp.BusCapabilities(rt=None, host=profile("slow-dac", everything))  # no sequencer at all
base = qp.BusCapabilities(rt=profile("base", everything), host=profile("base", everything))

caps = qp.PlatformCapabilities(
    bus={("q", "drive"): fast, ("q", "readout"): fast, ("q", "flux"): slow},
    platform=base,
    default_bus_profile=fast,
)

print("tokens in the registry:", len(everything))
print("drive rt, op.play:         ", fast.rt.supports("op.play"))
print("drive rt, op.set_parameter:", fast.rt.supports("op.set_parameter"))
print("flux rt half:              ", slow.rt)

# %% [markdown]
r"""
### Validate

`qp.validate(program, caps)` returns a list of diagnostics and an execution plan. It never raises.
That separation is deliberate. Validation reports, and the caller decides. An editor plugin wants
every diagnostic it can get and no exceptions; a CI job wants a non-zero exit; an interactive
notebook wants to keep going and show you the plan. A platform's `execute()` is the one thing that
turns an error into an exception.

The plan maps each operation and each block to the set of domains it may run in. The root `body` is
not an entry, because there is nowhere else for it to run. Operations come first, then the loops
that contain them. The drive and readout operations can go either way, the `set_offset` on the flux
bus is host-side only, and both loops inherit that from it.
"""

# %%
diagnostics, plan = qp.validate(program, caps)

for diag in diagnostics:
    print(diag)
    print()

for node, domains in plan.items():
    print(f"{type(node).__name__:14s} {'|'.join(sorted(domains))}")

# %% [markdown]
r"""
### The plan, drawn

`qp.explain` renders the same plan as a tree: each node as its `.qp` line, the domain column on the
right (`[rt|host]`, `[rt]`, `[host]`, or `[--]` for a node with no executable domain at all), and the
diagnostics annotated inline (`!!` error, `~` warning, `i` info).

The `forced-host` warning is a *warning*, not an error, and the difference is worth the arithmetic.
The program will run. It will run with the averaging loop on the host, which means 200 network round
trips per bias point rather than 200 sequencer iterations. At a millisecond per round trip that is
20200 milliseconds, so twenty seconds where the sequencer would have taken a fraction of one, and
the whole thing scales with your shot count. On a real rack that is the difference between a coffee
break and a lunch break, and the validator says so out loud rather than letting you find out from
the clock.
"""

# %%
print(qp.explain(program, caps))

# %% [markdown]
r"""
## 5.4 `qp.optimize`: the rewrite the plan is asking for

Look at the info line in the plan. The averaging is host-side only because it *encloses* the flux
sweep, but nothing inside the averaging needs the host. Swap the two loops and the problem goes
away:

```
average 200:                          for bias in Linspace(...):     # host, one DAC write per point
  for bias in Linspace(...):            set_offset q[0].flux bias    # hoisted setup
    set_offset q[0].flux bias    -->    average 200:                 # now real-time
    play q[0].drive ...                   play q[0].drive ...
    measure q[0].readout ...              measure q[0].readout ...
```

The arithmetic changes completely. Before the rewrite, every one of the 20200 executions is a host
round trip. After it, the host does 101 DAC writes and the sequencer does 20200 iterations on its
own. Same experiment, same data, two orders of magnitude in wall clock.

`qp.optimize(program, caps)` applies it. It is opt-in, because the rewrite is not unconditionally
equivalent. It groups all 200 shots of one bias point together instead of interleaving passes over
the sweep, identical for a stationary system and different under drift. If your chip wanders over
ten minutes, the interleaved version spreads that drift evenly across the whole sweep and the
reordered one concentrates it into a slope along the bias axis. Most of the time you want the speed.
Occasionally you want the interleaving, and then you do not call `optimize`.

The hoisted `set_offset` also runs once per bias point instead of once per shot. For a DC bias that
is the whole point, and it would be wrong for an operation with side effects, so the rewrite
only ever hoists a leading run of host-side-only operations and refuses to move one past an
operation it would reorder against.
"""

# %%
optimized = qp.optimize(program, caps)

print(qp.explain(optimized, caps))
print()
print("body[0] before:", type(program.body.elements[0]).__name__)
print("body[0] after: ", type(optimized.body.elements[0]).__name__)

# %% [markdown]
r"""
### The broadcast that blocks the rewrite

`program.sync()` with no arguments means "align every bus in this program". It is a different
operation from `program.sync([q[0].drive, q[0].readout])`, even though both ask for the same token
`op.sync`. A broadcast touches every bus, so the validator intersects the domains of every bus in
the program, and the flux bus has no real-time half. The bare `sync` therefore lands on the host,
in the middle of a run of real-time operations, and the rewrite refuses to hoist across it.

One habit, `sync()` instead of `sync([...])`, costs a factor of a hundred in run time and produces
no error message anywhere. The same thing that made the plan correct made the rewrite impossible.
Naming the two buses you actually want aligned costs you nothing.

Leaving the flux bus out of the `sync` list is not the same as leaving it unaligned. The broadcast
`sync` does not vanish. The plan above puts it on the host, and that placement is exactly why it
blocks the rewrite. What no `sync` can do is hold a bus with no sequencer to a sequencer's clock.
Instruments in that position line up through a hardware trigger line instead. The slow box arms a
chassis trigger output at a chosen point in its own sequence, the fast box waits on that line, and
the alignment happens in copper rather than in the AST. A real slow-DAC extension ships an arm and a
wait on a trigger port alongside its DC write for exactly this reason. The mechanism sits outside
what the language expresses, and it is the reason `sync` can afford to be about sequencer buses
only.

The pattern the rewrite matches is narrow, and it is worth knowing its shape rather than calling
`optimize` hopefully. The averaging block's only child has to be one flat sweep whose body holds no
nested block. Add a second sweep inside the first and the average is still forced host-side, but the
`reorderable-averaging` hint is gone and `optimize` returns the program it was given. The hint and
the rewrite are computed from the same predicate, so they cannot disagree. No hint means no rewrite,
and reading the diagnostics is how you find out that calling `optimize` did nothing.
"""

# %%
from qprogram.operations import Sync

broadcast, _ = flux_sweep(None)  # program.sync(), no targets
b_diagnostics, b_plan = qp.validate(broadcast, caps)


def sync_domain(prog, node_plan):
    """The domain set the plan assigned to this program's one sync operation."""
    node = next(n for n in prog.body.walk() if isinstance(n, Sync))
    return "|".join(sorted(node_plan[node]))


print("sync q[0].drive q[0].readout ->", sync_domain(program, plan))
print("sync (broadcast)             ->", sync_domain(broadcast, b_plan))
print("targeted, diagnostic codes: ", [d.code for d in diagnostics])
print("broadcast, diagnostic codes:", [d.code for d in b_diagnostics])

targeted_top = type(qp.optimize(program, caps).body.elements[0]).__name__
broadcast_top = type(qp.optimize(broadcast, caps).body.elements[0]).__name__
print("targeted,  optimize gives body[0] =", targeted_top)
print("broadcast, optimize gives body[0] =", broadcast_top)

# %% [markdown]
r"""
## 5.5 Diagnostics as a contract

Three racks, three ways to say no. All three come back through the same channel: a list of
`Diagnostic` objects with a `severity`, a machine-readable `code`, a `message`, the offending
`node`, and a structural `path` you can resolve back to a line of `.qp` text.

The machine-readable half matters more than it sounds. A message is for a person reading a terminal.
A `code` is for a script deciding whether this failure is one your CI should fail on, and a `path`
is for an editor putting a squiggle under the right line. Part 6 runs the same diagnostics from a
shell and gets JSON.

First case: the rack does not implement the operation. Rack C has a plain DC source on the flux
line, one that takes a voltage over a serial link and has no offset register at all. Drop
`op.set_offset` from its token set and the program stops being runnable, at one exact node.
"""

# %%
dc_only = qp.BusCapabilities(rt=None, host=profile("dc-source", everything - {"op.set_offset"}))
caps_dc = qp.PlatformCapabilities(
    bus={("q", "drive"): fast, ("q", "readout"): fast, ("q", "flux"): dc_only},
    platform=base,
    default_bus_profile=fast,
)

for diag in qp.validate(program, caps_dc)[0]:
    print(diag)
    print("  severity:  ", diag.severity)
    print("  code:      ", diag.code)
    print("  capability:", diag.capability)
    print("  path:      ", diag.path, "->", qp.format_path(diag.path))

# %%
print(qp.explain(program, caps_dc))

# %% [markdown]
r"""
Read that tree from the leaves up. The `set_offset` row is `[--]`, no executable domain at all, and
it carries the diagnostic that says why. The sweep above it is also `[--]` and carries nothing of its
own, because an operation that can run nowhere empties the loop holding it. Looking on the loop's own
line for a reason will not find one. The `average` at the top still reads `[rt|host]`, and the
difference from 5.3 is instructive. There the sweep was host-side rather than empty, and a host-side
loop does pull its enclosing block host-side, which the `forced-host` warning reported. An empty child
does not propagate that way, so the `average` keeps the domain its own operations allow.

### From a path to a line of the file

The round trip only works when the program came from a file. `program.source_map` on a program you
built in Python is empty, because there is no file for a node to have come from. The parser records
which line produced which node, so the map arrives populated only on a program that came through
`qp.loads`. A program already on disk needs none of this, since loading it fills the map and every
diagnostic reports against a line directly. `expand()` returns a copy with an empty map for the same
reason, because inlining a call produces nodes no line of the file ever held. `qp.resolve_path` and
`qp.node_path` walk between a path and its node in either direction, with no file involved.
"""

# %%
print("built in Python, source_map entries:", len(program.source_map))

text = qp.dumps(program)
reloaded = qp.loads(text)
for diag in qp.validate(program, caps_dc)[0]:
    if diag.path is None:
        continue
    line = reloaded.source_map[diag.path]
    print(f"{qp.format_path(diag.path)} -> line {line}: {text.splitlines()[line - 1].strip()}")

# %% [markdown]
r"""
### A numeric limit

Second case: the program is expressible but too big. A sequencer runs its loops out of a fixed
number of hardware registers, and there is no spilling to memory when you run out, so
`max_loop_nesting` is a hard wall rather than a performance cliff. Below is the Part 3 flux arc on a
smaller grid, three repetition levels deep (average, bias, frequency), against a rack whose
sequencer has two.

The `limit` field carries the pair `(name, observed)`, so a tool can report the number without
parsing the message.

The validator reads four limit keys and passes over every other one. `max_loop_nesting`,
`max_parallel_loops`, and `max_measurements` come off the platform slot, and `min_wait_duration_ns`
off the bus a node routes to. A profile is free to publish a number outside that set, and
`qdac-default-v1` does exactly that with a `min_dwell_ns` waveform floor no core check reads.
Enforcing such a floor is the platform's job, through
`CompilerCapabilities.from_profile(name, extra_predicates=...)`. The same call takes
`limit_overrides=`, which tightens a published limit for one device without republishing the
profile.
"""

# %%
two_loops = profile("shallow", everything, limits={"max_loop_nesting": 2})
caps_shallow = qp.PlatformCapabilities(
    bus={("q", "drive"): fast, ("q", "readout"): fast, ("q", "flux"): slow},
    platform=qp.BusCapabilities(rt=two_loops, host=two_loops),
    default_bus_profile=fast,
)

arc = qp.QProgram(label="flux_arc", schema=schema)
arc_bias = arc.variable("bias", label="Flux bias", units="V")
arc_freq = arc.variable("drive_freq", label="Drive frequency", units="Hz")
with arc.average(shots=50):
    with arc.sweep(arc_bias, qp.Linspace(-0.05, 0.15, 21)):
        arc.set_offset(q[0].flux, arc_bias)
        with arc.sweep(arc_freq, qp.Linspace(4.70e9, 4.90e9, 21)):
            arc.set_frequency(q[0].drive, arc_freq)
            arc.play(q[0].drive, "saturation")
            arc.sync([q[0].drive, q[0].readout])
            arc.measure(q[0].readout, "readout", "weights", fields=(MF.STATE,))

for diag in qp.validate(arc, caps_shallow)[0]:
    print(diag)
    print("  limit:", diag.limit)

# %% [markdown]
r"""
### A rule about how a value is used

Third case: the operation is supported, the limits are fine, and it still cannot run, because of
how two nodes interact. Take `wait(bus, duration)` as the canonical example. It accepts a variable,
but on many backends the wait instruction takes a fixed-step counter. A delay swept by `Range` is a
register increment. The same delay swept by `Values([0, 200, 800, 3200])` is an arbitrary list,
and there is nowhere to put it.

No flat token can express that. `op.wait` is either supported or not, and it is supported in both
cases. The answer depends on the *binding loop*, which is a different node in the tree, several
levels up, and possibly not even written yet when the `wait` was appended. This is what predicates
are for. A predicate is a callable that receives each node and a `ValidationContext` carrying the
cross-node facts, eight queries in all:

| Query | Returns |
|---|---|
| `ctx.sweep_kind_of(var)` | `"linear"`, `"arbitrary"`, or `None` when the variable is not loop-bound |
| `ctx.binding_loop_of(var)` | the block that binds the variable |
| `ctx.max_loop_nesting` | deepest repetition depth in the program |
| `ctx.max_parallel_arity` | widest lockstep composition in the program |
| `ctx.measurement_count` | number of measurement operations |
| `ctx.measurement_fields(name)` | the fields one measurement asked for, or `None` |
| `ctx.known_measurement_names()` | every measurement name in the program |
| `ctx.program_buses` | every bus the program touches |

Yield a `Diagnostic` for a hard no. Yield a `DomainConstraint` instead when the answer is "not in
the sequencer, but the host can do it": the classifier subtracts that domain from the binding loop
and the program still runs. That is the second road to the `forced-host` warning from 5.3, where
the flux slot simply had no real-time half to begin with.
"""

# %%
from qprogram.operations import Wait


def reject_arbitrary_wait(node, ctx):
    """Rack D's wait instruction takes a fixed-step counter, so arbitrary delay lists are out."""
    if not isinstance(node, Wait) or not isinstance(node.duration, qp.Variable):
        return
    if ctx.sweep_kind_of(node.duration) == "arbitrary":
        yield qp.Diagnostic(
            severity="error",
            code="rackd.arbitrary-wait-sweep",
            message=(
                f"Variable {node.duration.id!r} is swept with arbitrary values and used at "
                f"Wait.duration. Use Range or Linspace, or a constant duration."
            ),
            node=node,
        )


checked = qp.BusCapabilities(
    rt=profile("rack-d", everything - param_ops, predicates=(reject_arbitrary_wait,)),
    host=profile("rack-d", everything, predicates=(reject_arbitrary_wait,)),
)
caps_rack_d = qp.PlatformCapabilities(
    bus={("q", "drive"): checked, ("q", "readout"): checked, ("q", "flux"): slow},
    platform=base,
    default_bus_profile=checked,
)

# A predicate belongs to one half of one slot, like a token does.
print("predicates on rack D's drive bus, rt half:",
      [p.__name__ for p in caps_rack_d.for_bus(q[0].drive).rt.predicates])

# %%
def t1_program(source):
    """Inversion recovery, with the delay axis coming from whatever sweep source you pass."""
    prog = qp.QProgram(label="t1", schema=schema)
    delay = prog.variable("delay", label="Delay", units="ns")
    with prog.average(shots=50), prog.sweep(delay, source):
        prog.play(q[0].drive, "pi")
        prog.wait(q[0].drive, delay)
        prog.sync([q[0].drive, q[0].readout])
        prog.measure(q[0].readout, "readout", "weights", fields=(MF.STATE,))
    return prog


for source in (qp.Range(0, 20_000, 500), qp.Values([0, 200, 800, 3200, 12_800])):
    found = qp.validate(t1_program(source), caps_rack_d)[0]
    print(f"{type(source).__name__:9s} {[str(d) for d in found] or 'no diagnostics'}")

# %% [markdown]
r"""
Notice which of those two is the natural thing to write. A $T_1$ scan wants log-spaced delays,
because the interesting part of an exponential is the first time constant and a linear grid spends
most of its points in the tail. Every experimentalist reaches for `Values` or `Logspace` here, and
on rack D every one of them gets an error at build time rather than a mystery at 3 a.m.

### 🧩 Exercise 5.1: your own rule

Rack B's flux line goes through a bias tee that saturates at 0.25 V. A sweep that asks for more
than that will not blow anything up, it will silently clip, and that is worse. You get a flux arc
with a flat section and no warning, and the flat section looks exactly like a sweet spot.

Write a predicate that catches it. Filter for `SetOffset` nodes, find the sweep that binds the
offset value with `ctx.binding_loop_of`, read the sweep's own numbers off `loop.source.values()`,
and yield an error when the largest magnitude exceeds `SAFE_VOLTS`.

This is the shape of most rules a lab actually cares about. Not "does this rack support sweeps" but
"does this particular sweep, on this particular line, stay inside the range where the hardware is
linear". Nothing in the core could know that number. Your rack knows it, and now it can say so.

The two programs below differ only in the range they sweep. The first must pass and the second
must fire.
"""

# %% solution
from qprogram.operations import SetOffset

SAFE_VOLTS = 0.25


def flux_within_range(node, ctx):
    """Reject a flux sweep that leaves the linear range of the bias tee."""
    if not isinstance(node, SetOffset):
        return
    value = node.offset_path0
    if isinstance(value, qp.Variable):
        loop = ctx.binding_loop_of(value)
        reach = max(abs(v) for v in loop.source.values()) if loop is not None else 0.0
    else:
        reach = abs(value)
    if reach > SAFE_VOLTS:
        yield qp.Diagnostic(
            severity="error",
            code="rackb.flux-out-of-range",
            message=f"flux offset reaches {reach:.2f} V, past the {SAFE_VOLTS} V bias-tee limit",
            node=node,
        )


guarded_flux = qp.BusCapabilities(
    rt=None, host=profile("slow-dac", everything, predicates=(flux_within_range,))
)
caps_guarded = qp.PlatformCapabilities(
    bus={("q", "drive"): fast, ("q", "readout"): fast, ("q", "flux"): guarded_flux},
    platform=base,
    default_bus_profile=fast,
)


def bias_scan(low, high):
    """A bare flux scan over one range, for the predicate to judge."""
    prog = qp.QProgram(label="bias_scan", schema=schema)
    bias = prog.variable("bias", units="V")
    with prog.average(shots=10), prog.sweep(bias, qp.Linspace(low, high, 11)):
        prog.set_offset(q[0].flux, bias)
        prog.measure(q[0].readout, "readout", "weights", fields=(MF.STATE,))
    return prog


for low, high in ((-0.05, 0.15), (-0.40, 0.40)):
    found = qp.validate(bias_scan(low, high), caps_guarded)[0]
    errors = [str(d) for d in found if d.severity == "error"]
    print(f"{low:+.2f} V to {high:+.2f} V -> {errors or 'no errors'}")

# %% stub
# TODO: write a predicate that rejects a flux sweep leaving the +/-0.25 V bias-tee range.
# 1) from qprogram.operations import SetOffset, and set SAFE_VOLTS = 0.25.
# 2) def flux_within_range(node, ctx): return early unless isinstance(node, SetOffset).
# 3) The value is node.offset_path0. If it is a Variable, get the binding loop with
#    ctx.binding_loop_of(value) and read loop.source.values(); otherwise use the constant.
# 4) yield qp.Diagnostic(severity="error", code="rackb.flux-out-of-range", message=..., node=node)
#    when max(abs(v)) exceeds SAFE_VOLTS.
# 5) Put it on the flux slot's host half with profile(..., predicates=(flux_within_range,)),
#    build a PlatformCapabilities around it, and validate two scans: -0.05 to 0.15 V (passes)
#    and -0.40 to 0.40 V (fires). Print the diagnostics for both.
# %% [markdown]
r"""
## 5.6 The rack that already exists

Rack B was invented for this notebook. The instrument on its flux line was not. A QDevil QDAC is a
multi-channel DC source with no FPGA on it, and it sits on the flux lines of a great many
dilution-fridge racks. Two published packages describe the two halves of rack B, and both install
from PyPI with no dependency beyond QProgram itself.

`qprogram-qdac` adds a `qdac` vendor namespace and registers `qdac-default-v1`, the bus profile for
one QDAC channel. `qprogram-qblox` does the same for a Qblox cluster, with `qblox-default-v1`
describing one sequencer. Importing either package runs its registration side effects, and after
that `CompilerCapabilities.from_profile` resolves the profile by name. Neither package talks to an
instrument. Both are description and vocabulary, so both run on a laptop next to everything else in
this notebook.
"""

# %%
import qprogram_qblox  # noqa: F401  registers the qblox namespace and qblox-default-v1
import qprogram_qdac  # noqa: F401  registers the qdac namespace and qdac-default-v1

qblox_seq = qp.CompilerCapabilities.from_profile("qblox-default-v1")
qdac_chan = qp.CompilerCapabilities.from_profile("qdac-default-v1")
core = qp.CompilerCapabilities.from_profile("qprogram-base-v1")

print("qblox-default-v1", len(qblox_seq.capabilities), "tokens, limits", qblox_seq.limits)
print("qdac-default-v1 ", len(qdac_chan.capabilities), "tokens, limits", qdac_chan.limits)
print("declared vendor versions:", qblox_seq.vendor_versions, qdac_chan.vendor_versions)
print()
print("op.set_offset on a qblox sequencer:", qblox_seq.supports("op.set_offset"))
print("op.set_offset on a qdac channel:  ", qdac_chan.supports("op.set_offset"))
print("waveform.iq on a qdac channel:    ", qdac_chan.supports("waveform.iq"))

# %% [markdown]
r"""
Two of those answers are worth a second look. `qblox-default-v1` claims `op.set_offset` because a
sequencer output really does have an offset register behind it. `qdac-default-v1` refuses the same
token, and the refusal is deliberate. Setting a QDAC channel is not a sequencer opcode at all, it is
a slow-control write over the chassis link, so the package gives it a vendor operation of its own
rather than borrowing a core name whose semantics do not fit. `waveform.iq` is absent for a blunter
reason, a QDAC channel being one wire.

Our hand-built rack B was generous. It handed the flux slot the entire token registry, which made
`program.set_offset` legal there. A published profile lists what the instrument actually implements,
so the first thing the real rack says about the Part 5 program is that it cannot run it at all.

That gap between the descriptor you invent while learning a protocol and the one a vendor publishes
is worth expecting. Hand-written descriptors are almost always too permissive, because you write
down the things you thought of.
"""

# %%
qblox_bus = qp.BusCapabilities(rt=qblox_seq, host=None)  # a sequencer, real time only
qdac_bus = qp.BusCapabilities(rt=None, host=qdac_chan)  # a DC source, host only

vendor_caps = qp.PlatformCapabilities(
    bus={("q", "drive"): qblox_bus, ("q", "readout"): qblox_bus, ("q", "flux"): qdac_bus},
    platform=qp.BusCapabilities(rt=core, host=core),
    default_bus_profile=qblox_bus,
)

for diag in qp.validate(program, vendor_caps)[0]:
    print(f"[{diag.severity}] {diag.code}: {diag.message}")

# %% [markdown]
r"""
So a port can need a third change, beyond the bus names and the pulse shapes of 5.7. When the new
rack drives a line with a different class of instrument, the operation itself changes. One line of
the program moves from `program.set_offset` to `program.qdac.set_offset`, and the `.qp` file records
the dependency in its header.

The rest of the experiment is untouched. Rewrite the flux line and validate again.
"""

# %%
def vendor_flux_sweep():
    """The 5.1 flux sweep with the DC write spelled as the QDAC operation it really is."""
    prog = qp.QProgram(label="flux_sweep", schema=schema)
    bias = prog.variable("bias", label="Flux bias", units="V")
    with prog.average(shots=200):
        with prog.sweep(bias, qp.Linspace(-0.05, 0.15, 101)):
            prog.qdac.set_offset(q[0].flux, bias)
            prog.set_frequency(q[0].drive, DRIVE_FREQ)
            prog.play(q[0].drive, "saturation")
            prog.sync([q[0].drive, q[0].readout])
            handle = prog.measure(q[0].readout, "readout", "weights", fields=(MF.STATE,))
    return prog, handle


vendor_program, vendor_m0 = vendor_flux_sweep()

print(qp.dumps(vendor_program).split("metadata:")[0].rstrip())
print()
print(qp.explain(vendor_program, vendor_caps))

# %% [markdown]
r"""
The `require qdac 0.1` line is now in the header, and `require qblox` is not, because the program
uses a qdac operation and no qblox operation. A `require` line records what the file needs from
whatever reads it, not the rack it happened to run on.

The plan is the more interesting half. Rack B in 5.3 filled both halves of its drive and readout
slots, so those operations could go either way and the loop settled on the host with a `forced-host`
warning. The published profiles are stricter. A Qblox sequencer operation is real-time only and a
QDAC write is host only, so the sweep now holds children with no domain in common and the validator
calls it `mixed-domain`, an error rather than a warning. The `[--]` column on the sweep means no
domain can run it.

Which turns `qp.optimize` from a speed fix into the thing that makes the program legal. The rewrite
from 5.4 hoists the DC write out of the averaging block, and every operation left inside the average
is a Qblox operation running in the sequencer.

Worth pausing on that. The same rewrite was a nice-to-have on one rack and a hard requirement on
another, and nothing about the program changed between the two. Whether an optimization is optional
turns out to be a property of the machine, in the same way the loop split was.
"""

# %%
hoisted = qp.optimize(vendor_program, vendor_caps)
print(qp.explain(hoisted, vendor_caps))

# %% [markdown]
r"""
Zero errors, zero warnings, and the averaging back in hardware where 200 shots cost 200 sequencer
iterations instead of 200 network round trips.

One caveat about the rewrite, which 5.4 stated and this is the place to see. Reordering the
loops regroups the shots. Rack A interleaved passes over the bias axis; the hoisted program takes
all 200 shots of one bias point before moving on. For a stationary device the two are the same
experiment, and the simulator's random draws still differ point by point. The fit is what has to
agree, and it does.
"""

# %%
vendor_result = qp.simulate(hoisted, model=qp.MockMeasurementModel(p_excited=p_flux, seed=11))
_, vendor_pop, vendor_fit = fit_sweet_spot(vendor_result, vendor_m0)

print("identical populations point by point:", bool(np.allclose(pop, vendor_pop)))
print(f"rack A, hand-built descriptor: {fit[1] * 1e3:.2f} mV")
print(f"rack B, published profiles:    {vendor_fit[1] * 1e3:.2f} mV")
print(f"device truth:                  {DEVICE['flux_offset'] * 1e3:.2f} mV")

# %% [markdown]
r"""
### The soft answer, in the vendor's own words

Section 5.5 said a predicate may yield a `DomainConstraint` rather than a `Diagnostic` when the
answer is "not in the sequencer, but the host can do it". Nothing in this notebook has produced one
yet, because rack B got its host-side classification from an empty `rt` half instead.
`qdac-default-v1` ships the predicate, and one change to the rack is enough to make it speak.

Give the Qblox slots a host half as well. The package's own documentation fills only the real-time
half, because that is the honest description of a sequencer, so the rack below is more forgiving
than a Qblox cluster really is. It is the shape in which the constraint has something left to
decide, and it is how any rack behaves whose fast slots can also be driven one shot at a time.
"""

# %%
either_way = qp.BusCapabilities(rt=qblox_seq, host=qblox_seq)
soft_caps = qp.PlatformCapabilities(
    bus={("q", "drive"): either_way, ("q", "readout"): either_way, ("q", "flux"): qdac_bus},
    platform=qp.BusCapabilities(rt=core, host=core),
    default_bus_profile=either_way,
)

for diag in qp.validate(vendor_program, soft_caps)[0]:
    print(f"[{diag.severity}] {diag.code}")
    print("   ", diag.message)

# %% [markdown]
r"""
The text in parentheses is not the validator's wording. It is the `reason` string the QDAC package
attached to its `DomainConstraint`, quoted back at the node where the constraint changed the plan.
A rack that declines part of a program, in the vendor's own sentence, at the loop the vendor cares
about, is the whole point of the predicate machinery from 5.5.

Both racks reach the same place by different roads. On the strict one the flux slot has no real-time
half and the sweep is an error until `qp.optimize` moves the DC write. On the forgiving one the
predicate subtracts `rt` from the binding loop and the program runs as a warning. A vendor that
publishes both the empty half and the predicate is covered either way, which is why the QDAC package
ships both.
"""


# %% [markdown]
r"""
## 5.7 Porting: names, then numbers

Two things have to change when the program moves next door, and QProgram keeps them apart on
purpose, because they change for different reasons and on different schedules.

**Bus references** change with `program.rebind`. It re-resolves every `BusRef` structurally through
a schema, so the result is still a typed `BusRef` with its element, index, kind, channel type, and
ADC flag intact. That is why it can move an experiment onto a different qubit, or onto a rack with
a different naming convention, and still validate. A textual find-and-replace would produce strings
that look right and carry no metadata, and the first thing you would lose is the channel check that
Part 1 spent a section on. Auto-generated measurement names that embed the bus are re-derived; names
you chose yourself are left alone.
"""

# %%
moved = program.rebind(elements={("q", 0): ("q", 1)})  # same rack, the other qubit
renamed = program.rebind(naming=BusNaming("{kind}_{element}{index}"))  # rack B's convention

print("original:", sorted(program.buses))
print("moved:   ", sorted(moved.buses))
print("renamed: ", sorted(renamed.buses))
print()
print(qp.dumps(renamed).split("body:")[0])  # the header carries the naming pattern
flux_line = next(line for line in qp.dumps(renamed).splitlines() if "set_offset" in line)
print("body, unchanged:", flux_line.strip())  # still a structural path, not the resolved string
print("measurement handle, original:", m0.name)
print("measurement handle, renamed: ", renamed.measurement_handles()[0].name)

# %% [markdown]
r"""
The `.qp` text of the renamed program still says `q[0].flux`, because the path form is structural:
the schema section carries the naming pattern, and the resolved string is derived from it. The file
is portable, and only the driver ever sees `flux_q0`.

**Waveforms** change with a `WaveformLibrary`. The string aliases in the program (`"saturation"`,
`"readout"`, `"weights"`) are the calibration seam from Part 3: the program says which pulse, the
library says what that pulse is on this chip. Resolution runs in three tiers, most specific first:

| Tier | Key | Use it for |
|---|---|---|
| exact | `(element, idx, kind, name)` | one qubit's calibrated pulse |
| family | `(element, kind, name)` | every qubit's readout tone |
| global | `(name,)` | integration weights, markers |

The library is a separate artifact with its own `.wfl` text format, and it is deliberately not
inside the `.qp` file. The program is the experiment and changes when you change the experiment.
The library is the calibration and changes every morning. Two lifetimes, two files, and the diff
of either one tells you something true. Merge them and neither diff means anything, because a
recalibration and a redesign look identical in the log.
"""

# %%
library = qp.WaveformLibrary()
library.set("saturation", IQPair(Square(0.02, 20_000), Square(0.0, 20_000)),
            element="q", idx=0, kind="drive")  # exact: q0's long weak tone
library.set("readout", IQPair(Square(0.2, 2000), Square(0.0, 2000)),
            element="q", kind="readout")  # family: any qubit's readout
library.set("weights", IQPair(Square(1.0, 2000), Square(1.0, 2000)))  # global

print(library.dumps())
print("round-trips:", qp.WaveformLibrary.loads(library.dumps()).dumps() == library.dumps())

# %% [markdown]
r"""
`program.with_waveforms(library)` returns a copy with the aliases replaced, re-running the
channel-type check on every replacement (an IQ pair on a single-channel bus is still an error). The
same library resolves against the *renamed* program with no edits, because the tiers are keyed on
the schema coordinate and not on the bus string.

Binding is a step you take, not something `execute()` does for you. The reference platform never
looks at a pulse, so every program in this notebook ran happily with `"saturation"` left as a
string. A real platform has to turn that alias into samples before it can upload anything, which is
why the port ends with `with_waveforms` and not with a hopeful `run`.

Order matters once a program has fragments. `with_waveforms` walks the body and does not follow a
`call` into the fragment it names, so an alias written inside a fragment body stays a string and
nothing says so. Every fragment in Part 4 holds a concrete pulse, so those programs bind as they
stand. The moment an alias moves into a fragment body, the binding step becomes
`program.expand().with_waveforms(library)`. `rebind` carries no such catch, because it expands
first whenever the program has fragments at all.

Run the bound program and fit it, and the sweet spot comes back where rack A found it. That is the
end of the port. New bus names, pulse shapes supplied from a file, the same program, the same
answer.
"""

# %%
def play_line(program):
    """Pull the single `play` statement out of a program's .qp text."""
    return next(line.strip() for line in qp.dumps(program).splitlines() if line.strip().startswith("play"))


print("renamed, still resolves:    ", play_line(renamed.with_waveforms(library)))
print("moved to q1, nothing to use:", play_line(moved.with_waveforms(library)))

# %% [markdown]
r"""
The two halves are independent only when the port is a rename. Rebinding onto a different qubit
moves the bus out from under its library entry, and the exact entry registered for `q[0].drive` does
not follow it. The alias falls through to the family entry, or stays a bare string when there is no
family entry either, as `"saturation"` does above. The behavior is correct, since q1 is a different
qubit with a different saturation tone, but it does mean that moving an experiment onto another
qubit and recalibrating it are one step rather than two.

One more property of `rebind` is worth carrying out of this section. Whether a measurement name was
auto-allocated or supplied by you is in-memory state the `.qp` format does not record, so rebinding
a program you loaded from a file treats every name as yours and leaves it stale. Rebind before
serializing, not after loading.
"""

# %%
bound = renamed.with_waveforms(library)
for line in qp.dumps(bound).splitlines():
    if "IQPair" in line:  # the two lines where an alias used to be
        print(line.strip())
print()

ported_model = qp.MockMeasurementModel(p_excited=p_flux, seed=11)
ported_result = qp.simulate(bound, model=ported_model)
_, ported_pop, ported_fit = fit_sweet_spot(ported_result, bound.measurement_handles()[0])

print(f"rack A sweet spot: {fit[1] * 1e3:.2f} mV")
print(f"rack B sweet spot: {ported_fit[1] * 1e3:.2f} mV")
print(f"device truth:      {DEVICE['flux_offset'] * 1e3:.2f} mV")
print("same populations:", bool(np.allclose(pop, ported_pop)))

# %% [markdown]
r"""
### 🧩 Exercise 5.2: port the two-dimensional arc

The `arc` program from 5.5 has the shape of the Part 3 experiment: a slow bias loop on the outside,
a fast frequency scan inside it. Take it to rack B:

1. Rebind it to the `drive_q0` naming convention with `BusNaming("{kind}_{element}{index}")`.
2. Print the bus strings before and after, to prove the names changed.
3. Validate the ported program against `caps` and compare the diagnostic codes to the original's.
4. Run `qp.optimize(ported_arc, caps)` and check whether the result differs from what went in. Say
   in a comment which diagnostic told you in advance that it would not.

The point is the third step. Renaming buses must not change what a rack thinks of the program,
because the validator routes on the schema coordinate, not on the string. If the two lists of codes
ever came out different, `rebind` would be doing something to the program beyond renaming, and every
port in this section would be suspect.
"""

# %% solution
ported_arc = arc.rebind(naming=BusNaming("{kind}_{element}{index}"))

print("before:", sorted(arc.buses))
print("after: ", sorted(ported_arc.buses))
print()
print("original codes:", [d.code for d in qp.validate(arc, caps)[0]])
print("ported codes:  ", [d.code for d in qp.validate(ported_arc, caps)[0]])
# No `reorderable-averaging` in either list, so optimize has nothing to match: the average's child
# sweep holds a second sweep, which is outside the shape the rewrite accepts.
print("optimize changed it:", qp.dumps(qp.optimize(ported_arc, caps)) != qp.dumps(ported_arc))
print()
print(qp.explain(ported_arc, caps))

# %% stub
# TODO: port the `arc` program to rack B's naming convention and check it still validates.
# 1) ported_arc = arc.rebind(naming=BusNaming("{kind}_{element}{index}"))
# 2) print sorted(arc.buses) and sorted(ported_arc.buses).
# 3) print the diagnostic codes from qp.validate(arc, caps) and qp.validate(ported_arc, caps),
#    and confirm they match.
# 4) print(qp.explain(ported_arc, caps)) and find the bias sweep in the domain column.
# 5) Compare qp.dumps(qp.optimize(ported_arc, caps)) with qp.dumps(ported_arc), and say in a
#    comment which missing diagnostic predicted the result.

# %% [markdown]
r"""
## Recap and what is next

- A platform declares three separate things: **tokens** for what it implements, **limits** for how
  much of it, and **predicates** for rules that depend on how a value is used. Each is the cheapest
  mechanism for its class of question, and each token is checked against the slot it belongs to
  (one bus, or the platform), with every slot split into a real-time half and a host half.
- `qp.validate` never raises. It returns diagnostics and an `ExecutionPlan`, and the caller decides
  what an error means. `qp.explain` draws the same plan as a tree with the domain of every node.
- The DSL has no syntax for "hardware loop" and "software loop", because that is the rack's
  decision, not the experiment's. The `forced-host` warning is where the rack tells you what it
  decided, and the cost of ignoring it is roughly a hundred times your run time.
- `qp.optimize` applies the rewrite the plan suggests. A bare `program.sync()` broadcasts across
  every bus, which drags the operation host-side and blocks the rewrite. Name the buses you mean.
- Rack B is a real pair of instruments, and `qprogram-qblox` and `qprogram-qdac` publish the
  profiles that describe them. A published profile lists what a box implements rather than what the
  language knows, so it refused `op.set_offset` on the flux line and turned the mixed loop into an
  error. On that rack `qp.optimize` is not a speed fix, it is the step that makes the program legal.
- Porting splits in two: `rebind` moves bus references structurally, `WaveformLibrary` supplies the
  numbers per bus. The program stays the same file, and the calibration lives in its own `.wfl`. A
  third change joins them when the new rack drives a line with a different class of instrument, and
  then the operation itself has to change.

Part 6 goes the other way. Instead of asking what a platform supports, you add to the language:
your own waveform, your own sweep source, and a vendor namespace with its own operation and its own
capability token, all registered from a notebook cell.
"""
