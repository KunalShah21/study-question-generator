# Judge Protocol

Validation harness for a generated question set. Three gates, each a **separate
subagent on a different model than the one that wrote the questions**.

A model grading its own questions rates them well — it reconstructs the reasoning it
just used and mistakes that fluency for question quality. Cross-model judging is the
point of this harness, not an optimization.

## Model resolution

| Generator | Judge |
|---|---|
| Opus 5 | Sonnet 5 (`model: sonnet`) |
| Sonnet 5 | Opus 5 (`model: opus`) |
| Haiku | Sonnet 5 (`model: sonnet`) |
| anything else | Sonnet 5, unless that is the generator |

Pass the choice explicitly via the Agent tool's `model` parameter. Never let the judge
default to inheriting the session model — that silently collapses to same-model judging.

Do not use Haiku as judge for gate 2: it may fail a hard question for lack of capability,
which reads as a false question defect.

## Judges load nothing

Every gate prompt below is complete on its own — you have to paste it anyway to interpolate
the questions and the source. So end each judge prompt with:

> Do not invoke the study-question-generator skill and do not read any of its files. This
> prompt contains everything you need. Return only the JSON.

Without that line a judge is liable to load `SKILL.md` and `question-anatomy.md` — roughly
5,600 tokens of *question-generation* rules, on every spawn, for an agent whose only job is to
answer or audit. This skill's `description` triggers on the phrase "exam questions," which is
exactly what a judge prompt is full of. Worse, a judge that has read the generation rules is
no longer a naive test-taker: gate 1's whole premise is a reader who knows nothing about how
the question was built.

## Gate 1 — Blind-cue gate (runs first, non-negotiable)

Detects the dominant failure: a question answerable from surface form alone.

The judge gets stems and options, **no source material, no answer key**, and is
forbidden from using domain reasoning. If it still lands on the keyed answer *and* can
name the cue, the question is broken.

**Separate agent, no source access.** An agent that has read the source cannot
credibly perform this pass.

```
You are taking a multiple-choice exam. You have NO access to any source material,
textbook, or notes, and you must NOT use subject-matter knowledge to reason about the
content.

Answer using ONLY test-taking heuristics based on the SURFACE FORM of the text:
option length, grammatical parallelism, how much detail an option gives, whether an
option contains absolutes (never, no effect, entirely), whether an option embeds its
own justification, whether an option repeats or paraphrases wording from the stem,
whether the stem rules out other options, and which option "looks like" what an exam
writer would mark correct.

If you find yourself reasoning about what is true in the subject matter, STOP — that
is domain knowledge and it is forbidden here. In that case record a random guess with
cue_used "none" and confidence "none". A cue must be something a reader with zero
subject knowledge could see. Do not back-fill a surface-sounding cue for an answer you
actually derived from knowledge.

For each question: state your guess and name the specific surface cue that led you
there, or "none" if you were genuinely guessing at random.

{questions with options, no answers}

Return one JSON array and no prose:
[{"question_id": 1, "blind_guess": "C", "cue_used": "longest option; only one with a
mechanism", "confidence": "high|medium|low|none", "used_domain_knowledge": false}]
```

**Read the cues, not just the score.** A frontier model cannot fully suppress what it
knows; it will sometimes answer from domain knowledge and back-fill a plausible-sounding
cue. *"The 5' cap and poly-A tail are added separately from splicing"* is biology, not a
surface cue — rewriting to defeat it makes the question worse. Discount any cue a reader
with zero subject knowledge could not have seen, and count that question as a pass.

