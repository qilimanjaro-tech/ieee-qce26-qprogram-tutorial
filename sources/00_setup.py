# %% [markdown]
r"""
# 00 · Setup and environment check

**Run this notebook before the tutorial.** It is a pass/fail check. If the last cell draws a curve
with a sharp dip near 7.2 GHz, you are ready.

Nothing here talks to hardware. QProgram ships a pure-Python reference platform, so every experiment
in this tutorial runs on your laptop. JupyterLab, VS Code, and Google Colab all work.

- **Local:** `pip install "qprogram[viz]" scipy` (Python 3.11 to 3.14), then run the cells below.
- **Colab:** run the cells top to bottom. The second one installs what is missing.
"""

# %% [markdown]
r"""
## What we will do today

A superconducting qubit arrives from the fab as a chip with three wires on it and no numbers
attached. Nobody knows where its readout resonator sits, where its transition frequency sits, how
hard you have to hit it to flip it, or how long it stays flipped. Bring-up is the process of turning
that chip into a row in a table. Every experiment in this tutorial is one entry in that row, run in
the only order they can be run in, because each one needs the answer from the last.

If your quantum computing so far has been circuits, here is the orientation in one paragraph. A
transmon is a circuit on a silicon chip at 10 millikelvin, and you reach it with microwaves on
coaxial cable. `X(q0)` is a 40 ns shaped burst on one line, and its area is the rotation angle.
`measure(q0)` is a 2 microsecond tone on another line, whose echo comes back as a complex number
that you threshold into a bit. Part 1 opens with that chain, wire by wire, and assumes you have
never seen a control rack.

| Experiment | Answers | Needed for |
|---|---|---|
| resonator spectroscopy | where the readout tone goes, $f_r$ | every measurement after it |
| punchout | how much readout power you can use | signal-to-noise on every shot |
| two-tone spectroscopy | where the qubit is, $f_{01}$ | pointing the drive line |
| Rabi | how hard a $\pi$ pulse hits, $a_\pi$ | every state preparation |
| $T_1$, $T_2^*$, $T_2$ | how long the qubit survives | how long a circuit can be |
| single-shot readout | the threshold, and the error it costs | any feedback at all |
| active reset | how fast you can start the next shot | throughput |

Along the way the library arrives one problem at a time, because each experiment needs a piece of it
that the one before did not. Sweeps show up when you have to step a frequency. Averaging shows up
when one shot turns out to be nothing but noise. Conditionals show up when a measurement has to
change what the program does next. By the end you will have a calibration set for a simulated qubit
and the files that produced it, in a format another lab could load.

The last two parts change the question. Instead of measuring a chip, you take a working calibration
to a rack that is wired differently and find out what a machine has to agree to before it will run
your program, then extend the language with vocabulary the core does not ship.
"""

# %% [markdown]
r"""
## Check 1: Python version

QProgram is pure Python and needs 3.11 or newer. Versions through 3.14 are tested.
"""

# %%
import sys

version = ".".join(str(v) for v in sys.version_info[:3])
if (3, 11) <= sys.version_info[:2] <= (3, 14):
    print(f"OK: Python {version} is supported.")
else:
    print(f"Python {version} is outside the tested range (3.11 to 3.14).")
    print("- On Google Colab: Runtime > Change runtime type, then pick a supported version.")
    print("- Locally: create a fresh environment, for example `uv venv --python 3.13`.")

# %% [markdown]
r"""
## Check 2: install QProgram

The cell below does nothing if QProgram is already installed, and installs it otherwise (a fresh
Colab runtime, for example). The `viz` extra pulls in matplotlib for the plots. `scipy` is not a
QProgram dependency. The tutorial uses it to fit the curves you measure. Parts 5 and 6 also read two
vendor extension packages, `qprogram-qblox` and `qprogram-qdac`, and their own first cells install
them. Neither drives an instrument.

One note on spelling before the imports start. The QProgram documentation writes a single import,
`import qprogram as qp`, and reaches the rest through it, as in `qp.BusSchema.transmon()`,
`qp.waveforms.IQDrag(...)`, and `qp.MeasurementField.IQ`. These notebooks import the names they use
most often directly instead, so a cell stays short enough to read on a projected screen. Both
spellings reach the same objects, so `BusSchema` in a cell here and `qp.BusSchema` on an example
page are one class.
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
## Check 3: build a program

The smallest experiment that tells you something about a chip is a frequency sweep of the readout
line. A transmon is not measured directly. It is measured through a resonator coupled to it, and the
resonator is a length of superconducting line that absorbs strongly at one frequency and passes
everything else. Send a tone down the feedline, step its frequency across the band the designer
aimed at, and record what comes back out. Where the transmission drops, the resonator lives.

This is the first measurement anyone runs on a new chip, and everything downstream depends on it,
because a readout tone parked at the wrong frequency returns the same number whatever the qubit is
doing.

Five names build it, one line each:

- `BusSchema.transmon()` describes the chip layout. Each qubit has a `drive` line and a `readout`
  line, and the readout line has an ADC.
- `QProgram` is the builder. Every method call appends a node to a tree.
- `program.variable(...)` declares the swept parameter.
- `average` and `sweep` are context managers that nest, so the `with` statements are the loops.
- `measure` returns a handle you use later to pull the data out.

The scan below is a survey: 100 MHz wide in 81 steps, so 1.25 MHz per point against a resonator
about 1.5 MHz wide. Roughly one sample per linewidth. That is enough to find the dip and nowhere
near enough to measure it, which is the right trade for a first look. Part 2 comes back with a 20
MHz window at 200 kHz steps once it knows where to point.
"""

