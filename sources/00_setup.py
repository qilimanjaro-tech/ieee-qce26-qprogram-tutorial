# %% [markdown]
r"""
# 00 · Setup and environment check

**Run this notebook before the tutorial.** It is pass/fail. If the last cell draws a curve with a sharp dip near 7.2 GHz, your environment is ready and there is nothing else to prepare.

Nothing here talks to hardware. QProgram ships a pure-Python reference platform, so every experiment in this tutorial runs on your laptop. JupyterLab, VS Code, and Google Colab all work.

- **Local:** `pip install "qprogram[viz]==0.1.0" scipy` (Python 3.11 to 3.14), then run the cells below.
- **Colab:** run the cells top to bottom. The second one installs what is missing.
"""

# %% [markdown]
r"""
## What we will do today

A superconducting qubit arrives from the fab as a chip with three wires on it and no numbers attached. Nobody knows where its readout resonator sits, where its transition frequency sits, how hard you have to hit it to flip it, or how long it stays flipped. Bring-up is the work of turning that chip into a row in a table, and each experiment in the tutorial fills one cell of that row.

| Experiment | Answers | Needed for |
|---|---|---|
| resonator spectroscopy | where the readout tone goes, $f_r$ | every measurement after it |
| punchout | how much readout power you can use | signal-to-noise on every shot |
| two-tone spectroscopy | where the qubit is, $f_{01}$ | pointing the drive line |
| Rabi | how hard a $\pi$ pulse hits, $a_\pi$ | every state preparation |
| $T_1$, $T_2^*$, $T_2$ | how long the qubit survives | how long a circuit can be |
| single-shot readout | the threshold, and the error it costs | any feedback at all |
| active reset | how fast you can start the next shot | throughput |

The third column is a chain, not a list of nice-to-haves. The rows run in the order printed and in no other, because each experiment is pointed by the answer the one above it returned. A qubit scan needs a working readout to see anything at all, a Rabi needs a qubit frequency to drive, a coherence curve needs a $\pi$ pulse to prepare the state it then watches decay. Get the first row wrong and the other six are measuring the wrong thing without telling you.

The library arrives at the same pace, one problem at a time. Sweeps show up when you have to step a frequency. Averaging shows up when one shot turns out to be nothing but noise. Conditionals show up when a measurement has to change what the program does next. The last two parts change the question. Part 5 takes a finished calibration to a rack that is wired differently, to find out what a machine has to agree to before it will run your program, and Part 6 adds to the language itself and ships the result as one file.

Six checks follow, each printing one line you can read at a glance. The last one draws the picture that says the whole stack works.
"""

# %% [markdown]
r"""
## Check 1: Python version

Start with the interpreter, since nothing below runs without it. QProgram is pure Python and needs 3.11 or newer, and versions through 3.14 are tested. The fix differs by platform, so the cell prints the one that applies to you.
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

With a supported interpreter the next cell does nothing at all if QProgram and SciPy are already installed, and installs them otherwise, which is the case on a fresh Colab runtime. The `viz` extra pulls in matplotlib for the plots. `scipy` is not a QProgram dependency, and the tutorial uses it to fit the curves you measure from Part 3 on, so the cell checks for it here rather than letting Part 3 be where you find out. Parts 5 and 6 also read two vendor extension packages, `qprogram-qblox` and `qprogram-qdac`, and their own first cells install them. Neither drives an instrument.

One note on spelling before the imports start. The QProgram documentation writes a single import, `import qprogram as qp`, and reaches the rest through it, as in `qp.BusSchema.transmon()`, `qp.waveforms.IQDrag(...)`, and `qp.MeasurementField.IQ`. These notebooks import the names they use most often directly instead, so a cell stays short enough to read on a projected screen. Both spellings reach the same objects, so `BusSchema` in a cell here and `qp.BusSchema` on an example page are one class.
"""

# %%
# Run me first. A no-op when both are already installed, an install when either is missing
# (a fresh Google Colab runtime, for example).
try:
    import qprogram  # noqa: F401
    import scipy  # noqa: F401
except ImportError:
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "qprogram[viz]==0.1.0", "scipy"],
        check=True,
    )
    import qprogram  # noqa: F401
    import scipy  # noqa: F401

from importlib.metadata import version

print("qprogram", version("qprogram"), "| scipy", version("scipy"))

