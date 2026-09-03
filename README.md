# Programming a Superconducting Qubit

**Pulse-Level Control and Calibration with QProgram**

Tutorial at [IEEE Quantum Week 2026](https://qce.quantum.ieee.org/2026/) (IEEE International Conference on Quantum Computing and Engineering), Toronto, Canada.

Tutorial ID: 126 · Two 90-minute sessions · Presented by [Qilimanjaro Quantum Tech](https://www.qilimanjaro.tech/)

This repository holds the notebooks, slides, and setup instructions for the tutorial. Materials are published here ahead of the session and stay available afterward.

The tutorial follows the order a real qubit gets brought up: find the readout resonator, find the qubit, calibrate a pi pulse, measure coherence, add feedback, then port the whole calibration to a different rack. Each experiment introduces the QProgram feature it needs, so the library arrives one problem at a time instead of as a feature tour.

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
| [`setup/README.md`](setup/README.md) | Install instructions (pip, uv, or Google Colab). Start here. |
| [`notebooks/`](notebooks/) | The seven tutorial notebooks (`00_setup` to `06_extending_and_shipping`), attendee versions with the exercises left blank. |
| [`notebooks/solutions/`](notebooks/solutions/) | The same notebooks with the exercises solved and the outputs embedded. |
| [`slides/`](slides/) | The Marp deck (`qprogram_tutorial.md`) and its diagrams. See [`slides/README.md`](slides/README.md). |
| [`sources/`](sources/) | The percent-format Python sources the notebooks are built from. Edit these, never the `.ipynb` files. |
| [`tools/`](tools/) | The notebook builder, the house-style checker, and the paragraph unwrapper. |

---

## Schedule

| | Part | Experiments |
|---|------|-------------|
| | Setup ([`00_setup`](notebooks/00_setup.ipynb), run it before the session) | readout pulse, one resonator scan |
| 1 | The program is data ([`01_pulse_programs`](notebooks/01_pulse_programs.ipynb)) | readout pulse and acquisition |
| 2 | Sweeps and results ([`02_sweeps_and_results`](notebooks/02_sweeps_and_results.ipynb)) | resonator spectroscopy, punchout |
| 3 | Finding the qubit ([`03_finding_the_qubit`](notebooks/03_finding_the_qubit.ipynb)) | qubit spectroscopy, Rabi, flux arc |
| 4 | Coherence and feedback ([`04_coherence_and_feedback`](notebooks/04_coherence_and_feedback.ipynb)) | T1, Ramsey, Hahn echo, single-shot readout, active reset |
| 5 | One program, many machines ([`05_one_program_many_machines`](notebooks/05_one_program_many_machines.ipynb)) | porting the flux arc to another rack, then rebuilding that rack from two published vendor profiles |
| 6 | Extending and shipping ([`06_extending_and_shipping`](notebooks/06_extending_and_shipping.ipynb)) | custom waveform, custom sweep source, vendor profile and namespace, full bring-up capstone |

The notebooks carry more material than a live session gets through, and the excess is deliberate. They are also the thing attendees take home, so the sections a live session drops are the ones worth having in writing.

---

## Everything runs on your laptop

No hardware, no cloud account, no instrument driver. QProgram ships `ReferencePlatform`, a pure-Python interpreter reachable through the `qp.simulate(program, model=...)` one-liner, and every notebook runs end to end on it. Parts 5 and 6 install `qprogram-qblox` and `qprogram-qdac`, which are not drivers. They carry the operations, capability profiles, and serialization for two real instruments and nothing that opens a socket, so they run on a laptop like the rest. Each experiment supplies a small measurement model that plays the part of the fridge: it is handed the loop variables currently bound and returns one sample per shot.

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
2. Write pulse programs against typed bus schemas, using the waveform library and the timing and parameter-control operations.
3. Parameterize experiments with symbolic expressions and sweeps, expressing standard characterization routines such as Rabi, relaxation, coherence, and spectroscopy.
4. Compose multi-dimensional experiments with parallel sweeps, and branch on measurement outcomes for feedback.
5. Factor recurring sequences into reusable, parameterized fragments.
6. Port a program across qubits and naming conventions, and bind calibration data to it separately from the experiment logic.
7. Run programs on QProgram's reference executor and work with the labeled result arrays it returns.
8. Read a platform's capability declaration, interpret validation diagnostics and the resulting execution plan, and serialize programs to the portable text format.

---

## Format

The two halves of the material do different jobs. The slides carry the physics and the concepts: what a transmon is, what the fridge and the rack around it are for, how a gate becomes a voltage, what a measurement really returns, and why any of that needs a language of its own. The notebooks carry the code. They build one experiment at a time, explain what that experiment measures and why it comes in this order, and leave the background to the deck. The coding is instructor-led, and each part ends with one exercise on a real problem. The attendee notebooks leave that cell blank and `notebooks/solutions/` has the answer. Every example runs on QProgram's reference executor, so no hardware, GPU, or network access is needed for any part of the tutorial.

The figures come from the library. `result.plot(measurement)` draws whatever the array's shape asks for, a line per quadrature, a heatmap, or an IQ scatter, and hands back the Matplotlib `Axes` it drew on, so a fit, a reference line, or an annotation is one more call. `waveform.plot()` draws an envelope through the same palette, which is why a pulse and the sweep it produced look like one experiment. That is the whole reason the notebooks reach for Matplotlib as rarely as they do.

QProgram depends only on NumPy and xarray, with Matplotlib as an optional `viz` extra for waveform and result plotting. The tutorial adds SciPy for the curve fits in Parts 3, 4, and 6. [`setup/README.md`](setup/README.md) covers all of it, whether you install locally with pip or uv or run the notebooks on Google Colab, and `notebooks/00_setup.ipynb` is the pass/fail check that your environment is ready.

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
- **[qprogram-qblox](https://github.com/qilimanjaro-tech/qprogram-qblox)** and **[qprogram-qdac](https://github.com/qilimanjaro-tech/qprogram-qdac)** are vendor extensions: separate packages that add hardware-specific operations and capability profiles for Qblox control instruments and QDevil QDAC flux biasing. Parts 5 and 6 build a rack out of the two and read their packaging, and neither talks to an instrument.
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