# %%
import qprogram as qp
from qprogram.buses import BusSchema

schema = BusSchema.transmon()
q = schema.q

program = qp.QProgram(label="resonator_spectroscopy", schema=schema)
ro_freq = program.variable("ro_freq", label="Readout frequency", units="Hz")

with program.average(shots=100):
    with program.sweep(ro_freq, qp.Linspace(7.15e9, 7.25e9, 81)):
        program.set_frequency(q[0].readout, ro_freq)
        m0 = program.measure(q[0].readout, "readout", "weights")

print("buses touched:", sorted(program.buses))
print("measurement handle:", m0.name)

# %% [markdown]
r"""
## Check 4: read the program back as text

A QProgram is data, not a script, so it serializes. `qp.dumps` writes the `.qp` text format. One
statement per line, indentation for nesting, no hidden state. This is the file you commit next to
your results.
"""

# %%
print(qp.dumps(program))

# %% [markdown]
r"""
## Check 5: run it

`qp.simulate` runs the program on the reference platform, a pure-Python interpreter that ships
inside QProgram. It does not model pulses or timing. It models the shape of the experiment: the
loops, the averaging, and one measurement record per `measure` call.

Where the numbers come from is up to you. A `MeasurementModel` is asked for one sample per shot, and
it receives `env`, a dict of the loop variables currently bound. Here the response is the standard
notch line shape of a resonator hung off a feedline,

$$S_{21}(f) = 1 - \frac{0.9}{1 + i\,\delta}, \qquad \delta = \frac{f - f_r}{\kappa/2}$$

with $f_r$ = 7.20 GHz and $\kappa$ = 1.5 MHz. Two facts hide in that second number. A 7.2 GHz
resonance 1.5 MHz wide has a loaded quality factor of 4800, and it fills and empties in about
$1/\kappa$, or 106 ns. Both matter later. The quality factor sets how sharply the resonance moves
when the qubit changes state, and the fill time is the reason a readout pulse is measured in
microseconds rather than nanoseconds: you have to wait for the resonator to reach steady state
before the light coming back means anything.
"""

# %%
import numpy as np

F_RESONATOR = 7.20e9  # Hz, where the dip should land
KAPPA = 1.5e6  # Hz, the resonator linewidth


def transmission(bus, env):
    """Complex transmission through the readout line at the frequency currently being swept."""
    detuning = (env["ro_freq"] - F_RESONATOR) / (KAPPA / 2)
    return 1.0 - 0.9 / (1.0 + 1j * detuning)


model = qp.MockMeasurementModel(response=transmission, noise=0.01, seed=4)
result = qp.simulate(program, model=model)

data = result.get(m0)
print("dims:", data.dims, "shape:", data.shape)

# %% [markdown]
r"""
The result is an `xarray.DataArray`. Its dimensions are named after your loop variables, so the
sweep you wrote is the axis you index. `IQ` is the extra axis every integrated measurement carries.
"""

# %%
freqs = data.coords["ro_freq"].values
magnitude = np.abs(data.sel(IQ="I").values + 1j * data.sel(IQ="Q").values)

print("lowest transmission at:", freqs[magnitude.argmin()] / 1e9, "GHz")
print("expected:", F_RESONATOR / 1e9, "GHz")

# The scatter away from the dip, which is the number the closing note asks you to move.
off_resonance = magnitude[np.abs(freqs - F_RESONATOR) > 10e6]
print("baseline scatter:", round(float(off_resonance.std()), 5))

# %% [markdown]
r"""
## Check 6: plotting

Several parts of the tutorial draw figures, so the last check is matplotlib. If you see a curve with
a dip in it, plotting works.
"""

# %%
import matplotlib.pyplot as plt

plt.plot(freqs / 1e9, magnitude)
plt.axvline(F_RESONATOR / 1e9, color="grey", linestyle=":", label="true resonator")
plt.xlabel("Readout frequency (GHz)")
plt.ylabel("|S21| (arb.)")
plt.title("Resonator spectroscopy on a simulated chip")
plt.legend()
plt.show()

# %% [markdown]
r"""
A curve with a dip near 7.2 GHz means the whole stack works. Build, serialize, run, plot. ✅
See you at the tutorial.

Curious already? Change `shots=100` to `shots=2` in Check 3 and rerun the last four cells. Watch two
different things happen, or rather watch one of them fail to happen.

The dip does not move. It is 90 percent deep and the sweep steps 1.25 MHz at a time, so its
neighbours sit far above the noise at any shot count worth trying. What moves is the scatter away
from resonance, from about 0.001 to about 0.0074. Averaging 50 times fewer shots predicts a factor
of $\sqrt{50}$, near 7, and that is the factor you get.

Nothing in this tutorial ever measures anything once. Every number is a mean over some number of
shots, and the shot count buys precision at exactly that rate: four times the measurement time for
half the error bar. In a lab that arithmetic decides what you can afford to measure before the
fridge drifts out from under you, and Part 2 is where you start spending it deliberately.
"""