**A failure needs both conditions: the guess matches the key *and* a real cue is named.**
Neither alone is a defect. A named cue on a *wrong* guess is a pass — the judge described a
surface feature that did not in fact lead anywhere. This is not a corner case: one real round
of this harness named cues on 8 of 10 questions ("longest option", "only one containing a
digit", "only two-word option") while **only one** of those guesses matched the key. Rewriting
the other seven would have burned seven rounds and made the questions worse. Score the pairing,
not the cue list.

**Scoring.** With *k* options, random guessing yields ≈1/*k*.

| Result | Verdict |
|---|---|
| Guess ≠ key | PASS |
| Guess = key, `confidence: none` | PASS (coincidence) |
| Guess = key **and** a real cue named | **FAIL — rewrite** |
| Set-wide hit rate ≫ 1/*k* | **FAIL the set** — systemic tell, likely length parity or position clustering |

Also fail the set if correct answers cluster in one position, even when individual
questions pass. On rewrite rounds this set-wide check is carried by
`scripts/check_mechanics.py`, which computes position clustering for free — see
"Scoping the rewrite loop" below.

## Gate 2 — Answerability gate

The user's core requirement: a different model must answer **accurately and completely
using only the source material**.

Fresh agent, **with** the source, **without** the answer key. Requiring a quoted source
passage is what separates "the question is broken" from "the judge slipped" — an
unsupported answer means the question isn't grounded.

```
You are answering exam questions using ONLY the source material provided. Do not use
outside knowledge. If the source does not support an answer, say so explicitly.

SOURCE MATERIAL:
{extracted text}

QUESTIONS:
{questions with options, no answers}

For each question:
1. Choose the single best answer.
2. Reconstruct the reasoning as an explicit numbered chain of facts, each traceable
   to the source.
3. Quote the exact source passage(s) supporting each link.
4. State whether any OTHER option is also defensible from the source.
5. State whether the source alone is sufficient, or outside knowledge was needed.

Return one JSON array and no prose:
[{"question_id": 1, "answer": "D", "chain": ["fact 1", "fact 2", "fact 3"],
  "source_quotes": ["..."], "other_defensible": ["B"], "source_sufficient": true,
  "unanswerable_reason": ""}]
```

**Scoring** against the key:

| Result | Meaning | Action |
|---|---|---|
| Matches key, chain sound, quotes real | Question works | PASS |
| Judge picks another option, defensibly | Two right answers | FAIL — tighten stem or replace the option |
| `source_sufficient: false` | Needs outside knowledge | FAIL — reground or drop |
| `other_defensible` non-empty | Ambiguous | FAIL — revise |
| Chain shorter than the intended one | Shortcut exists | FAIL — the question is easier than designed |
| Quotes fabricated or absent | Not grounded | FAIL — verify against source |

Target ≥90% of items passing. Below that, the *generation* is at fault, not the judge.

## Gate 3 — Order and grounding audit

Confirms the questions are genuinely third-order rather than recall in vignette clothing.

**Run this in the gate-2 agent, as a second turn.** It already has the source loaded, so a
fresh agent would re-send the whole source for no gain in independence — both gates are
sourced passes, and neither is the blind pass whose isolation matters. Spawning separately is
allowed but costs a spawn and a second copy of the source every round.

```
Audit each question for cognitive order, using this rubric:

- First order: one fact retrieved from the source.
- Second order: the stem states a relationship; the student applies it once.
- Third order: the student must supply a bridging fact the stem never states, and
  chain 3+ facts. The answer term and its category do not appear in the stem.

For each question:
1. Count inference hops a student must make (a hop = one distinct fact retrieved and
   applied).
2. Assign order: 1, 2, or 3.
3. Does the answer term or its category appear in the stem? (yes/no)
4. Is the stem still answerable with the options covered? (yes = options leak)
5. Is each distractor a true statement drawn from the source? List any that are
   absurd, absolute, or invented.
6. Does length parity hold — longest option ≤1.3x the shortest? Any option
   containing "because"/"since"/"due to"?

SOURCE MATERIAL:
{extracted text}

QUESTIONS (with answer key):
{questions and key}

Return one JSON array and no prose:
[{"question_id": 1, "hop_count": 3, "order": 3, "answer_in_stem": false,
  "answerable_without_options": true, "bad_distractors": [], "parity_ok": true,
  "notes": ""}]
```

Fail any question with `order < 3`, `answer_in_stem: true`,
`answerable_without_options: false`, non-empty `bad_distractors`, or `parity_ok: false`.

## Consolidated verdict

One row per question:

```json
{"question_id": 1, "blind_guess": "C", "cue_used": "longest option",
 "with_source_answer": "D", "keyed_answer": "D", "hop_count": 3, "order": 3,
 "grounded": true, "verdict": "PASS", "failure_reason": ""}
```

`verdict` is PASS only when **all** hold:
- gate 1 did not identify the key via a named cue
- gate 2's answer matches the key, with a sound chain and real quotes
- gate 2 found no other defensible option and needed no outside knowledge
- gate 3 reports order 3, answer absent from stem, clean distractors, parity OK

## Handling failures

1. Report the pass rate and each failure reason. **Never silently drop failures** —
   a set that quietly shrinks from 10 to 6 misrepresents what was delivered.
2. Rewrite failures against the specific reason:
   - *Blind-guessable* → redraw all options from **one closed source category** in
     identical form; equalize length; move rationale to the key. If the judge's cue was
     *elimination* ("the stem rules out the others"), the fix is in the **stem**: delete
     every `normal` / `identical` / `unaffected` clause the mechanism doesn't need.
   - *Two defensible answers* → narrow with "most directly"/"most likely," or replace
     the competing option.
   - *Order too low* → remove the bridging fact from the stem, or extend the chain.
   - *Answer in stem* → rewrite as observations only.
   - *Ungrounded* (`source_sufficient: false`) → the vignette leans on outside knowledge.
     Usually the trigger detail is too oblique: a mushroom "gathered at the base of an oak"
     with coagulopathy requires clinical toxicology the source never states. Name the thing
     the source itself names ("identified as a death cap") and let the hops run from there.
3. Re-run **all three gates** on rewrites — but **only on the rewritten questions**. A rewrite
   is a new question, not a patch; fixing length parity can easily introduce a second
   defensible answer. A question that passed is finished: re-judging it cannot improve it and
   costs the same as judging it the first time. See "Scoping the rewrite loop" below.

   *Hop count collapsed after regrounding* → the vocabulary step you removed **was** a hop.
   A question asking which transcript class a death-cap-poisoned polymerase stops making ran
   4 hops while the answer was `Interfering` (the source says `mi/siRNA`) and dropped to 2 as
   soon as the option was renamed to the source's literal `protein-coding` — the source links
   mushroom → Pol II → mRNA in a single clause. Do not restore the synonym; the question was
   never third order, the ungrounded step was only *masquerading* as one. Find a concept
   whose chain is 3 hops in the source's own vocabulary.

   Expect fixes to fight each other. Real sequences from building this skill:
   equalizing length made the correct option the longest; fixing that clustered three
   answers on B; adding exclusions for gate 2 handed gate 1 an elimination path. Run
   `scripts/check_mechanics.py` after every edit and re-check the whole set, not the
   question you touched. When an option is unavoidably the longest because its
   category word just *is* longer (`Interfering` vs `Ribosomal`), lengthen a distractor
   rather than mangling the answer.
4. Cap at 3 rewrite rounds per question — **count the rounds, out loud, per question.** This
   cap has been documented since the first version of this file and was still exceeded in a
   real build: one question was flagged by gate 2 in rounds 1, 2, 4, 5, 6 and 7 — seven rounds
   under a three-round cap, because nobody was counting. Beyond the cap, **replace the concept
   rather than patching the question** — or report it unresolved. Some option sets carry a defect no
   wording fixes: the five parts of a mature transcript contain two natural pairs (two
   termini, two UTRs), which leaves the coding sequence permanently the odd one out, and a
   blind judge said so. Two questions in this build hit the cap and were rewritten onto
   different concepts with enumerable option sets; both then scored a 1.00 length ratio.
   Grinding a fourth round on a structurally cued set wastes tokens.

## Scoping the rewrite loop

Judge spawns are the entire cost of this harness. A student on a metered plan ran this skill
twice and spent ~20% of a weekly limit — not because the gates are expensive to *pass*, but
because the loop re-judged work that was already done.

Measured from two real builds: a 5-question set consumed **~24 judge spawns**, and a
10-question set delivered **40 question-judgments to resolve one failing question**. Every one
of those extra judgments returned the same verdict as the round before it.

**The loop:**

| Round | What gets judged | Cost |
|---|---|---|
| 1 | The full set — gate 1's set-wide hit-rate check needs it | 2 spawns (gate 1; gate 2+3 share one) |
| 2+ | **Only the questions that failed** | 2 spawns, tiny payload |
| after every edit | `scripts/check_mechanics.py` on the **whole set** | free |
| a round comes back clean | **stop** | — |

Rules, in order of how much they save:

1. **Never re-judge a passing question.** Rounds 2+ carry only the rewritten questions. If one
   question of ten failed, judge one question.
2. **A clean round ends the loop.** Do not run a confirmation round. In one build, gate 1 ran
   three further full-set rounds after the last real failure was fixed; all three returned no
   cues on any question. That is three rounds of pure spend.
3. **Count rewrite rounds per question and stop at 3** (see "Handling failures" item 4).
4. **Gate 3 runs in the gate-2 agent** — one sourced agent per round, not two.
5. **`check_mechanics.py` runs first and must exit 0** before any judge is spawned. It costs
   nothing and catches length parity, absolutes, reasoning words, stem echo and answer-position
   clustering. Judge tokens spent on those is money burned.

**What this trades away, stated plainly.** After round 1, gate 1 no longer recomputes a
set-wide blind hit rate, so a *systemic* tell introduced by a late rewrite is caught by
`check_mechanics.py` (clustering, parity, absolutes) but not by a fresh blind pass over the
whole set. If a build needed many rewrite rounds and you have reason to think the set drifted
as a whole, one final full-set gate 1 is a defensible spend — but it is a deliberate choice,
not the default.

What does **not** change: all three gates still run on every question, gates 1 and 2 stay
separate agents on a different model than the generator, and every PASS condition in the
consolidated verdict above still holds. Nothing here makes a question easier to pass.

## Same-model fallback (only when a cross-model subagent isn't available)

Cross-model judging is the point of this harness, not an optional strengthening —
"a model grading its own questions rates them well; it reconstructs the reasoning it
just used and mistakes that fluency for question quality" (top of this file) is exactly
as true when the same model self-critiques in the same conversation. Use this fallback
only when the environment genuinely cannot spawn a subagent on a different model — e.g.
this skill running as an uploaded Skill on claude.ai's plain Chat tab (not the Code tab),
a single Claude instance with no `Agent` tool. If a cross-model subagent is available at
all — including Claude Code's terminal, Desktop app Code tab, or claude.ai/code in a
browser, which all support it — use it; this section is not a shortcut.

Run the **same three gates, same prompts, same JSON shapes, and same scoring tables**
already defined above (Gate 1, Gate 2, Gate 3) — nothing about the prompts changes.
The only difference is who runs them:

- No separate subagent: reason through each gate **sequentially, in strict isolation
  from the others**. Run Gate 1 first, in a response that does not look back at the
  drafted answer key or the source material. Only after recording Gate 1's verdicts,
  move on to Gate 2 with the source; only after that, Gate 3.
- Gates 1 and 2 still cannot be the same reasoning pass — the model must genuinely
  attempt to forget the key and the source before Gate 1, the same way a human test-taker
  would. If you cannot honestly separate "what would a blind guesser see" from "what do I
  know the answer is," treat that question as **FAIL** for Gate 1 rather than reporting a
  false pass.
- This fallback cannot catch what cross-model judging exists to catch: a model's fluency
  at reconstructing its own reasoning, mistaken for the question being sound. Treat every
  PASS here as provisional.
- **"Scoping the rewrite loop" applies here too**, and matters more: reasoning passes in one
  context re-read the source and the whole question set every round. Round 1 covers the full
  set, rounds 2+ only the failures, a clean round ends the loop, cap 3 rounds per question, and
  `check_mechanics.py` runs first if a shell is available.

Every deliverable produced under this fallback must say so (see SKILL.md step 6) — never
report fallback results as if the cross-model harness ran.

## Reporting to the user

State plainly:
- generator model, judge model (or "same-model fallback" if no cross-model subagent was
  available), N requested vs N passing
- per-gate results, blind hit rate vs chance
- any question that failed 3 rounds and why
- **judge spawns used, and rewrite rounds per question.** Two spawns per round is the target;
  a run that used many more is a bug in the loop, not thoroughness. Reporting it is what keeps
  the cost honest and visible to a user on a metered plan.
- if fewer than N survived, say so rather than padding with recall questions
- if the same-model fallback ran, say so explicitly and note that pass results are
  provisional, not equivalent to a cross-model verdict
