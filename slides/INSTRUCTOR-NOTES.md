# Instructor notes

What to say, and where. This file exists because the deck is deliberately thin. A slide carries one claim and the presenter carries the rest, so anything the room would otherwise read instead of listening to was taken off the slides and written down here.

Two kinds of entry, both in deck order.

**Spoken, no slide.** Five slides were cut because they land better said than read. Their notes below are the whole of them, and each entry says which gap in the deck it fills.

**Behind the figure.** Ten diagrams used to carry prose panels, explanatory footers, and caveats about their own drawing. That text is gone from the pictures and is here instead, attached to the slide whose figure it belonged to. The picture now shows the mechanism and you say what it means.

Slide numbers are the current deck, eighty-one slides. `python tools/slide_fit.py --all` prints the numbered list if the deck moves under you.

---

## The chip and the rack

### Slide 12 · The transmon · behind the figure

The picture is two panels and a comparison band. The left panel is the circuit, a capacitor across a Josephson junction, with `E_C` under the capacitor and `E_J` under the junction. The right panel is the cosine well with four levels drawn at their turning points. The band underneath is two mini ladders side by side, labelled `harmonic` and `transmon`.

The band is the argument and it carries no words, so it needs you. A harmonic oscillator has evenly spaced levels, so one drive frequency hits every transition at once. The junction bends the walls of the well, so the rungs crowd as you climb, and that crowding is the only reason there is a qubit here rather than a resonator.

Two things to say about the right panel. The level spacings are drawn exaggerated to show the trend, because at true scale the crowding is invisible. And the ladder does not stop at the four levels drawn, it goes on up, closer every time.

The gap between $f_{01}$ and $f_{12}$ is small, and that small gap is the whole margin a single-qubit gate has to work in. Hold that thought for the Leakage and DRAG slides.

### Spoken, no slide · The design ratio

Fills the gap between slide 12, The transmon, and slide 13, Tuning with flux. The figure you are still standing in front of says `transmon regime, E_J/E_C >~ 50`, so this is where that number comes from.

- A large $E_J/E_C$ puts the phase deep in the cosine well, and stray charge then stops shifting the levels.
- Charge dispersion falls as $e^{-\sqrt{8E_J/E_C}}$ and the anharmonicity falls only as $-E_C$, so the immunity is bought exponentially and paid for linearly.
- Above roughly 50 the charge sensitivity has gone, and nobody quotes a ratio of 10 any more.
- The ratio therefore trades charge noise against gate speed. A big ratio buys immunity to charge noise, and the cost is the anharmonicity, which shrinks with it.
- Land it on the number the previous slides already gave. The anharmonicity on this chip is $-300$ MHz, and a gate has to fit inside that.

### Spoken, no slide · Why 5 GHz

Follows The design ratio in the same gap. Nobody asks this question out loud and everybody wonders it.

- The thermal scale $hf/k_B$ at $f_{01}$ is 233 mK, and a 10 mK stage sits far below it, so the qubit starts in the ground state rather than in a thermal mixture.
- The band is also where the parts can be bought. Coax, circulators, and microwave generators are all commodity at 4 to 8 GHz because telecoms and radar got there first.
- Real devices sit warmer than their fridge, at 40 to 60 mK, which leaves about one percent excited before you have done anything.
- Forward pointer worth making here, because it pays off in the second session. Part 3 resets that population rather than waiting for it, and the active-reset section takes 30 percent hot down to 3 in one extra measurement.

### Slide 14 · The control rack · behind the figure

The picture is three bands, the rack at 300 K, the fridge from 300 K to 10 mK, and the chip at 10 mK, with four vertical lines crossing them. Read it left to right, flux, drive, readout, return.

The claim the footer used to make, and the one worth saying, is that every operation in this tutorial is one of two things. Put a voltage on a line going down, or record what comes back on the line coming up. There is nothing else in the vocabulary.

Point at the coupling line between the transmon and the resonator without naming a number. It used to be labelled $2\chi$ and the label has moved to The dispersive shift, where the deck has actually defined $\chi$. Saying it here is a hundred slides early.

Two details in the instrument boxes are worth a sentence each. The slow DC source settles in milliseconds, and that single fact makes the flux line a different animal from the AWG for the whole of Part 3. And the AWG runs on a 4 ns instruction grid, so a `wait` of 3 ns is a question for the platform rather than for the language.

### Spoken, no slide · Attenuation

Fills the gap between slide 14, The control rack, and slide 15, The fridge. It is the argument the fridge picture assumes.

- A 50 ohm resistor at room temperature radiates into every mode it touches, and at the drive frequency that is 1300 photons per mode. The qubit sits on one of them.
- So an attenuator on the way down is not there to protect the chip from your signal. Every attenuator does two jobs, it cuts the signal, and it re-thermalizes the noise it passes on to its own stage temperature.
- That is why the attenuation is spread down the fridge rather than done once in the rack. An attenuator at 300 K would hand the line 300 K noise on the other side of itself.
- The next slide shows the arithmetic, 20 dB at the 4 K plate, 10 dB at the still, and 20 dB at the mixing chamber.
- Microwatts at the generator arrive as femtowatts at the chip. The power figures are the ones the deck carries, so check them against your own line budget before you say them out loud.

