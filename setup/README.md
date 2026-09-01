# Setup: *Programming a Superconducting Qubit* (QCE 2026)

Please install **before the session** and run `notebooks/00_setup.ipynb`. It is a pass/fail check: if
its last cell draws a curve with a sharp dip near 7.2 GHz, you are ready.

You have two options, **local** or **Google Colab**. Either is fine; pick whichever you prefer.
Nothing in this tutorial talks to hardware, so there is no lab access to arrange and no credentials
to collect.

> **QProgram 0.1.0 is pre-release.** It is an alpha library and the tutorial is pinned to that exact
> version, along with the two vendor extension packages Parts 5 and 6 read. All three are on PyPI.
> Pinning matters more than usual here, because an alpha library is allowed to move under you.

---

## Option A: local install

QProgram is pure Python. Its only hard dependencies are numpy and xarray, there is nothing to
compile, and it installs the same way on Windows, macOS, and Linux.

**Requirements:** Python **3.11, 3.12, 3.13, or 3.14**. Check with `python --version`.

### A1: with venv + pip

```bash
# 1. (recommended) create a fresh virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. install QProgram, scipy, and a notebook UI if you do not have one
pip install "qprogram[viz]==0.1.0" qprogram-qblox==0.1.0 qprogram-qdac==0.1.0 scipy jupyterlab

# 3. launch Jupyter and open notebooks/00_setup.ipynb
jupyter lab
```

The `v0.1.0` tag is what the notebooks are verified against. To track the source instead, each
distribution installs from its own repository:

```bash
pip install "qprogram[viz] @ git+https://github.com/qilimanjaro-tech/qprogram@v0.1.0" scipy jupyterlab
```

### A2: with uv

[uv](https://docs.astral.sh/uv/) handles the Python version for you and downloads a supported
interpreter if yours is too old:

```bash
uv venv --python 3.13
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv pip install "qprogram[viz]==0.1.0" qprogram-qblox==0.1.0 qprogram-qdac==0.1.0 scipy jupyterlab
jupyter lab
```

---

## Extras: what the base install leaves out

`pip install qprogram` gives you the whole DSL: the builder, the AST, sweeps, fragments, capability
validation, the `.qp` text format, and the reference simulator. Two optional **extras** add the
pieces this tutorial and your editor want, in brackets after the package name:

| Extra | Adds | Used for |
|-------|------|----------|
| `viz` | matplotlib | every plot in the tutorial, and `Waveform.plot()`. Install it. |
| `lsp` | pygls | `python -m qprogram.lsp serve`, the language server behind the VS Code extension. Optional, mentioned in Part 6. |

`python -m qprogram.lsp check file.qp` and `python -m qprogram.lsp explain file.qp` need **no** extra:
they run on the base install and print JSON diagnostics or the execution plan. Only `serve` needs
`lsp`.

**The two vendor packages are separate distributions, not extras.** `qprogram-qblox` and
`qprogram-qdac` add operations, capability profiles, and serialization for a Qblox cluster and a
QDevil QDAC. Neither talks to an instrument and neither pulls in a vendor SDK. Their only dependency
is `qprogram` itself, so they cost an import and nothing else. Part 5 builds a rack out of the two
published profiles and Part 6 reads their packaging, which is why the install lines above include
them. Parts 0 to 4 never touch either one.

**scipy is not a QProgram dependency.** The tutorial uses it for exactly one thing,
`scipy.optimize.curve_fit`: the Lorentzian and Rabi fits in Part 3, the decay fits in Part 4, and the
capstone in Part 6. Install it alongside QProgram:

```bash
pip install "qprogram[viz]==0.1.0" scipy
```

---

## Option B: Google Colab (no local setup, needs internet)

Every notebook starts with a **"Run me first"** cell that installs QProgram when it is missing. On
Colab:

1. Open the notebook in Colab (File > Upload notebook, or use the links we send).
2. Run the first cell. It takes well under a minute.
3. Continue normally.

That same first cell is a no-op locally, so the notebooks are identical in both environments. Colab's
default runtime is inside the supported Python range; if it ever is not, use Runtime > Change runtime
type.

---

## Verify your environment

Run this anywhere (a notebook cell, or `python -c`). It builds a resonator scan, runs it on the
reference simulator, and round-trips it through the `.qp` text format:

```python
from importlib.metadata import version

import qprogram as qp
from qprogram.buses import BusSchema

print("qprogram", version("qprogram"))                     # 0.1.0

schema = BusSchema.transmon()
program = qp.QProgram(label="smoke", schema=schema)
freq = program.variable("ro_freq")
with program.average(shots=10):
    with program.sweep(freq, qp.Linspace(7.1e9, 7.3e9, 5)):
        program.set_frequency(schema.q[0].readout, freq)
        m0 = program.measure(schema.q[0].readout, "readout", "weights")

result = qp.simulate(program, model=qp.MockMeasurementModel(response=lambda bus, env: 1 + 0j))
print(result.get(m0).dims)                                 # ('ro_freq', 'IQ')
print(qp.loads(qp.dumps(program)).body == program.body)     # True
```

Three lines of expected output. The version is read through `importlib.metadata` rather than through
`qprogram.__version__`, because the attribute reports a `0.0.0` placeholder when the package is
imported from a source tree with no installed metadata, while `importlib.metadata.version` raises
there instead of quietly reporting the wrong number. `notebooks/00_setup.ipynb` does all of this plus
the plot.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ERROR: Could not find a version that satisfies the requirement qprogram` | Almost always an unsupported interpreter: the distributions require Python 3.11 or newer. Check `python --version` first, then use the `git+https://` line from A1. |
| `ModuleNotFoundError: No module named 'qprogram_qdac'` | Part 5 needs it: `pip install qprogram-qdac==0.1.0 qprogram-qblox==0.1.0`. Parts 0 to 4 run without both. |
| `pip` picks an old resolver or fails on the extras syntax | Upgrade pip first: `pip install -U pip`. Keep the quotes around `"qprogram[viz]==0.1.0"`; some shells eat the brackets. |
| `python --version` is 3.10 or older | Make a fresh environment on a supported interpreter: `uv venv --python 3.13`. On Colab: Runtime > Change runtime type. |
| `ModuleNotFoundError: No module named 'matplotlib'` | The `viz` extra is missing: `pip install "qprogram[viz]"`. |
| `ModuleNotFoundError: No module named 'scipy'` | `pip install scipy`. Parts 3, 4, and 6 fit curves. |
| `python -m qprogram.lsp serve` fails to import | The `lsp` extra is missing: `pip install "qprogram[lsp]"`. The `check` and `explain` modes do not need it. |
| Plots stay invisible | matplotlib is inline by default in a notebook kernel, so check you are in a kernel and not running the file as a script. The notebooks deliberately carry no `%matplotlib` magic. |
| Colab offers to restart the session after the install | Re-run the first cell. The install is cached for the session. |
| A notebook cell is slower than you expect | The simulator costs roughly 10 microseconds per shot, so `shots x sweep points` is the number that matters. Drop `shots` while you are experimenting. |
| Anything else | Use Colab (Option B). It sidesteps every local toolchain problem. |

Source: <https://github.com/qilimanjaro-tech/qprogram> · Docs:
<https://qilimanjaro-tech.github.io/qprogram>
