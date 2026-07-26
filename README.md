# Pulse-Level Programming with QProgram

**Tutorial at [IEEE Quantum Week 2026](https://qce.quantum.ieee.org/2026/) (IEEE International Conference on Quantum Computing and Engineering) — Toronto, Canada**

Tutorial ID: 126 · Duration: two 90-minute sessions · Presented by [Qilimanjaro Quantum Tech](https://www.qilimanjaro.tech/)

This repository hosts the agenda, notebooks, slides, and supplementary materials for the tutorial. It is updated as the tutorial materials are finalized — check back for the latest version.

---

## About the Tutorial

Circuit-level abstractions hide the physical layer where quantum operations become timed control signals on real hardware. Understanding and controlling this pulse layer is essential for calibration, characterization, error mitigation, and the design of high-fidelity quantum gates — yet most quantum SDKs either lack pulse-level access or couple it tightly to a single hardware vendor.

This tutorial introduces **QProgram**, an open-source, hardware-agnostic domain-specific language (DSL) for pulse-level quantum programming. QProgram provides a minimal-dependency Python library for describing pulse sequences, waveform envelopes, channel scheduling, symbolic parameter sweeps, measurement-conditioned control flow, and readout acquisition in a way that is portable across platforms: any backend can implement a compiler to translate QProgram into its native instruction set.

Two properties shape the tutorial. First, the language makes **no distinction between real-time and host-side execution** — you describe what the experiment is, and a platform's declared capabilities decide how each part of it runs. QProgram makes that decision inspectable, so a program can be validated and its execution plan explained before it reaches any hardware. Second, QProgram ships a **reference software executor**, so every example in this tutorial runs end to end on a laptop, with results shaped exactly as a real backend would return them.

- **Session 1** covers the programming model: bus schemas for typed channel references, the waveform library, pulse operations and timing, and symbolic variables and sweeps — building up to complete experiments such as Rabi oscillations and $T_1$ relaxation, run and plotted on the reference executor.
- **Session 2** covers the workflows built on top: parallel multi-dimensional sweeps, measurement handles and feedback, fragments for composition, porting programs across qubits and calibrations, the portable text formats, vendor extensions, and the capability and diagnostics layer that decides where a program runs.

By the end of the tutorial, participants will be able to design, validate, serialize, and execute pulse-level quantum experiments with QProgram.

**Keywords:** pulse programming · quantum control · QProgram · symbolic parameter sweeps · calibration workflows · execution planning · superconducting qubits · hardware-aware quantum computing

---

## Agenda

Two 90-minute sessions with a break in between. Each session includes two guided hands-on exercises that attendees run on their own laptops.

### Session 1 — Pulse Programming Fundamentals (90 min)

| # | Topic | Time |
|---|-------|------|
| 1 | From Circuits to Pulses | 10 min |
| 2 | Programs and Bus Schemas | 15 min |
| 3 | Waveform Design | 15 min |
| 4 | Pulse Operations and Timing | 15 min |
| 5 | Variables, Expressions, and Sweeps | 20 min |
| 6 | Running Programs: The Reference Executor | 10 min |
| 7 | Wrap-up and Q&A | 5 min |

#### 1. From Circuits to Pulses (10 min)

How a gate on a circuit diagram becomes a microwave pulse, a flux excursion, and a readout tone — and why the pulse layer is where calibration, custom gate design, and device characterization actually happen. Introduces QProgram's design stance: describe what the experiment is, and leave the choice of how it runs to the platform.

#### 2. Programs and Bus Schemas (15 min)

A QProgram is a tree of nested blocks and operations, and every operation targets a bus. This chapter covers how programs are built and how bus schemas give those channels typed, autocompleting names for common qubit architectures — transmons, flux-tunable transmons, fluxonium. Because a bus reference carries its own structure, a mistake such as sending an IQ pulse to a single-channel line is caught as the program is written rather than when it runs.

#### 3. Waveform Design (15 min)

A tour of the waveform library: the standard single-channel envelopes, the IQ waveforms built on top of them, and the parameters that matter physically. Any numeric parameter can be left symbolic, which is what later makes it sweepable. We close by defining a custom envelope for the cases the built-ins don't cover.

#### 4. Pulse Operations and Timing (15 min)

The instruction set — playing waveforms, acquiring readout with integration weights, waiting, synchronizing channels, and adjusting frequency, phase, gain, and offset. This is also where the distinction between real-time signal operations and instrument configuration first appears; it returns in Session 2 as the thing that determines where a block of a program can run.

#### 5. Variables, Expressions, and Sweeps (20 min)

Experiments are parameterized, not fixed. This chapter introduces symbolic variables and the expressions built from them, then the block constructs that turn a single pulse sequence into a measurement: linear and array sweeps, averaging, and plain grouping. By the end, a Rabi and a $T_1$ experiment are each expressed as one program.

> **Hands-on:** Build both experiments from scratch and inspect the resulting block tree.

#### 6. Running Programs: The Reference Executor (10 min)

QProgram ships a pure-Python executor that interprets a program against a pluggable measurement model. It is the reference definition of the language's semantics, and it means a program can be run — and its results shaped, labeled, and plotted — with no hardware involved. Results come back as labeled arrays whose dimensions follow the program's own sweep structure.

> **Hands-on:** Run the two experiments from the previous chapter against a simulated response and plot the oscillation and the decay curve.

#### 7. Session 1 Wrap-up and Q&A (5 min)

Recap of the programming model, and a preview of Session 2.

### ☕ Break (30 min)

### Session 2 — Composition, Portability, and Execution Planning (90 min)

| # | Topic | Time |
|---|-------|------|
| 1 | Parallel Sweeps and Multi-Dimensional Experiments | 10 min |
| 2 | Measurements, Conditionals, and Feedback | 15 min |
| 3 | Fragments | 10 min |
| 4 | Portability: Rebinding Buses and the Waveform Library | 15 min |
| 5 | Serialization and Vendor Extensions | 15 min |
| 6 | Capabilities, Diagnostics, and the Execution Plan | 20 min |
| 7 | Wrap-up and Q&A | 5 min |

#### 1. Parallel Sweeps and Multi-Dimensional Experiments (10 min)

Sweeps can be composed to advance together rather than nest, which is how chevron patterns and two-tone spectroscopy are expressed. We look at how that composition is written and what it means for the shape of the results.

#### 2. Measurements, Conditionals, and Feedback (15 min)

A measurement returns a handle, and what that measurement yields — integrated IQ, a classified state, the raw trace — is requested at the call site. Handles can be compared, which allows a program to branch on its own measurement outcomes. This is the basis for feedback, and for expressing something like active reset portably rather than relying on a vendor-specific operation.

#### 3. Fragments (10 min)

Fragments are named, parameterized sub-programs — a gate, an echo sequence, a readout block — defined once and called many times. Their parameters are untyped placeholders, so the same fragment can be bound to a different bus or a different waveform at each call site. Calls remain visible in the program and can be lowered away when a flat program is wanted.

#### 4. Portability: Rebinding Buses and the Waveform Library (15 min)

Two transforms let a single experiment definition serve many qubits and many calibrations. Rebinding re-resolves a program's bus references through the schema, so an experiment written for one qubit moves to another — or to another naming convention, or another chip — without string surgery. Waveform resolution then fills in symbolic pulse names per bus from a calibration library, so a rebound program picks up the target qubit's calibration on its own.

> **Hands-on:** Write a characterization routine against symbolic pulse names, then move it to a different qubit and resolve it against different calibration sets.

#### 5. Serialization and Vendor Extensions (15 min)

Programs serialize to a plain-text format that round-trips exactly and is meant to be read, diffed, and edited by hand; calibration libraries have their own companion format. The same chapter covers how a hardware vendor contributes its own operations under its own namespace without any change to the core language, and how a serialized program records which extensions it depends on so that a missing one fails clearly instead of silently.

#### 6. Capabilities, Diagnostics, and the Execution Plan (20 min)

Because the language deliberately doesn't say where a block runs, something else has to. A platform declares what it supports per channel and per execution domain; validating a program against that declaration reports what the platform cannot do and produces a plan assigning each part of the program to real-time or host-side execution. `explain()` renders that plan as an annotated tree, and `optimize()` can restructure a program so that averaging which had been pushed host-side runs in real time again.

> **Hands-on:** Validate a program that a platform can only partly run in real time, read the plan, then optimize it and compare.

#### 7. Session 2 Wrap-up and Q&A (5 min)

Where QProgram sits in the wider software stack, pointers to documentation and the repository, and open discussion.

---

## Target Audience and Prerequisites

The tutorial is designed for quantum hardware engineers, experimentalists, calibration scientists, and software developers who need fine-grained control over the physical signals driving quantum processors. It is especially relevant for those building calibration routines, custom gates, or control infrastructure, as well as researchers moving from circuit-level programming to hardware-aware quantum computing.

**Attendees should have:**

- Working knowledge of Python programming.
- Basic understanding of quantum computing concepts (qubits, gates, measurement).
- Familiarity with the idea that quantum gates are implemented via microwave/flux pulses on physical hardware is helpful but not required, as the tutorial covers these concepts from first principles.

No prior experience with QProgram, pulse programming, or any specific quantum hardware platform is assumed.

**Content level:** Beginner 20% · Intermediate 50% · Advanced 30%

---

## Learning Goals

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

## Format and Hands-On Setup

The tutorial combines structured presentations with interactive coding exercises:

- **Slides** — conceptual introduction linking circuit-level gates to physical control signals.
- **Live coding** — instructor-led demonstrations using Jupyter notebooks, building pulse programs step by step.
- **Hands-on exercises** — two guided exercises per session, which attendees work through on their own laptops.
- **Local execution** — every example runs on QProgram's reference executor, so no hardware, GPU, or network access is needed to complete any part of the tutorial.

QProgram depends only on NumPy and xarray, with Matplotlib as an optional extra for waveform and result plotting. Pre-configured environments will be provided via a `requirements.txt` file and an optional Docker container, and installation instructions will be distributed one week before the tutorial.

---

## Presenters

### Vyron Vasileiadis

*Technical Lead, Qilimanjaro Quantum Tech* — [vyron@qilimanjaro.tech](mailto:vyron@qilimanjaro.tech)

Vyron leads the design and development of core quantum software infrastructure for Qilimanjaro's quantum processors. His work spans SDKs, simulators, runtimes, and execution pipelines, with a focus on connecting digital circuits, Hamiltonian-based models, pulse-level programming, and backend execution within coherent, usable abstractions. He is a key contributor to QProgram, QiliSDK, and Qilimanjaro's broader quantum computing stack.

Vyron holds an MSc in Quantum Computing and is currently pursuing a PhD in quantum control, with research focused on pulse optimization and gate design for high-fidelity operation of superconducting qubits. He has extensive experience in training, technical consulting, and public speaking, having delivered talks and technical sessions at conferences, hackathons, incubators, and innovation programs worldwide. He serves on the Advisory Board of DevNetwork.

### Flavie Le Bars

*Quantum Software Engineer, Qilimanjaro Quantum Tech* — [flavie.lebars@qilimanjaro.tech](mailto:flavie.lebars@qilimanjaro.tech)

Flavie holds an MEng in Aerospace Engineering from the University of Bristol. She works on the quantum hardware control stack, focusing on compilers that translate QProgram (pulse-level quantum programs) into low-level Q1ASM instructions for Qblox control hardware. She contributes to Qilimanjaro's hardware control library, and QPySequence, a Pythonic abstraction layer over Q1ASM assembly. Her interests span the full stack, from the physics of superconducting qubits to the software that controls them, and she enjoys solving problems that require bridging multiple disciplines.

---

## Repository Contents

Materials are published here ahead of the tutorial and remain available afterward.

| Path | Contents |
|------|----------|
| `README.md` | This page — tutorial overview, agenda, and presenter information. |
| *(coming soon)* | Jupyter notebooks for both sessions, with executable examples and solutions. |
| *(coming soon)* | Slides and environment setup instructions (`requirements.txt`, Docker). |

## Related Projects

- **[QProgram](https://github.com/qilimanjaro-tech/qprogram)** — the hardware-agnostic DSL for pulse-level quantum programming covered in this tutorial, including its reference software executor, capability and diagnostics layer, and text serialization format. *(The repository is currently private and will be open-sourced ahead of the tutorial.)*
- **Vendor extensions** — separate packages that add hardware-specific operations to the core DSL, such as Qblox control instruments and QDevil QDAC flux biasing. They demonstrate the extension pattern covered in Session 2.
- **[QiliSDK](https://github.com/qilimanjaro-tech/qilisdk)** — Qilimanjaro's open-source Python framework for designing and executing analog, digital, and hybrid quantum algorithms, unifying circuit-based and Hamiltonian-based workflows behind a single backend-agnostic API. It is the algorithm-level counterpart to QProgram's pulse level.

## Further Reading

1. P. Krantz, M. Kjaergaard, F. Yan, T. P. Orlando, S. Gustavsson, and W. D. Oliver, "A quantum engineer's guide to superconducting qubits," *Applied Physics Reviews*, vol. 6, no. 2, p. 021318, 2019.
2. M. A. Serrano, R. Perez-Castillo, and M. Piattini, "Quantum software engineering," Springer, 2022.
3. T. Proctor *et al.*, "Measuring the capabilities of quantum computers," *Nature Physics*, vol. 18, pp. 75–79, 2022.
4. N. Khaneja, T. Reiss, C. Kehlet, T. Schulte-Herbrüggen, and S. J. Glaser, "Optimal control of coupled spin dynamics: design of NMR pulse sequences by gradient ascent algorithms," *Journal of Magnetic Resonance*, vol. 172, no. 2, pp. 296–305, 2005.
5. J. M. Gambetta, F. Motzoi, S. T. Merkel, and F. K. Wilhelm, "Analytic control methods for high-fidelity unitary operations in a weakly nonlinear oscillator," *Physical Review A*, vol. 83, no. 1, p. 012308, 2011.

---

## Contact

Questions about the tutorial? Reach out to [vyron@qilimanjaro.tech](mailto:vyron@qilimanjaro.tech) or open an issue in this repository.