### Slide 15 · The fridge · behind the figure

The picture is six stages with their temperatures, the input line down the left and the output line up the right. Three prose panels used to sit beside it and they are now yours.

**Down the input line.** Room-temperature Johnson noise would reach the chip as thermal photons if nothing were in the way. Every attenuator cuts the signal and re-thermalizes the noise it passes on to its own stage temperature, and the total on the way down is about 60 dB.

**Up the output line.** What comes back is a few tens of photons and it still has to reach an ADC at room temperature. So amplify at the coldest point first, where the amplifier adds the least noise of its own, and the order of the boxes on the right is the whole point. The isolator is there to keep the amplifier's own noise from travelling back down to the qubit.

**Why 10 mK.** At 4.85 GHz the thermal scale $hf/k_B$ is 233 mK, so a 10 mK stage keeps the thermal population of the qubit down near a percent. If you have already spoken the Why 5 GHz notes above, this is the callback rather than the reveal.

The 50 mK and 100 mK bands are drawn empty on purpose. The lines just pass through, and an empty band says that better than a label would.

### Slide 19 · Axis and angle · behind the figure

Two panels, and each heading is a claim. Left, phase picks the axis. Right, area is the angle.

On the left, the two labelled axes read `phase = 0` and `phase = 90 deg`. The sentence that used to sit under them is the one to say. The pulse is the same either way, and only the carrier phase differs, so `Y` is `X` with the phase advanced 90 degrees and it costs no extra calibration.

On the right, the big burst is labelled `envelope` on its outline and `carrier` on the wiggle inside it. What matters is the integral of the envelope and not the height of it, the formula the previous slide displayed. Then the three shapes below, `pi`, `pi/2`, `pi/4`, are the same shape at half and quarter height. Same duration, same envelope, half the area, half the angle.

Close the pair by naming both knobs together. One envelope, two knobs. The area sets how far the state turns and the carrier phase sets what it turns about.

### Slide 26 · The readout chain · behind the figure

Four columns, and the slide used to carry a numbered list under them. The list is now yours, one item per column.

1. **The coupled pair.** The detuning is $\Delta = f_{01} - f_r = -2.35$ GHz, far larger than the coupling $g$, and that ratio makes this dispersive rather than an energy exchange. The shift goes as $\chi \approx g^2/\Delta$, so the resonator moves to $f_r - \chi$ or $f_r + \chi$ and the qubit picks which. That shift is the signal, and everything downstream is an attempt to measure it without disturbing it.
2. **Two dips, one axis.** The resonator fills at rate $\kappa$, and the return picks up a state-dependent phase only once it has. The two arrows are the two numbers that matter, $2\chi = 3.6$ MHz between the dips and $\kappa = 1.5$ MHz across one of them. Their ratio, $2\chi/\kappa = 2.4$ on this chip, is the figure of merit for the whole readout.
3. **After the chip.** Read the boxes downward and name what each one is for. The returning tone carries the state, the amplifier chain is ordered cold first and then warm, the IF mixer brings it down to an intermediate frequency, the ADC samples the waveform, and demodulation multiplies by the weights and sums over the window. One complex number per shot comes out of the bottom.
4. **The IQ plane.** One dot per shot. `d` is the gap between the two cloud centres and `sigma` is the spread of one cloud, and every choice you made upstream shows up here as $d/\sigma$ and nowhere else.

The weights deserve their own sentence, because the next slide is about them. They pick the part of the record that carries the state, and everything outside that window is noise you are choosing to integrate.

### Spoken, no slide · Readout fidelity

Fills the gap between slide 27, Integration weights, and slide 28, Coherence times. Go back a slide to the IQ panel of the readout chain figure while you say it, because the picture labels $d$ and $\sigma$ and the threshold already.

- The resonator has to fill before the return says anything, at rate $\kappa$, so the first part of every acquisition window carries no information.
- Integrating longer beats down the amplifier noise, and $T_1$ caps the window from the other side. Integrate past the qubit's lifetime and you are averaging in shots that have already decayed.
- Cloud separation $d$ grows with photon number and with $2\chi/\kappa$.
- Information per photon peaks near $2\chi = \kappa$, and this chip sits at 2.4, so it is close to the best it can do without a redesign.
- The error is an erfc of $d$ against the cloud width $\sigma$, $\varepsilon = \tfrac{1}{2}\,\mathrm{erfc}\!\left(d / 2\sqrt{2}\sigma\right)$. Four sigma of separation gives about 2 percent and six sigma about 0.1 percent, the difference between a usable qubit and a published one.
- Separation and spread are the two things you tune. Everything else on the readout chain is in service of one or the other.

### Spoken, no slide · How hard to read out

