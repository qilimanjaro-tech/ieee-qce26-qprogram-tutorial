# Programming a Superconducting Qubit

Material for the IEEE Quantum Week 2026 (QCE 2026) hands-on tutorial **Programming a
Superconducting Qubit: Pulse-Level Control and Calibration with QProgram**.

The tutorial follows the order a real qubit gets brought up: find the readout resonator, find the
qubit, calibrate a pi pulse, measure coherence, add feedback, then port the whole calibration to a
different rack. Each experiment introduces the QProgram feature it needs, so the library arrives one
problem at a time instead of as a feature tour.

## Where everything is

| Path | What it is |
|------|------------|
| [`setup/README.md`](setup/README.md) | Install instructions (pip, uv, or Google Colab). Start here. |
| [`notebooks/`](notebooks/) | The seven tutorial notebooks (`00_setup` to `06_extending_and_shipping`), attendee versions with the exercises left blank. |
| [`notebooks/solutions/`](notebooks/solutions/) | The same notebooks with the exercises solved and the outputs embedded. |
| [`slides/`](slides/) | The Marp deck (`qprogram_tutorial.md`) and its diagrams. See [`slides/README.md`](slides/README.md). |
| [`sources/`](sources/) | The percent-format Python sources the notebooks are built from. Edit these, never the `.ipynb` files. |
| [`tools/`](tools/) | The notebook builder and the house-style checker. |

## Schedule

| | Part | Experiments | Duration |
|---|------|-------------|----------|
| | Setup ([`00_setup`](notebooks/00_setup.ipynb), run it before the session) | readout pulse, one resonator scan | at home |
| 1 | The program is data ([`01_pulse_programs`](notebooks/01_pulse_programs.ipynb)) | readout pulse and acquisition | 35 min |
| 2 | Sweeps, averaging, and what comes back ([`02_sweeps_and_results`](notebooks/02_sweeps_and_results.ipynb)) | resonator spectroscopy, punchout | 35 min |
| 3 | Finding and driving the qubit ([`03_finding_the_qubit`](notebooks/03_finding_the_qubit.ipynb)) | qubit spectroscopy, Rabi, flux arc | 40 min |
| | **Break** | | 15 min |
| 4 | Coherence, single shots, and feedback ([`04_coherence_and_feedback`](notebooks/04_coherence_and_feedback.ipynb)) | T1, Ramsey, Hahn echo, single-shot readout, active reset | 40 min |
| 5 | One program, many machines ([`05_one_program_many_machines`](notebooks/05_one_program_many_machines.ipynb)) | porting the flux arc to another rack | 30 min |
| 6 | Extending the language and shipping the work ([`06_extending_and_shipping`](notebooks/06_extending_and_shipping.ipynb)) | custom waveform, custom sweep source, vendor operation, full bring-up capstone | 25 min |

Total: 3 hours 40 minutes with the break. For a three-hour slot, cut Part 6's capstone and the
second exercise in Parts 2 and 5. Those three are the pieces designed to come out, and nothing
later depends on them.

## Everything runs on your laptop

No hardware, no cloud account, no vendor package. QProgram ships `ReferencePlatform`, a pure-Python
interpreter reachable through the `qp.simulate(program, model=...)` one-liner, and every notebook
runs end to end on it. Each experiment supplies a small measurement model that plays the part of the
fridge: it is handed the loop variables currently bound and returns one sample per shot. The limits
are worth stating plainly. The simulator produces plausible numbers, not physics from first
principles, and it models no pulse shapes and no timing at all. It is there so that the *program* you
write and the *analysis* you run on the results are the real thing, which is where the engineering
work in a control stack actually lives.

## Maintaining this repo

The notebooks are generated. `sources/NN_name.py` is the file you edit; the two `.ipynb` flavours
fall out of it.

```bash
python tools/build_notebooks.py --check    # validate the sources, write nothing
python tools/build_notebooks.py            # write notebooks/ and notebooks/solutions/
python tools/build_notebooks.py --execute  # ... then run the solutions and embed their outputs
python tools/check_style.py                # house style: no em or en dashes, no filler vocabulary
```

`--execute` runs each solution notebook with nbconvert and then copies the outputs onto the attendee
notebook, matching cells by source text. Exercise stubs have different source, so they stay empty
while every shared cell keeps the output the reader will see.

Each source file is also a runnable script, and that is how the material is verified:

```bash
MPLBACKEND=Agg python sources/03_finding_the_qubit.py
```

Markdown lives in raw triple-quoted strings and exercise stubs are comments, so the script executes
exactly the code the notebook does. A source file that exits non-zero is broken material. Run
`check_style.py` and the script before committing.

QProgram source: <https://github.com/qilimanjaro-tech/qprogram> · Docs:
<https://qilimanjaro-tech.github.io/qprogram>
