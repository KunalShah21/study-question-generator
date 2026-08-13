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

### Draw all options from one closed category

Parity of *length* is not enough. If the options name things from different categories, a
blind reader sorts them by category and the odd one out is visible. Pull every option from
a single enumerable set in the source — the three polymerases, the four ribosome sites, the
named chaperones, the parts of a mature transcript — in identical grammatical form:

> A. Small nuclear transcripts
> B. Transfer transcripts
> C. Interfering transcripts
> D. Ribosomal transcripts

Now no option is distinguishable by form, and picking requires knowing which polymerase was
hit. This is the strongest single defense against blind guessing, and it comes free: a
closed source category *is* a ready-made set of true-but-wrong-step distractors.

### Default to opaque labels for options

**Enumerated labels are the default. Prose options need a reason.**

The best-performing option sets in testing were **enumerated labels with no descriptive
content at all** — `TFIID / TFIIB / TFIIE / TFIIF / TFIIH`, or `Asn / Gln / Ser / Thr / Tyr`.
Both scored a 1.00 length ratio and gave the blind judge literally nothing to work with: you
cannot echo a stem, embed reasoning, or leak generality in a five-character abbreviation.

So **look for an enumerable set in the source before choosing the concept**, not after
drafting the options — factor families, numbered enzymes, three-letter residue codes, named
sites, named repair pathways. When a source offers one, the whole class of surface-cue defects
disappears at once and the question rests entirely on the fact chain.

This is a cost rule as much as a quality rule. Every surface-cue defect an opaque label set
makes impossible is a gate-1 failure that never happens, and a rewrite round never spent — and
the two questions in this build that hit the 3-round cap were both rescued by switching to
enumerable sets, scoring 1.00 immediately (see `judge-protocol.md`, "Handling failures"). It is
cheaper to pick a concept with an enumerable option set than to fix a prose set the blind judge
cued on.

Reach for prose options only when no enumerable set fits the concept, and expect them to take
more rounds to make safe.

`check_mechanics.py` skips length checks entirely on these sets and says so, because a ratio
over 3- and 4-character acronyms is noise: `CSB` beside `TFIIH` computes to 1.67 and carries
no signal a reader could act on. Never pad or truncate a source-verbatim name to satisfy the
checker — that breaks grounding to fix nothing.

### Name options in the source's own words

An option is only grounded if the source uses that word. A set drawn from the polymerase
table looked homogeneous and passed every mechanical check, but the source says *mi/siRNA*
and the option said *Interfering transcripts* — the sourced judge returned
`source_sufficient: false`, noting that mapping one to the other "requires knowing that
si/miRNA are conventionally called 'interfering' RNA, a label the source itself never uses."

Homogeneity is about *form*; grounding is about *vocabulary*. A closed category satisfies
both only when you name its members the way the source names them.

`check_mechanics.py --source` now catches this class for free: it flags any distinctive word in
an option that the source never uses, which is exactly the `Interfering` above. Run it with
`--source` and the expensive version of this failure — discovering it from gate 2's
`source_sufficient: false` — mostly stops happening. It checks options only, because a stem is
*supposed* to describe a vignette in fresh words.

**The same trap sits in the stem.** Lecture notes are full of bare abbreviations. A stem
describing "both enzyme families that add and remove acetyl groups on histone tails" reads
as a careful paraphrase of `HATs, HDACs` — but the source never expands those letters, so
recognizing the match requires knowing what they stand for. The judge failed it:
*"the source only lists the bare abbreviations alongside 'chromatin remodeling'."* Describing
them as "the enzyme families credited with chromatin remodeling" uses the source's own phrase
and grounds cleanly.

Check both directions before running the judge: every option word, and every stem
paraphrase, must be traceable to text the source actually contains.