Follows Readout fidelity in the same gap, and it is the answer to the obvious question the previous notes raise.

- If more photons separate the two clouds, the temptation is to turn the tone up until the readout is perfect.
- The dispersive approximation has a limit and the limit is a photon number, $n_{\text{crit}} = \Delta^2/4g^2$, about 37 photons on this chip.
- Below it the resonator reports the qubit. Above it the resonator sits on bare $f_r$ and reports nothing at all, so the failure is not a gradual loss of fidelity, it is the signal going away.
- Worth saying plainly, because it catches people. Turning the readout power up is the first thing anybody tries and there is a cliff a factor of a few above where you want to be.

---

## Why a language of its own

### Slide 39 · The architecture · behind the figure

One spine from the experiment script down to the instruments, with vendor extensions plugging into the core from the left and artifacts falling out to the right.

The claim to say over it is that the same program object runs the whole length of the spine. Your script builds the tree, the core owns it, validation reads it, and a platform is the only thing that ever turns it into voltages.

Two labels were taken off the picture because Part 3 has not happened yet. The capability validation box produces a diagnostics list and an execution plan split into a real-time half and a host half, and its three mechanisms are tokens, limits, and predicates. Say the names if the room is ahead of you, and skip them otherwise, because slides 71 to 74 do it properly.

The vendor extension panel used to list what a package registers, a namespace, its operations and blocks, and its capability tokens. `program.qblox.*` on the panel is the whole idea in one line.

---

## Part 1 · The program is data

### Slide 42 · One signal path · behind the figure

Instrument ports on the left, bus names in the middle, chip lines on the right. Two qubits, five buses, three instruments, and exactly one bus name per signal path.

A reference band used to sit under the map, giving each kind of bus its properties and its verbs. That band is notebook 1.4 and the operations table on the next slide, so it does not need to be on screen, but the three facts in it are worth saying while the map is up.

- A **drive** bus is two DACs into an IQ line and no ADC, so `channel` is `IQ` and `acquires` is `False`. It takes `set_frequency`, `set_phase`, `reset_phase`, `set_gain`, `play`, `wait`, and `sync`.
- A **readout** bus is the same on the way out with an ADC on the way back, so `acquires` is `True`, and it is the only kind of bus a `measure` can name.
- A **flux** bus is one filtered wire with no carrier and no ADC, so `channel` is `single` and it takes single-channel waveforms only. It moves $f_{01}$, and it is often on a separate box, the entire subject of the second session.

### Slide 44 · One clock per bus · behind the figure

The same two-line program drawn twice, without a barrier and with one.

The top panel is the bug. Each bus advances only when you write to it, so both cursors are still at zero when the measurement starts, and the shaded region is the 44 ns of acquisition that runs while the qubit is still being flipped.

The bottom panel is the fix, and the sentence worth saying is how little it took. The barrier holds every named bus until the furthest ahead has finished, so both cursors now read 44 ns and the tone starts after the pulse. Nothing else in the program had to change.

Two caveats that used to be printed on the figure. The durations are drawn to be readable rather than proportional, 40 ns against 2000 ns. And the reference simulator models no timing at all, so the picture shows what a real platform does with the barrier and not what `qp.simulate` does. Worth flagging before anybody tries to see it in the notebook.

---

## Part 2 · Variables, sweeps, and results

### Slide 53 · Anatomy of a program · behind the figure

The Rabi program of Exercise 2.1 as a tree, with the class behind each line in the right margin and the two arrays it returns in the band at the bottom. Three annotations mark what each block contributes to the shape.

Four panels used to explain those annotations and they are now four sentences.

- **Average, no new dimension.** Two hundred shots at every point. The integrated point and the raw trace come back as means over the shots, and the classified state becomes a population. The shot count appears nowhere in the shape.
- **Sweep, one dimension each.** Forty-one iterations, so the result gains a dimension named after the variable id you declared, `amp`. Nest another sweep and it goes two dimensional, outermost first.
- **Measure, one record each.** The handle `m0` is how you fetch it afterwards, and the fields the call requested decide which arrays exist at all.
- **Operations are leaves.** `amp` inside the `IQDrag` is an expression rather than a number, and the loop binds its value before each iteration.

---

## Part 3 · Fragments, feedback, and the machine

### Slide 74 · Two domains · behind the figure

The same flux sweep planned twice, as written on the left and after `qp.optimize` on the right, with the rack's three buses along the top.

The left panel is the problem. The flux bus has no real-time half, so the bias sweep runs host side, and the averaging that encloses it gets dragged along with it. The `forced-host` warning on the top row is telling you exactly that, and the cost is the round trip paid two hundred times per bias point rather than once.

The right panel is the swap. The sweep is the outer block now, the `set_offset` has been hoisted to sit between the two, and the averaging is back in real time with no warning left.

The trap that used to be printed in the corner has its own slide two along, so point forward rather than spending it here. A bare `program.sync()` broadcasts to every bus, lands host side, and blocks this rewrite with no error message anywhere.
