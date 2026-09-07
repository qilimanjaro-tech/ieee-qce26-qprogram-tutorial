# Programming a Superconducting Qubit

**Pulse-Level Control and Calibration with QProgram**

Tutorial at [IEEE Quantum Week 2026](https://qce.quantum.ieee.org/2026/) (IEEE International Conference on Quantum Computing and Engineering), Toronto, Canada.

Tutorial ID: 126 · Two 90-minute sessions · Presented by [Qilimanjaro Quantum Tech](https://www.qilimanjaro.tech/)

This repository holds the notebooks, slides, and setup instructions for the tutorial. Materials are published here ahead of the session and stay available afterward.

The material is three notebooks. **Introduction** covers what a pulse program is made of, meaning the operation vocabulary, the bus schemas that check it, the waveforms it plays, the text format it serializes to, and the software platform that runs it. **Basics** adds the variables, sweep sources, and averaging that turn one sequence into an experiment, along with the labeled arrays that come back from a run. **Advanced** is six independent sections on fragments, measurement-conditioned control flow, extending the language with your own waveform and sweep source, vendor extension packages, implementing the platform interface, and reading the capability descriptor a machine publishes.

---

## About the tutorial

Circuit-level abstractions hide the physical layer where quantum operations become timed control signals on real hardware. Understanding and controlling this pulse layer is essential for calibration, characterization, error mitigation, and the design of high-fidelity quantum gates, yet most quantum SDKs either lack pulse-level access or couple it tightly to a single hardware vendor.

This tutorial introduces **QProgram**, an open-source, hardware-agnostic domain-specific language (DSL) for pulse-level quantum programming. QProgram provides a minimal-dependency Python library for describing pulse sequences, waveform envelopes, channel scheduling, symbolic parameter sweeps, measurement-conditioned control flow, and readout acquisition in a way that is portable across platforms: any backend can implement a compiler to translate QProgram into its native instruction set.

Two properties shape the tutorial. First, the language makes **no distinction between real-time and host-side execution**. You describe what the experiment is, and a platform's declared capabilities decide how each part of it runs. QProgram makes that decision inspectable, so a program can be validated and its execution plan explained before it reaches any hardware. Second, QProgram ships a **reference software executor**, so every example in this tutorial runs end to end on a laptop, with results shaped exactly as a real backend would return them.

By the end of the tutorial, participants will be able to design, validate, serialize, and execute pulse-level quantum experiments with QProgram.

**Keywords:** pulse programming · quantum control · QProgram · symbolic parameter sweeps · calibration workflows · execution planning · superconducting qubits · hardware-aware quantum computing

---

## Where everything is

| Path | What it is |
|------|------------|
| [Setup](#setup) | Install instructions (pip, uv, or Google Colab). Start here. |
| [`notebooks/`](notebooks/) | The three tutorial notebooks (`01_introduction`, `02_basics`, `03_advanced`), attendee versions whose exercise cells are a numbered `# TODO`, with every other cell's output already in place. |
| [`notebooks/solutions/`](notebooks/solutions/) | The same notebooks with the exercises solved. |
| [`slides/`](slides/) | The Marp deck (`qprogram_tutorial.md`) and its diagrams. See [`slides/README.md`](slides/README.md). |

---

## Setup

Please install **before the session** and open `notebooks/01_introduction.ipynb`. Its first two cells are a pass/fail check: if they print a supported Python version and `qprogram 0.1.0`, you are ready.

You have two options, **local** or **Google Colab**. Either is fine; pick whichever you prefer. Nothing in this tutorial talks to hardware, so there is no lab access to arrange and no credentials to collect.

> **QProgram 0.1.0 is pre-release.** It is an alpha library and the tutorial is pinned to that exact version, along with the two vendor extension packages the Advanced notebook reads. All three are on PyPI. Pinning matters more than usual here, because an alpha library is allowed to move under you.

### Option A: local install

QProgram is pure Python. Its only hard dependencies are numpy and xarray, there is nothing to compile, and it installs the same way on Windows, macOS, and Linux.

**Requirements:** Python **3.11, 3.12, 3.13, or 3.14**. Check with `python --version`.

**With venv and pip:**

```bash
# 1. (recommended) create a fresh virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. install QProgram and a notebook UI if you do not have one
pip install "qprogram[viz]==0.1.0" qprogram-qblox==0.1.0 qprogram-qdac==0.1.0 jupyterlab

# 3. launch Jupyter and open notebooks/01_introduction.ipynb
jupyter lab
```

The `0.1.0` tag is what the notebooks are verified against. To track the source instead, each distribution installs from its own repository:

```bash
pip install "qprogram[viz] @ git+https://github.com/qilimanjaro-tech/qprogram@0.1.0" \
            "qprogram-qblox @ git+https://github.com/qilimanjaro-tech/qprogram-qblox@0.1.0" \
            "qprogram-qdac @ git+https://github.com/qilimanjaro-tech/qprogram-qdac@0.1.0" \
            jupyterlab
```

**With uv:** [uv](https://docs.astral.sh/uv/) handles the Python version for you and downloads a supported interpreter if yours is too old:

```bash
uv venv --python 3.13
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv pip install "qprogram[viz]==0.1.0" qprogram-qblox==0.1.0 qprogram-qdac==0.1.0 jupyterlab
jupyter lab
```

### Option B: Google Colab (no local setup, needs internet)

Every notebook starts with a **"Run me first"** cell that installs QProgram when it is missing. On Colab:

1. Open the notebook in Colab (File > Upload notebook, or use the links we send).
2. Run the first cell. It takes well under a minute.
3. Continue normally.

That same first cell is a no-op locally, so the notebooks are identical in both environments. Colab's default runtime is inside the supported Python range; if it ever is not, use Runtime > Change runtime type.

### What the base install leaves out

`pip install qprogram` gives you the whole DSL: the builder, the AST, sweeps, fragments, capability validation, the `.qp` text format, and the reference simulator. Two optional **extras** add the pieces this tutorial and your editor want, in brackets after the package name:

| Extra | Adds | Used for |
|-------|------|----------|
| `viz` | matplotlib | every figure in the tutorial. `result.plot(...)` draws a measurement and `waveform.plot()` draws an envelope, and both need it. Install it. |
| `lsp` | pygls | `python -m qprogram.lsp serve`, the language server behind the VS Code extension. Optional, mentioned at the close of the Advanced notebook. |

`python -m qprogram.lsp check file.qp` and `python -m qprogram.lsp explain file.qp` need **no** extra: they run on the base install and print JSON diagnostics or the execution plan. Only `serve` needs `lsp`.

**The two vendor packages are separate distributions, not extras.** `qprogram-qblox` and `qprogram-qdac` add operations, capability profiles, and serialization for a Qblox cluster and a QDevil QDAC. Neither talks to an instrument and neither pulls in a vendor SDK. Their only dependency is `qprogram` itself, so they cost an import and nothing else. The Advanced notebook reads both of them, watches a `.qp` file load one on demand, and compares the two published profiles, which is why the install lines above include them. The Introduction and Basics notebooks never touch either one.

**Nothing else is needed.** The tutorial adds no dependency of its own beyond the `viz` extra. Every figure comes from `result.plot(...)` or `waveform.plot()`, and every number a notebook reads off an array comes from NumPy, which QProgram already requires.

### Verify your environment

Run this anywhere (a notebook cell, or `python -c`). It builds a resonator scan, runs it on the reference simulator, and round-trips it through the `.qp` text format:

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

Three lines of expected output. The version is read through `importlib.metadata` rather than through `qprogram.__version__`, because the attribute reports a `0.0.0` placeholder when the package is imported from a source tree with no installed metadata, while `importlib.metadata.version` raises there instead of reporting a wrong number in silence. `notebooks/01_introduction.ipynb` starts with the same check and goes on to draw a figure.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ERROR: Could not find a version that satisfies the requirement qprogram` | Almost always an unsupported interpreter: the distributions require Python 3.11 or newer. Check `python --version` first, then use the `git+https://` line above. |
| `ModuleNotFoundError: No module named 'qprogram_qdac'` | The Advanced notebook needs it: `pip install qprogram-qdac==0.1.0 qprogram-qblox==0.1.0`. The other two run without both. |
| `pip` picks an old resolver or fails on the extras syntax | Upgrade pip first: `pip install -U pip`. Keep the quotes around `"qprogram[viz]==0.1.0"`; some shells eat the brackets. |
| `python --version` is 3.10 or older | Make a fresh environment on a supported interpreter: `uv venv --python 3.13`. On Colab: Runtime > Change runtime type. |
| `ModuleNotFoundError: No module named 'matplotlib'` | The `viz` extra is missing: `pip install "qprogram[viz]"`. |
| `python -m qprogram.lsp serve` fails to import | The `lsp` extra is missing: `pip install "qprogram[lsp]"`. The `check` and `explain` modes do not need it. |
| Plots stay invisible | matplotlib is inline by default in a notebook kernel, so check you are in a kernel and not running the file as a script. The notebooks deliberately carry no `%matplotlib` magic. |
| A figure comes with `<Axes: ...>` printed beside it | `result.plot(...)` returns the axes it drew on, and a notebook prints the last value of a cell. Bind it (`ax = result.plot(m0)`) or end the line with a semicolon. |
| Colab offers to restart the session after the install | Re-run the first cell. The install is cached for the session. |
| A notebook cell is slower than you expect | The simulator costs roughly 10 microseconds per shot, so `shots x sweep points` is the number that matters. Drop `shots` while you are experimenting. |
| Anything else | Use Colab (Option B). It sidesteps every local toolchain problem. |

---

## Schedule

| | Part | What it covers |
|---|------|----------------|
| 1 | Introduction ([`01_introduction`](notebooks/01_introduction.ipynb)) | a program is data, the twelve operations, bus schemas and what they catch, waveforms, plotting, the `.qp` file, and one measurement run on the reference platform |
| 2 | Basics ([`02_basics`](notebooks/02_basics.ipynb)) | variables and symbolic expressions, the eight sweep sources, `average(shots)`, the measurement model and the result model, then one swept variable, two of them nested, and two of them in lockstep |
| 3 | Advanced ([`03_advanced`](notebooks/03_advanced.ipynb)) | fragments, conditionals and active reset, registering a waveform and a sweep source, the two vendor packages and a namespace of your own, implementing `PlatformProtocol`, and `PlatformCapabilities` with `qp.validate`, `qp.explain`, and `qp.optimize` |

The first two cells of the Introduction are the environment check. Run them before the session, and if the version numbers print, you are ready.

The notebooks carry more material than a live session gets through, and the excess is deliberate. They are also the thing attendees take home, so the sections a live session drops are the ones worth having in writing. Every section of the Advanced notebook stands on its own, so a session can take them in any order or leave any of them for the flight home.

---

## Everything runs on your laptop

No hardware, no cloud account, no instrument driver. QProgram ships `ReferencePlatform`, a pure-Python interpreter reachable through the `qp.simulate(program, model=...)` one-liner, and every notebook runs end to end on it. The Advanced notebook installs `qprogram-qblox` and `qprogram-qdac`, which are not drivers. They carry the operations, capability profiles, and serialization for two real instruments and nothing that opens a socket, so they run on a laptop like the rest. Each experiment supplies a small measurement model that plays the part of the fridge: it is handed the loop variables currently bound and returns one sample per shot.

The simulator has limits worth knowing before you trust anything it prints. It produces plausible numbers rather than physics from first principles, and it models no pulse shapes and no timing at all. It is there so that the *program* you write and the *analysis* you run on the results are the real thing, which is where the engineering work in a control stack lives.

---

## Target audience and prerequisites

The tutorial is for quantum hardware engineers, experimentalists, calibration scientists, and software developers who need fine-grained control over the physical signals driving quantum processors. That includes anyone building calibration routines, custom gates, or control infrastructure, and researchers moving from circuit-level programming to hardware-aware quantum computing.

**Attendees should have:**

- Working knowledge of Python programming.
- Basic understanding of quantum computing concepts (qubits, gates, measurement).
- Familiarity with the idea that quantum gates are implemented via microwave and flux pulses on physical hardware is helpful but not required, as the tutorial covers these concepts from first principles.

No prior experience with QProgram, pulse programming, or any specific quantum hardware platform is assumed.

**Content level:** Beginner 20% · Intermediate 50% · Advanced 30%

---

## Learning goals

Upon completing this tutorial, attendees will be able to:

1. Explain how circuit-level quantum gates map to timed control signals on superconducting quantum hardware.
2. Write pulse programs against typed bus schemas, using the waveform vocabulary and the timing and parameter-control operations.
3. Parameterize experiments with symbolic expressions and sweep sources, including a swept parameter inside a pulse envelope.
4. Compose multi-dimensional and lockstep experiments, and branch on a measurement outcome to change what the program does next.
5. Factor recurring sequences into reusable, parameterized fragments, and know what inlining one renames.
6. Run programs on QProgram's reference executor and work with the labeled result arrays it returns.
7. Extend the language with a waveform, a sweep source, and a vendor operation of their own, and understand how a shipped extension is loaded by the file that needs it.
8. Implement the six-member platform interface a back-end has to satisfy, and serialize programs to the portable text format.
9. Read a platform's capability declaration, interpret validation diagnostics and the resulting execution plan, and predict what the built-in rewrite will and will not do.

---

## Format

The two halves of the material do different jobs. The slides carry the physics and the concepts: what a transmon is, what the fridge and the rack around it are for, how a gate becomes a voltage, what a measurement really returns, and why any of that needs a language of its own. The notebooks carry the code. They build up the language one piece at a time and leave the background to the deck. The coding is instructor-led, and each notebook carries one exercise on a real problem, placed where it has taught enough to attempt it. The attendee notebooks leave that cell blank and `notebooks/solutions/` has the answer. Every example runs on QProgram's reference executor, so no hardware, GPU, or network access is needed for any part of the tutorial.

The figures come from the library. `result.plot(measurement)` draws whatever the array's shape asks for, a line per quadrature, a heatmap, or an IQ scatter, and hands back the Matplotlib `Axes` it drew on, so a fit, a reference line, or an annotation is one more call. `waveform.plot()` draws an envelope through the same palette, which is why a pulse and the sweep it produced look like one experiment. That is the whole reason the notebooks reach for Matplotlib as rarely as they do.

QProgram depends only on NumPy and xarray, with Matplotlib as an optional `viz` extra for waveform and result plotting, and the tutorial adds nothing to that. The [Setup](#setup) section above covers the install, whether you use pip or uv locally or run the notebooks on Google Colab, and the first two cells of `notebooks/01_introduction.ipynb` are the pass/fail check that your environment is ready.

---

## Presenters

### Vyron Vasileiadis

*Technical Lead, Qilimanjaro Quantum Tech* · [vyron@qilimanjaro.tech](mailto:vyron@qilimanjaro.tech)

Vyron leads the design and development of core quantum software infrastructure for Qilimanjaro's quantum processors. His work spans SDKs, simulators, runtimes, and execution pipelines, with a focus on connecting digital circuits, Hamiltonian-based models, pulse-level programming, and backend execution within coherent, usable abstractions. He is a key contributor to QProgram, QiliSDK, and Qilimanjaro's broader quantum computing stack.

Vyron holds an MSc in Quantum Computing and is currently pursuing a PhD in quantum control, with research focused on pulse optimization and gate design for high-fidelity operation of superconducting qubits. He has extensive experience in training, technical consulting, and public speaking, having delivered talks and technical sessions at conferences, hackathons, incubators, and innovation programs worldwide. He serves on the Advisory Board of DevNetwork.

### Flavie Le Bars

*Quantum Software Engineer, Qilimanjaro Quantum Tech* · [flavie.lebars@qilimanjaro.tech](mailto:flavie.lebars@qilimanjaro.tech)

Flavie holds an MEng in Aerospace Engineering from the University of Bristol. She works on the quantum hardware control stack, focusing on compilers that translate QProgram (pulse-level quantum programs) into low-level Q1ASM instructions for Qblox control hardware. She contributes to Qilimanjaro's hardware control library, and QPySequence, a Pythonic abstraction layer over Q1ASM assembly. Her interests span the full stack, from the physics of superconducting qubits to the software that controls them, and she enjoys solving problems that require bridging multiple disciplines.

---

## Related projects

- **[QProgram](https://github.com/qilimanjaro-tech/qprogram)** is the hardware-agnostic DSL for pulse-level quantum programming covered in this tutorial, including its reference software executor, capability and diagnostics layer, and text serialization format. The documentation is at [qilimanjaro-tech.github.io/qprogram](https://qilimanjaro-tech.github.io/qprogram).
- **[qprogram-qblox](https://github.com/qilimanjaro-tech/qprogram-qblox)** and **[qprogram-qdac](https://github.com/qilimanjaro-tech/qprogram-qdac)** are vendor extensions: separate packages that add hardware-specific operations and capability profiles for Qblox control instruments and QDevil QDAC flux biasing. The Advanced notebook reads both, watches a file load one of them on demand, and then registers a third namespace of its own, and neither package talks to an instrument.
- **[QiliSDK](https://github.com/qilimanjaro-tech/qilisdk)** is Qilimanjaro's open-source Python framework for designing and executing analog, digital, and hybrid quantum algorithms, unifying circuit-based and Hamiltonian-based workflows behind a single backend-agnostic API. It is the algorithm-level counterpart to QProgram's pulse level.

---

## Further reading

1. P. Krantz, M. Kjaergaard, F. Yan, T. P. Orlando, S. Gustavsson, and W. D. Oliver, "A quantum engineer's guide to superconducting qubits," *Applied Physics Reviews*, vol. 6, no. 2, p. 021318, 2019.
2. M. A. Serrano, R. Perez-Castillo, and M. Piattini, "Quantum software engineering," Springer, 2022.
3. T. Proctor *et al.*, "Measuring the capabilities of quantum computers," *Nature Physics*, vol. 18, pp. 75-79, 2022.
4. N. Khaneja, T. Reiss, C. Kehlet, T. Schulte-Herbrüggen, and S. J. Glaser, "Optimal control of coupled spin dynamics: design of NMR pulse sequences by gradient ascent algorithms," *Journal of Magnetic Resonance*, vol. 172, no. 2, pp. 296-305, 2005.
5. J. M. Gambetta, F. Motzoi, S. T. Merkel, and F. K. Wilhelm, "Analytic control methods for high-fidelity unitary operations in a weakly nonlinear oscillator," *Physical Review A*, vol. 83, no. 1, p. 012308, 2011.

---

## Contact

Questions about the tutorial? Reach out to [vyron@qilimanjaro.tech](mailto:vyron@qilimanjaro.tech) or [flavie.lebars@qilimanjaro.tech](mailto:flavie.lebars@qilimanjaro.tech), or open an issue in this repository.