# %% [markdown]
r"""
## Check 3: build a program

The library is in, so the remaining checks build, serialize, run, and draw one real experiment, the resonator spectroscopy that opens the table above. A transmon is never measured directly. It is measured through a resonator coupled to it, so the first scan on a new chip sends a tone down the feedline, steps its frequency across the band the designer aimed at, and records what comes back. Where the transmission drops, the resonator lives. Everything downstream depends on that number, because a readout tone parked at the wrong frequency returns the same value whatever the qubit is doing.

Five names build the scan, one line each. `BusSchema.transmon()` describes the chip layout, giving each qubit a `drive` line and a `readout` line with an ADC on it. `QProgram` is the builder, and every method call on it appends a node to a tree. `program.variable(...)` declares the swept parameter along with the label and units that later name its axis. `average` and `sweep` are context managers that nest, so the `with` statements are the loops. And `measure` returns a handle you use later to pull the data out.

The scan below is a survey, 100 MHz wide in 81 steps, so 1.25 MHz per point against a resonator about 1.5 MHz wide. Roughly one sample per linewidth is enough to find the dip and nowhere near enough to measure it, which is the right trade for a first look. Part 2 comes back with a 20 MHz window at 200 kHz steps once it knows where to point.
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

Nothing ran yet. What the last cell built is a tree, and because a QProgram is data rather than a script, that tree serializes. `qp.dumps` writes the `.qp` text format, one statement per line, indentation for nesting, no hidden state. This is the file you commit next to your results.
"""

# %%
print(qp.dumps(program))

# %% [markdown]
r"""
## Check 5: run it

`qp.simulate` runs the program on the reference platform, a pure-Python interpreter that ships inside QProgram. It does not model pulses or timing. It models the shape of the experiment, meaning the loops, the averaging, and one measurement record per `measure` call.

Where the numbers come from is up to you. A `MeasurementModel` is asked for one sample per shot, and it receives `env`, a dict of the loop variables currently bound. Here the response is the standard notch line shape of a resonator hung off a feedline,

$$S_{21}(f) = 1 - \frac{0.9}{1 + i\,\delta}, \qquad \delta = \frac{f - f_r}{\kappa/2}$$

with $f_r$ = 7.20 GHz and $\kappa$ = 1.5 MHz. Two facts hide in that second number. A 7.2 GHz resonance 1.5 MHz wide has a loaded quality factor of 4800, and it fills and empties in about $1/2\pi\kappa$, or 106 ns. Both matter later. The quality factor sets how sharply the resonance moves when the qubit changes state, and the fill time is the reason a readout pulse is measured in microseconds rather than nanoseconds, since you have to wait for the resonator to reach steady state before the light coming back means anything.
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
Those dimensions are the shape of what you wrote. The result is an `xarray.DataArray` whose axes are named after your loop variables, so the sweep you declared is the axis you index. `IQ` is the extra axis every integrated measurement carries, holding the two quadratures of each point. Combine them and the dip should sit where the model put it.
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

Several parts of the tutorial draw figures, so the last check is the drawing path. The result knows how to plot itself, and it takes the axis label straight off the variable you declared in Check 3. `coords` restates the frequency in GHz for the figure without touching the stored array, `value` names the measured quantity, and the axes that comes back takes the reference line at the true resonator. If the figure comes up, plotting works.
"""

# %%
import matplotlib.pyplot as plt
from qprogram.plotting import Quantity

ax = result.plot(
    m0,
    channels="magnitude",
    coords={"ro_freq": Quantity(units="GHz", transform=lambda v: v / 1e9)},
    value=Quantity("Readout magnitude"),
    title="Resonator spectroscopy on a simulated chip",
)
ax.axvline(F_RESONATOR / 1e9, color="grey", linestyle=":", label="true resonator")
ax.legend(fontsize=8)
plt.show()

# %% [markdown]
r"""
A curve with a dip near 7.2 GHz means the whole stack works. Build, serialize, run, plot. See you at the tutorial.

Curious already? Change `shots=100` to `shots=2` in Check 3 and rerun from there. Watch two different things happen, or rather watch one of them fail to happen.

The dip does not move. It is 90 percent deep and the sweep steps 1.25 MHz at a time, so its neighbours sit far above the noise at any shot count worth trying. What moves is the scatter away from resonance, from about 0.001 to about 0.0074. Averaging 50 times fewer shots predicts a factor of $\sqrt{50}$, near 7, and that is the factor you get.

Nothing in this tutorial ever measures anything once. Every number is a mean over some number of shots, and the shot count buys precision at exactly that rate: four times the measurement time for half the error bar. In a lab that arithmetic decides what you can afford to measure before the fridge drifts out from under you, and Part 2 is where you start spending it deliberately.
"""
