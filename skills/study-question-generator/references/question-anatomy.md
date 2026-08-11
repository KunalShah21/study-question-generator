# Question Anatomy

Reference for writing and grading third-order questions. Examples are from
*Central Dogma ELS* (Brett Condon, PhD), the source deck this rubric was derived from.

## The three orders

Order is measured by **inference hops**: distinct facts the student must retrieve and
chain before an option can be eliminated.

### First order — 1 hop (retrieve)

> Which of the following is responsible for synthesizing rRNA?
> A. RNA Pol I  B. RNA Pol II  C. RNA Pol III  D. DNA Pol I  E. DNA Pol III

One lookup: "RNA Pol I → rRNA." Anyone who memorized the list answers it. Anyone who
didn't cannot. It measures recall, nothing else.

### Second order — 2 hops (apply one relationship)

> Researchers study an enzyme that adds acetyl groups to histone tails. This
> modification reduces the positive charge of the histone tail. What impact would this
> have on the interaction between DNA and the modified histone tail?
> A. Strengthens  B. Weakens  C. No impact

The stem *hands over* the causal fact (acetyl reduces positive charge). The student
supplies one more (DNA is negatively charged; opposite charges attract) and applies it.

### Third order — 3+ hops (chain to something unnamed)

> A patient with multiple contusions is treated at an accident scene with an
> unexpectedly low heart rate and marked lack of concern for her surroundings. Blood
> tests reveal no alcohol or illicit drugs. The patient becomes drowsy and her heart
> rate plummets. A roommate injects her with an Epipen containing epinephrine. The
> patient does not appear to respond. A lab tech determines the patient has a
> nucleotide disorder. Which of the following is most likely irregular?
> A. Thymine  B. Coenzyme-A  C. Uracil  D. cAMP  E. ATP

The chain:
1. Epinephrine was administered and produced **no response**.
2. Epinephrine acts through a G-protein-coupled receptor → **second messenger**.
3. That second messenger is **cAMP** (from the "signal transduction" bullet).
4. Therefore the broken nucleotide is cAMP.

Note what the stem never says: *cAMP*, *second messenger*, *signal transduction*,
*receptor*. The bridging mechanism is entirely the student's to supply. **That absence
is what makes it third order.**

## Three third-order patterns worth reusing

| Pattern | Source example | Shape |
|---|---|---|
| **Silent mechanism** | #5 (above) | Observable clinical failure → student names the pathway → identifies the broken molecule |
| **Subtraction** | #9: heat separates the strands, so which enzyme is now unnecessary? (helicase) | Remove a step from a process; ask what becomes redundant. Requires knowing each player's *purpose*, not its name |
| **Direction-of-effect** | #24: inclusion bodies of misfolded protein — which would *exacerbate* them? (inactive Hsp70, ATP deficiency, inhibited ubiquitin ligase — but *hyperactive* proteasome/Hsp60 would help) | Each option pairs a real player with a direction. Student must reason per option about which way the arrow points |

Subtraction and direction-of-effect are the most guess-resistant, because surface cues
say nothing about which direction is harmful.

## Distractor taxonomy

**The rule: every distractor must be a true fact from the source that is the correct
answer to a neighboring question.**

In #5 the options are Thymine, Coenzyme-A, Uracil, cAMP, ATP — the source's own
nucleotide-function list. Each is genuinely correct for a different function:

| Option | Legitimately correct for | Why wrong here |
|---|---|---|
| Thymine | DNA vs RNA distinction | not a signaling molecule |
| Coenzyme-A | enzymatic facilitation | wrong function |
| Uracil | RNA base | wrong function |
| **cAMP** | **signal transduction** | **correct** |
| ATP | energy provision | plausible trap: real and vital, but not the epinephrine messenger |

A student who half-knows the material is pulled toward ATP. That is a *productive*
wrong answer — it diagnoses a specific gap.

### Distractor sources, best to worst

1. **Adjacent function** — right category, wrong role (Coenzyme-A above). Best.
2. **Adjacent step** — correct for the step before/after (DNA Pol I vs III).
3. **Right answer to the inverted question** — what you'd pick if the stem said
   *increase* instead of *decrease*. Catches misread stems.
4. **Common misconception** — what students actually get wrong.
5. ❌ **Invented or absurd** — "Magnets." Eliminated instantly; wastes a slot.
6. ❌ **Self-refuting absolutes** — "no effect," "functionally interchangeable,"
   "X is entirely unrelated." Test-wise students discard these on sight.

## Option mechanics

Options must be **interchangeable in appearance** so their form carries no signal.

| Rule | Why |
|---|---|
| Same grammatical form throughout | A lone full sentence among noun phrases marks itself |
| Longest ≤ ~1.3× shortest | Length is the #1 giveaway; graders reward detail, students learn to pick it |
| No `because` / `since` / `due to` / `which leads to` in any option | Embedded reasoning appears only in the correct option. Rationale belongs in the answer key |
| One claim per option | Compound options ("X and Y, because Z") can't be cleanly wrong |
| No absolutes as filler | `never`, `no effect`, `entirely` read as wrong |
| Alphabetize or order logically where natural | Prevents position bias; correct answers must not cluster |
| Vary the correct position across the set | Roughly uniform across A–E |

### Length parity in practice

❌ Fails parity — the answer announces itself:

> A. No effect — glycine and proline are functionally interchangeable
> B. Beta-sheet formation is enhanced, since proline stabilizes strand pairing
> C. Beta-strand formation is disrupted, because proline's rigid ring prevents the
>    extended, planar backbone conformation required within a strand
> D. The mutation increases inter-strand hydrogen bonding

C is 2.5× the shortest, the only one with a mechanism, and the only one whose reasoning
is spelled out. A blind test-taker picks it without knowing any biology.

✅ Holds parity — form is uninformative:

> A. Alpha helix elongation
> B. Beta strand disruption
> C. Disulfide bond formation
> D. Increased hydrogen bonding

## Stem mechanics

1. **Open with a vignette.** A patient presentation or lab-experiment setup. The source
   uses this for nearly every non-recall question.
2. **Report observations, not mechanisms.** "The patient does not appear to respond" —
   not "because epinephrine signals through cAMP."
3. **Never name the answer or its category.** If the answer is cAMP, the stem cannot say
   *cAMP*, *second messenger*, or *cyclic nucleotide*.
4. **Include realistic noise.** #5's contusions and lacerations are irrelevant;
   filtering signal from noise is part of the skill being tested.
5. **Ask one question.** "Which is most likely irregular?" — never "predict X and
   explain why," which forces a bloated correct option.
6. **Prefer "most likely" / "most directly"** when several options are defensible but
   one is best.
7. **No meta-language.** Never write "this cross-topic question" or "per the slides."
   Students see none of that on a real exam.

## Self-check before accepting a question

- [ ] Fact chain written out; **≥3 hops**
- [ ] Every fact traceable to the source (no outside knowledge required)
- [ ] Answer term and its category absent from the stem
- [ ] Cover the options: is the stem still answerable? (If yes, the options leak.)
- [ ] Every distractor true-but-wrong-step, none absurd, none absolute
- [ ] Length parity holds; no `because` in any option
- [ ] Exactly one defensible answer
- [ ] A student who knows the material but is bad at test-taking gets it **right**;
      a student who knows nothing but is good at test-taking gets it **wrong**

That last line is the whole point.