**Grounding starts at concept selection, not wording.** A clinical vignette only grounds if
the source states the *identifying features* that let a reader map the presentation back to
it. A Huntington vignette (involuntary movements, affected parent, trinucleotide repeat)
read as clean third-order, but the source never expands "HD" and never lists its symptoms —
so the vignette→disease link needed outside knowledge and the judge returned
`source_sufficient: false`. The fix was not a reword but a different disease: Bloom's, whose
features the source *does* spell out verbatim ("Red facial butterfly rash... high risk
cancer, short stature"). Before building a vignette, confirm the source itself contains the
findings you plan to describe — if it only names the entity, the question is ungrounded no
matter how the options are worded.

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
8. **Never rule out the distractors in the stem.** This one is counter-intuitive and cost
   a full test round. Writing *"the promoter and sequence are identical, and transcription
   rates are equal"* feels like precision — it removes ambiguity so the answer is
   unarguable. But it hands the reader a process-of-elimination path that needs no domain
   knowledge: cross off promoter, cross off rate, and only one option is left standing.
   A blind judge named exactly this cue: *"stem explicitly rules out promoter/sequence/rate
   differences, leaving only the option not yet excluded."*

   Give only the **positive findings** the student must interpret. State a normal finding
   only when the *mechanism* depends on it — "unfolded clients still bind its hydrophobic
   surfaces" localizes the lesion to the ATP step and is load-bearing. Compare:

   | ❌ Exclusionary | ✅ Positive only |
   |---|---|
   | "Ribosomes, mRNA, and elongation machinery all function normally" | "The enzyme still consumes ATP and charges its tRNA at a normal rate" |
   | "Its sequence and promoter are identical and it is transcribed at equal rates" | "Sequencing confirms the gene is identical in both tissues" |

   Rule of thumb: if striking a "normal/identical/unaffected" clause does not change the
   correct answer, it was scaffolding for the guesser. Strike it.

9. **No semantic echo between stem and answer.** Sharing no *words* is not enough. A blind
   judge found the key three times running through pure paraphrase:

   | Stem said | Correct option said | Judge's cue |
   |---|---|---|
   | "barrel-shaped" | "sealed inside the **cavity**" | *"the only option that explicitly names a cavity"* |
   | "accepts a second, chemically similar amino acid" | "holding the **wrong residues**" | *"directly restates that mismatch"* |
   | enzymes that "**add and remove**" marks | "**Adjusting** DNA access" | *"the only bidirectional capability; A/B/C name narrow one-off actions"* |

   None of these share a word long enough for a mechanical checker to flag. Read the stem
   and ask: *which option sounds most like a restatement of the vignette?* If that is the
   key, rewrite. The fix is usually to name the option in the **source's** vocabulary rather
   than the stem's — "sealed inside the cap" is the source's word and echoes nothing.

   **A closed category can carry the echo in its own names.** The strongest defense — draw every
   option from one enumerable source set — backfires when the set's members are named by
   *antonym pairs* or otherwise describe themselves. A stem saying a compound "does nothing to
   purified DNA but alters DNA inside intact cells" was keyed to `Indirect acting agents`, sitting
   beside `Direct acting agents`. The blind judge hit it with `used_domain_knowledge: false`:
   *"the stem lexically mirrors 'Indirect' and is the direct antonym of option B's word 'Direct',
   ruling B out and pointing to C by elimination."* Homogeneity of form did not help, because the
   *semantics of the labels themselves* encoded the answer. When a source category names its
   members `direct`/`indirect`, `more accurate`/`less accurate`, `activating`/`inhibiting`, any
   stem describing that axis leaks. Either key the question to a member outside the pair, or pick
   a different category.

   Watch also for the *abstraction* echo in that third row: when three distractors are
   specific one-off acts and the answer is a general capability, the answer's grammatical
   altitude gives it away even with perfect length parity. Keep every option at the same
   level of generality.

**The two gates pull against each other.** Exclusionary stems help gate 2 (answerability)
and destroy gate 1 (blind guessing). Resolve it in the *options*, never the stem: a
homogeneous closed-category set makes the answer unambiguous without narrating any
eliminations.

**Gate 1 has a measurement limit worth knowing.** A frontier model cannot fully suppress
what it knows, so it sometimes answers from domain knowledge and back-fills a plausible
"cue." Treat a named cue as real only if a reader with zero subject knowledge could see it.
*"The 5' cap and poly-A tail are added separately from splicing"* is biology, not a surface
cue, and rewriting to satisfy it degrades the question. The blind prompt should tell the
judge to report `used_domain_knowledge` explicitly for exactly this reason.

## Self-check before accepting a question

- [ ] Fact chain written out; **≥3 hops**
- [ ] Every fact traceable to the source (no outside knowledge required)
- [ ] Answer term and its category absent from the stem
- [ ] Cover the options: could a reader who knows the source still produce the answer?
      (If no, the option list is carrying the question.)
- [ ] Every distractor true-but-wrong-step, none absurd, none absolute
- [ ] All options from one closed source category, identical grammatical form
- [ ] Options are enumerated labels, or there's a reason they can't be
- [ ] Each option named in the **source's own vocabulary**, not a synonym for it
- [ ] Every option at the same level of generality — not three specific acts plus one
      general capability
- [ ] No option **paraphrases or conceptually mirrors** the stem's descriptive language
- [ ] The option *names* themselves don't encode the answer — no antonym pair
      (`direct`/`indirect`) whose axis the stem describes
- [ ] Stem rules nothing out — no "normal", "identical", "unaffected" scaffolding that a
      guesser could cross options off with
- [ ] Length parity holds; no `because` in any option
- [ ] Exactly one defensible answer
- [ ] A student who knows the material but is bad at test-taking gets it **right**;
      a student who knows nothing but is good at test-taking gets it **wrong**

That last line is the whole point.
