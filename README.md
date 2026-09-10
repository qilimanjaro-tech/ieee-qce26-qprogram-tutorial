# Pulse-Level Programming with QProgram

Tutorial at [IEEE Quantum Week 2026](https://qce.quantum.ieee.org/2026/) (IEEE International Conference on Quantum Computing and Engineering), Toronto, Canada.

Tutorial ID: 126 · Two 90-minute sessions · Presented by [Qilimanjaro Quantum Tech](https://www.qilimanjaro.tech/)

This repository contains the notebooks, slides, and setup instructions for the tutorial. The materials are available before the session and will remain available afterward.

The tutorial includes three notebooks:

- **Introduction** covers programs, operations, bus schemas, waveforms, the `.qp` file format, and a first simulated measurement.
- **Basics** introduces variables, sweeps, and averaging, then shows how to retrieve and plot measurement results.
- **Advanced** contains six independent sections on fragments, conditionals, custom waveforms and sweep sources, vendor extensions, platform implementations, and capability validation.

---

## About the tutorial

Quantum gates are implemented through physical control signals. Working directly with these signals is important for calibration, device characterisation, and gate design. Pulse programming lets you describe the waveforms, timing, and measurements that make up an experiment.

This tutorial introduces **QProgram**, an open-source Python library and domain-specific language (DSL) for pulse-level quantum programming. It provides a common interface for describing pulse sequences, waveform envelopes, bus timing, parameter sweeps, and measurement-based control flow. A platform implementation translates these programs into operations supported by its hardware.

QProgram uses the same programming interface for operations performed by control hardware and those handled by the host computer. A platform's capability descriptor specifies what it supports and where each operation can run. You can validate a program and inspect its execution plan before running it.

QProgram also includes a **reference software executor**. The tutorial uses it with simple measurement models to generate data locally, so you can practise writing programs and analysing results without access to quantum hardware.

By the end of the tutorial, you will be able to write, validate, save, and simulate pulse-level experiments with QProgram.

**Keywords:** pulse programming · quantum control · QProgram · symbolic parameter sweeps · calibration workflows · execution planning · superconducting qubits · hardware-aware quantum computing

---

## Where everything is

| Path | Contents |
|------|----------|
| [Setup](#setup) | Installation instructions for pip, uv, and Google Colab. Start here. |
| [`notebooks/`](notebooks/) | The three student notebooks: `01_introduction`, `02_basics`, and `03_advanced`. Examples include saved outputs. Exercises have Markdown instructions and commented code hints with `...` gaps. |
| [`notebooks/solutions/`](notebooks/solutions/) | The same notebooks with complete exercise solutions. |
| [`slides/`](slides/) | The [Marp](https://marp.app/) source (`qprogram_tutorial.md`), the exported HTML presentation (`qprogram_tutorial.html`), and diagrams in `img/`. See [Slides](#slides). |

---

## Setup

Please set up your environment **before the session** and open `notebooks/01_introduction.ipynb`. Run its first two code cells and check that they report Python 3.11–3.14 and QProgram 0.2.0. The [verification example](#verify-your-environment) below also checks program construction, simulation, and serialisation.

You can run the notebooks locally or in Google Colab. Both options support the tutorial. You will need an internet connection to install the packages; Colab also requires a connection while you work.

> QProgram is under active development and currently has alpha status. The tutorial uses version **0.2.0** of QProgram and both vendor extensions. Use these exact versions so the examples match the installed APIs.

### Option A: local install

QProgram is written in Python and requires NumPy and xarray. It supports Windows, macOS, and Linux.

**Requirements:** Python **3.11, 3.12, 3.13, or 3.14**. Check your version with `python --version`.

**With venv and pip:**

```bash
# Create and activate a virtual environment.
python -m venv .venv
source .venv/bin/activate  # Windows Command Prompt: .venv\Scripts\activate

# Install the tutorial packages and JupyterLab.
pip install "qprogram[viz]==0.2.0" qprogram-qblox==0.2.0 qprogram-qdac==0.2.0 jupyterlab

# Start JupyterLab, then open notebooks/01_introduction.ipynb.
jupyter lab
```

You can also install the same versions from their Git repositories, using the `0.2.0` tags:

```bash
pip install "qprogram[viz] @ git+https://github.com/qilimanjaro-tech/qprogram@0.2.0" \
            "qprogram-qblox @ git+https://github.com/qilimanjaro-tech/qprogram-qblox@0.2.0" \
            "qprogram-qdac @ git+https://github.com/qilimanjaro-tech/qprogram-qdac@0.2.0" \
            jupyterlab
```

**With uv:**

The following commands use [uv](https://docs.astral.sh/uv/) to create an environment with Python 3.13. uv can download that interpreter if it is not already installed.

```bash
uv venv --python 3.13
source .venv/bin/activate  # Windows Command Prompt: .venv\Scripts\activate
uv pip install "qprogram[viz]==0.2.0" qprogram-qblox==0.2.0 qprogram-qdac==0.2.0 jupyterlab
jupyter lab
```

### Option B: Google Colab

Each notebook starts with a setup cell that installs its required QProgram packages if they are missing.

1. Upload the notebook to Colab using **File > Upload notebook**, or open a provided Colab link.
2. Run the setup cells and wait for installation to finish.
3. Continue through the notebook in order.

The same setup cells work locally and skip installation when the packages are already available. If Colab asks you to restart the runtime, restart it and run the setup cells again.

### Optional extras and vendor packages

The base `qprogram` package includes the program builder, sweeps, fragments, capability validation, `.qp` serialisation, and the reference executor. Optional extras add plotting and language-server support:

| Extra | Dependency | Purpose |
|-------|------------|---------|
| `viz` | Matplotlib | Provides plotting for measurement results and waveforms. Required for the tutorial and included in the commands above. |
| `lsp` | pygls | Runs the language server with `python -m qprogram.lsp serve`. Optional for the tutorial. |

The commands `python -m qprogram.lsp check file.qp` and `python -m qprogram.lsp explain file.qp` work with the base package and print JSON output. Only `serve` requires the `lsp` extra.

The vendor extensions, `qprogram-qblox` and `qprogram-qdac`, are installed as separate packages. They define operations, capability profiles, and serialisation support for Qblox control instruments and the QDevil QDAC. They depend on QProgram and do not install instrument drivers or connect to hardware.

**Advanced** uses both packages to introduce vendor namespaces, automatic loading of extensions from `.qp` files, and capability profiles. **Introduction** and **Basics** use only QProgram with the `viz` extra. JupyterLab provides the local notebook interface.

### Verify your environment

Run this example in a notebook cell or save it as a Python script. It builds a readout-frequency sweep, generates mock measurements, and checks that the program can be serialised and loaded again.

```python
from importlib.metadata import version

import qprogram as qp
from qprogram.buses import BusSchema

print("qprogram", version("qprogram"))

schema = BusSchema.transmon()
program = qp.QProgram(label="smoke", schema=schema)
freq = program.variable("ro_freq")

with program.average(shots=10):
    with program.sweep(freq, qp.Linspace(7.1e9, 7.3e9, 5)):
        program.set_frequency(schema.q[0].readout, freq)
        m0 = program.measure(schema.q[0].readout, "readout", "weights")

result = qp.simulate(program, model=qp.MockMeasurementModel(response=lambda bus, env: 1 + 0j))
print(result.get(m0).dims)
print(qp.loads(qp.dumps(program)).body == program.body)
```

Expected output:

```text
qprogram 0.2.0
('ro_freq', 'IQ')
True
```

`importlib.metadata.version` reads the installed package version. The final line confirms that the original and loaded program bodies are structurally equal.

### Troubleshooting

| Symptom | What to check |
|---------|---------------|
| `Could not find a version that satisfies the requirement qprogram` | Check that `python --version` reports Python 3.11–3.14 and that pip can access PyPI. The tagged source installation above is another option. |
| `ModuleNotFoundError: No module named 'qprogram_qdac'` or `'qprogram_qblox'` | Install both extensions for **Advanced**: `pip install qprogram-qdac==0.2.0 qprogram-qblox==0.2.0`. |
| pip reports a resolver or extras-syntax error | Upgrade pip with `pip install -U pip`. Keep the quotes around `"qprogram[viz]==0.2.0"` so the shell passes the brackets unchanged. |
| Python is 3.10 or older | Create an environment with a supported interpreter, for example with `uv venv --python 3.13`, then activate it and install the tutorial packages. |
| `ModuleNotFoundError: No module named 'matplotlib'` | Install the plotting extra: `pip install "qprogram[viz]==0.2.0"`. |
| `python -m qprogram.lsp serve` fails because pygls is missing | Install the language-server extra: `pip install "qprogram[lsp]==0.2.0"`. The `check` and `explain` commands do not need it. |
| Plots do not appear | Check for an error in the plotting cell and make sure the cell runs `plt.show()`. When using a notebook, also check that it is using the environment where you installed the packages. |
| `<Axes: ...>` appears beside a figure | The notebook is displaying the value returned by the plotting method. Assign it to a variable, such as `ax = result.plot(m0)`, or end the call with a semicolon. |
| Colab requests a restart after installation | Restart the runtime, then rerun the setup cells before continuing. |
| A simulation takes longer than expected | Its workload increases with the number of shots and sweep points. Reduce the shot count or the number of points while trying changes. |
| A local setup problem persists | Try Colab, or ask an instructor for help and include the full error message. |

---

## Schedule

| Part | Notebook | Topics |
|------|----------|--------|
| 1 | [Introduction](notebooks/01_introduction.ipynb) | Building programs, adding operations, validating buses, defining and plotting waveforms, saving `.qp` files, and generating a first measurement result. |
| 2 | [Basics](notebooks/02_basics.ipynb) | Variables, expressions, sweep sources, averaging, measurement models, result arrays, and nested or paired sweeps. |
| 3 | [Advanced](notebooks/03_advanced.ipynb) | Fragments, conditionals, custom waveforms and sweep sources, vendor extensions, platform implementations, validation, execution plans, and optimisation. |

The notebooks include more examples than we will cover during the live sessions. The remaining sections are available for further practice and reference. Each section of **Advanced** can be run independently after its two setup cells.

---

## Slides

The slides introduce the physics and hardware behind the examples: superconducting qubits, cryogenic and control equipment, microwave and flux pulses, and readout. They then explain QProgram's role and summarise the concepts covered in each notebook.

To view the presentation, open [`slides/qprogram_tutorial.html`](slides/qprogram_tutorial.html). Keep the `img/` folder beside the HTML file so the diagrams can load. Use the arrow keys to navigate, `f` for fullscreen, and `p` for presenter view.

The source is [`slides/qprogram_tutorial.md`](slides/qprogram_tutorial.md). You can edit it in VS Code with the **Marp for VS Code** extension, which provides a live preview and export to HTML, PDF, and PPTX.

---

## Running the examples locally

All three notebooks run without connected quantum hardware or instrument drivers. For examples that generate measurement results, `qp.simulate(program, model=...)` runs the program on QProgram's `ReferencePlatform`. A measurement model supplies samples using the current sweep-variable values. The vendor-extension examples define and inspect hardware-specific operations without connecting to instruments.

The reference executor follows the program's control flow and organises the results into labelled arrays. It does not simulate pulse dynamics or hardware timing. The measurement models provide simple responses for practising program construction, data analysis, and plotting.

After downloading the materials and installing the packages, the local examples can run offline. Google Colab requires an internet connection.

---

## Target audience and prerequisites

This tutorial is for quantum hardware engineers, experimentalists, calibration scientists, and software developers working with quantum control. It is also suitable for researchers who have used circuit-based tools and want to learn how experiments are described at the pulse level.

**You should be comfortable with:**

- Writing Python code.
- Basic quantum computing concepts, including qubits, gates, and measurement.

Familiarity with microwave and flux pulses is helpful, but the introductory slides explain these concepts. No prior experience with QProgram or a particular hardware platform is required.

**Content level:** Beginner 20% · Intermediate 50% · Advanced 30%

---

## Learning goals

By the end of the tutorial, you will be able to:

1. Explain how control pulses implement quantum gates on superconducting hardware.
2. Write pulse programs using bus schemas, waveforms, timing operations, and bus settings.
3. Use variables and expressions to parameterise operations and waveform envelopes.
4. Build nested and paired sweeps, average measurements, and choose operations based on a measured state.
5. Define reusable fragments and inspect how their parameters are substituted during expansion.
6. Run simulated experiments and retrieve, analyse, and plot their labelled result arrays.
7. Add custom waveforms, sweep sources, and vendor operations, and understand how `.qp` files load vendor extensions.
8. Implement QProgram's platform interface and save and load programs in the `.qp` format.
9. Validate a program against a platform's capabilities, interpret its execution plan, and inspect the effects of optimisation.

---

## Format

The sessions combine short explanations with instructor-led coding. The slides provide the physical background and summarise the main ideas. The notebooks introduce the APIs through worked examples.

Each notebook ends with an exercise:

- **Exercise 1.1:** Define a flux-tunable transmon schema, build a preparation and readout sequence, save and load it, and check an invalid measurement.
- **Exercise 2.1:** Sweep the drive amplitude, estimate a pi-pulse amplitude from simulated measurements, and plot the result.
- **Exercise 3.1:** Define a simple custom waveform, use it in a parameterised fragment, set a QDAC flux bias, and call the fragment from an `if_`/`else_` conditional.

Exercise instructions appear in Markdown. The student code cells contain commented hints with `...` for you to complete. Full solutions are available in `notebooks/solutions/`.

The examples use `result.plot(...)` and `waveform.plot()` for plotting. You can add reference lines, labels, and other annotations through the returned Matplotlib axes.

---

## Presenters

### Vyron Vasileiadis

*Technical Lead, Qilimanjaro Quantum Tech* · [vyron@qilimanjaro.tech](mailto:vyron@qilimanjaro.tech)

Vyron leads the design and development of software infrastructure for Qilimanjaro's quantum processors. His work covers SDKs, simulators, runtimes, and execution pipelines, connecting circuit and Hamiltonian models with pulse programming and backend execution. He contributes to QProgram, QiliSDK, and Qilimanjaro's broader software stack.

He holds an MSc in Quantum Computing and is pursuing a PhD in quantum control, focusing on pulse optimisation and gate design for superconducting qubits. He has experience in training, technical consulting, and public speaking, including talks and workshops at conferences, hackathons, incubators, and innovation programmes. He serves on the Advisory Board of DevNetwork.

### Flavie Le Bars

*Quantum Software Engineer, Qilimanjaro Quantum Tech* · [flavie.lebars@qilimanjaro.tech](mailto:flavie.lebars@qilimanjaro.tech)

Flavie holds an MEng in Aerospace Engineering from the University of Bristol. She works on the quantum hardware control stack, developing compilers that translate QProgram into Q1ASM instructions for Qblox hardware. She contributes to Qilimanjaro's hardware control library and QPySequence, a Python interface for building Q1ASM programs. Her interests span superconducting-qubit physics and control software, particularly problems that require understanding both.

---

## Related projects

- **[QProgram](https://github.com/qilimanjaro-tech/qprogram)** is the pulse-programming library used in this tutorial. It includes the reference executor, capability validation, execution planning, and `.qp` serialisation. See the [reference documentation](https://qilimanjaro-tech.github.io/qprogram).
- **[qprogram-qblox](https://github.com/qilimanjaro-tech/qprogram-qblox)** and **[qprogram-qdac](https://github.com/qilimanjaro-tech/qprogram-qdac)** add operations and capability profiles for Qblox instruments and QDevil QDAC channels. The **Advanced** notebook uses them to demonstrate vendor extensions and loading requirements from `.qp` files.
- **[QiliSDK](https://github.com/qilimanjaro-tech/qilisdk)** is Qilimanjaro's open-source Python framework for analog, digital, and hybrid quantum algorithms. It supports circuit and Hamiltonian models through a common API and complements QProgram's focus on pulse-level control.

---

## Further reading

1. P. Krantz, M. Kjaergaard, F. Yan, T. P. Orlando, S. Gustavsson, and W. D. Oliver, "A quantum engineer's guide to superconducting qubits," *Applied Physics Reviews*, vol. 6, no. 2, p. 021318, 2019.
2. M. A. Serrano, R. Perez-Castillo, and M. Piattini, "Quantum software engineering," Springer, 2022.
3. T. Proctor *et al.*, "Measuring the capabilities of quantum computers," *Nature Physics*, vol. 18, pp. 75-79, 2022.
4. N. Khaneja, T. Reiss, C. Kehlet, T. Schulte-Herbrüggen, and S. J. Glaser, "Optimal control of coupled spin dynamics: design of NMR pulse sequences by gradient ascent algorithms," *Journal of Magnetic Resonance*, vol. 172, no. 2, pp. 296-305, 2005.
5. J. M. Gambetta, F. Motzoi, S. T. Merkel, and F. K. Wilhelm, "Analytic control methods for high-fidelity unitary operations in a weakly nonlinear oscillator," *Physical Review A*, vol. 83, no. 1, p. 012308, 2011.

---

## Contact

For questions about the tutorial, email [vyron@qilimanjaro.tech](mailto:vyron@qilimanjaro.tech) or [flavie.lebars@qilimanjaro.tech](mailto:flavie.lebars@qilimanjaro.tech), or open an issue in this repository.
