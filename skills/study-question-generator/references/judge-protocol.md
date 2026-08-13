# Judge Protocol

Validation harness for a generated question set. Three gates, each a **separate
subagent on a different model than the one that wrote the questions**.

A model grading its own questions rates them well — it reconstructs the reasoning it
just used and mistakes that fluency for question quality. Cross-model judging is the
point of this harness, not an optimization.

## Model resolution

**"Generator" means the model that *wrote the questions*, not the session model.** Questions
are written by Sonnet subagents (see "Batched generation" below), so the main session's model
is irrelevant to cross-model integrity — what matters is that no gate runs on Sonnet.

| Role | Model | Why this tier |
|---|---|---|
| Generator, and every rewrite | Sonnet 5 (`model: sonnet`) | The largest cost in a run is writing questions, not judging them |
| Gate 1 — blind cue | Haiku 4.5 (`model: haiku`) | Gate 1 is *forbidden* from using domain knowledge and applies surface-form heuristics only, so capability buys nothing — the cheapest model does this identically |
| Gates 2+3 — answerability, order | Opus 5 (`model: opus`) | These need real capability, and both run in one agent |

Pass the choice explicitly via the Agent tool's `model` parameter — for generators as well as
judges. Never let any of them inherit the session model: an inherited generator silently
becomes whatever the session is (often Opus, the thing this is avoiding), and an inherited
judge silently collapses to same-model judging.

Do not use Haiku as judge for gate 2: it may fail a hard question for lack of capability,
which reads as a false question defect. That asymmetry is exactly why gate 1 and gates 2+3
get different models rather than one shared judge model — gate 1 cannot suffer from it,
because it is not allowed to reason about the subject at all.

Cost note, for reasoning about the tiers rather than quoting numbers: at API list rates Opus 5
is roughly 1.7× Sonnet 5 and 5× Haiku 4.5 per token. Subscription plans weight models
differently and the weighting isn't published, so treat the ordering as reliable and the
ratios as approximate.

## Batched generation

Judge spawns are *not* the dominant cost of a run — the generating context is. Writing N
questions in one conversation means each new question is written with the source, the fact
inventory, and every question already written in context, so input cost grows roughly
quadratically in N. A 15-question set written this way ran 45 minutes and consumed most of a
day's subscription budget, against roughly 80K tokens total for four judge rounds.

So generation is **split into parallel Sonnet subagents of ~5 questions each**, while judging
stays **pooled over the whole set**:

| | Split | Pooled |
|---|---|---|
| Generation, and rewrites | ✅ one subagent per batch of ~5, spawned in parallel | |
| Gate 1 | | ✅ one agent, all N questions |
| Gates 2+3 | | ✅ one agent, all N questions, source read once |

Both halves of that matter. Splitting generation removes the quadratic growth and the
serialization. Keeping judging pooled is what protects the harness: gates 2+3 would otherwise
re-send the whole source once per batch, and gate 1's set-wide hit-rate check would be
computed over 5 questions instead of N, which is too small to mean anything.

### Nothing moves except paths

Splitting generation only helps if the material stays split. So every handoff in a run is a
**file path**, and the orchestrator holds none of the contents:

| Artifact | Written by | The orchestrator holds |
|---|---|---|
| `/tmp/source.txt` | `scripts/extract_source.py` | the path and the word count the script printed |
| `facts.md` — facts pre-grouped under `## Batch 1`, `## Batch 2`… | a **delegated Sonnet subagent**, not the orchestrator | the path, and the totals it reported |
| `batch1.md`, `batch2.md`, … | one Sonnet generator each, in parallel | the paths, plus each batch's answer key |
| `questions.md` | `cat batch*.md > questions.md` | the path |

Each generator subagent gets: the **path** to the extracted source, the **name of its `## Batch
N` heading** in `facts.md`, the writing rules verbatim, and a target answer-position spread for
its batch. It reads the source and its own fact group itself. Disjoint groups are what stop two
batches building the same concept; the position targets are what stop the merged set clustering
on one letter. Cross-batch clustering and parity are then caught free by
`scripts/check_mechanics.py` on the merged set, which is set-wide already.

The inventory is delegated for the same reason the questions are. A ~45-fact list read into the
orchestrator is exactly the accumulation this section exists to remove, and grouping belongs
with the agent that enumerated the facts anyway — it knows which ones chain.

Generator prompts carry the same "load nothing" rule as judge prompts, below — for the same
reason and at the same cost per spawn.

## Judges and generators load nothing

Every prompt in this file is complete on its own: it carries the task, the JSON shape, and the
**paths** to whatever the agent must read. The only payload interpolated anywhere is gate 3's
answer key, which is a list of letters. That makes the rule below matter more rather than less —
an agent already told to go read two files is more likely to go read a third. So end each judge
prompt with:

> Read only the files named above. Do not invoke the study-question-generator skill and do not
> read any of its files — this prompt plus those files are everything you need. Return only the
> JSON.

Without that line a judge is liable to load `SKILL.md` and `question-anatomy.md` — roughly
5,600 tokens of *question-generation* rules, on every spawn, for an agent whose only job is to
answer or audit. This skill's `description` triggers on the phrase "exam questions," which is
exactly what a judge prompt is full of. Worse, a judge that has read the generation rules is
no longer a naive test-taker: gate 1's whole premise is a reader who knows nothing about how
the question was built.

Naming the files it *should* read is part of the same rule. A prompt that says "read
`questions.md`" and stops there leaves the agent to decide what else is relevant; a prompt that
says which paths to read and that nothing else is needed does not.

**Generator subagents get the same line**, with `question-anatomy.md`'s rules pasted into the
prompt instead. A generator that loads the skill re-reads the same ~5,600 tokens on every
batch spawn, which is a large fraction of what batching just saved. Paste the rules; don't
send the agent to fetch them.

## Gate 1 — Blind-cue gate (non-negotiable)

**Spawn gate 1 and the gate-2/3 agent in the same message, in parallel.** Nothing consumes
gate 1's output before gates 2 and 3 run — the verdicts are only combined at the consolidated
verdict below — so running them in sequence buys nothing and roughly doubles judge wall clock.
Gate 1 is still a *separate agent with no source*; that is what is non-negotiable, not its
ordering.

Detects the dominant failure: a question answerable from surface form alone.

The judge reads stems and options **from `questions.md`, and nothing else** — no source
material, no answer key — and is forbidden from using domain reasoning. If it still lands on
the keyed answer *and* can name the cue, the question is broken.

**Separate agent, no source access.** An agent that has read the source cannot
credibly perform this pass. `questions.md` carries no answers (`--assert-no-answers` gates
that before delivery, SKILL.md step 6), so handing over the path is not handing over the key.

```
You are taking a multiple-choice exam. Read the questions from questions.md.

That file is the ONLY thing you may read. Do not read /tmp/source.txt, facts.md, or any
other file: you have NO access to any source material, textbook, or notes, and you must
NOT use subject-matter knowledge to reason about the content.

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
`scripts/check_mechanics.py`, which flags any letter holding more than about
`n / k + 1` of the answers — chance plus one — for free. See "Scoping the rewrite loop"
below.

## Gate 2 — Answerability gate

The user's core requirement: a different model must answer **accurately and completely
using only the source material**.

Fresh agent, **with** the source, **without** the answer key. Requiring a quoted source
passage is what separates "the question is broken" from "the judge slipped" — an
unsupported answer means the question isn't grounded.

```
Read the source material from /tmp/source.txt and the questions from questions.md.

You are answering those questions using ONLY that source material. Do not use outside
knowledge. If the source does not support an answer, say so explicitly.

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

**Run this in the gate-2 agent, as a second turn.** It has already read both files, so a fresh
agent would re-read the whole source for no gain in independence — both gates are sourced
passes, and neither is the blind pass whose isolation matters. Spawning separately is allowed
but costs a spawn and a second copy of the source every round.

The **answer key is the one thing this prompt interpolates**, because `questions.md` doesn't
contain it and must not: it is the student-facing file, and `--assert-no-answers` fails if an
answer reaches it. A key is a list of letters, so passing it inline costs nothing.

```
Audit each question in questions.md — which you have already read, along with the source
at /tmp/source.txt — for cognitive order, using this rubric:

- First order: one fact retrieved from the source.
- Second order: the stem states a relationship; the student applies it once.
- Third order: the student must supply a bridging fact the stem never states, and
  chain 3+ facts. The answer term and its category do not appear in the stem.

For each question:
1. Count inference hops a student must make (a hop = one distinct fact retrieved and
   applied).
2. Assign order: 1, 2, or 3.
3. Does the answer term or its category appear in the stem? (yes/no)
4. Cover the options and read the stem alone. Could a reader who knows this
   source produce the keyed answer without seeing the option list? (no = the
   options are carrying the question)
5. Is each distractor a true statement drawn from the source? List any that are
   absurd, absolute, or invented.

ANSWER KEY: {Q1: C, Q2: A, …}

Return one JSON array and no prose:
[{"question_id": 1, "hop_count": 3, "order": 3, "answer_in_stem": false,
  "answerable_from_stem_alone": true, "bad_distractors": [], "notes": ""}]
```

Fail any question with `order < 3`, `answer_in_stem: true`,
`answerable_from_stem_alone: false`, or non-empty `bad_distractors`.

Item 4 runs in that direction on purpose: a well-posed question is answerable from the stem
alone, and the options only offer somewhere to put the answer. Inverted, it fails good
questions — *"which polymerase synthesizes rRNA?"* is answerable with the options covered and
leaks nothing.

**Parity and reasoning words are deliberately absent from this prompt.**
`check_mechanics.py` gates both, free, and must exit 0 first, so re-asking here can only
manufacture false failures — a 1.32 set clears the script's 1.35 but fails a judge told
"1.3", and an enumerated-label set the script skips (`CSB` vs `TFIIH` = 1.67) reads as a
parity defect. Each one costs a rewrite round to discover the tooling disagreed with itself.

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
- gate 3 reports order 3, answer absent from stem, answerable from the stem alone, and
  clean distractors (parity is already gated by `check_mechanics.py`)

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
3. Rewrites go to **Sonnet generator subagents, one per failing question, in parallel** — not
   into the main session. Each gets the path to `questions.md`, the question number, the source
   path, and the judge's failure reason verbatim, and **edits that question in place**; the
   orchestrator holds numbers and reasons, never question text. Doing it in the orchestrator
   drags the whole set back into an expensive context, which is what batching exists to prevent.
   Keeping rewrites on Sonnet is also what keeps Opus a genuine cross-model judge for gates 2+3.
4. Re-run **all three gates** on rewrites — but **only on the rewritten questions**. A rewrite
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
5. Cap at 3 rewrite rounds per question — **count the rounds, out loud, per question.** This
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

Judge spawns are the entire cost *of this harness* — though not of a run as a whole, which the
generating context dominates (see "Batched generation"). A student on a metered plan ran this
skill twice and spent ~20% of a weekly limit — not because the gates are expensive to *pass*,
but because the loop re-judged work that was already done.

Measured from two real builds: a 5-question set consumed **~24 judge spawns**, and a
10-question set delivered **40 question-judgments to resolve one failing question**. Every one
of those extra judgments returned the same verdict as the round before it.

**SKILL.md step 5 has the loop table** — round 1 full set, rounds 2+ failures only,
`check_mechanics.py` free after every edit, a clean round stops. What that table can't carry
is *why each rule exists*, which is what makes them hold up under pressure:

1. **Never re-judge a passing question.** Re-judging cannot improve it and costs exactly what
   judging it the first time cost. If one question of ten failed, judge one question.
2. **A clean round ends the loop.** In one build, gate 1 ran three further full-set rounds
   after the last real failure was fixed; all three returned no cues on any question. Three
   rounds of pure spend, bought by wanting confirmation.
3. **Count rewrite rounds per question and stop at 3** (see "Handling failures" item 4).
4. **Gate 3 runs in the gate-2 agent** — a fresh agent would re-send the whole source for no
   gain in independence.
5. **`check_mechanics.py` must exit 0 before any judge is spawned, and run it with
   `--source`.** Length parity, absolutes, reasoning words, stem echo, answer-position
   clustering and **option-vocabulary grounding** are all free there and cost a full round to
   find here. Grounding is the one worth naming: without `--source`, an option that renames a
   source concept reaches gate 2 and comes back `source_sufficient: false`, and those are the
   rewrites that collapse hop count and burn the 3-round cap (see "Handling failures" item 2).
6. **Rewrite in parallel Sonnet subagents, one per failing question** — not in the
   orchestrator, which would pull the whole set back into an expensive context.

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
  `check_mechanics.py` runs first if a shell is available — with `--source`, which matters more
  here too, since there is no cheap judge to fall back on.
- **Batched generation does not apply** — there are no subagents to batch into. Write the
  questions in this one context, and expect the cost this section's whole preamble is about.
  Keeping N small is the only lever available on this surface.
- **The gate prompts' "read `questions.md`" / "read `/tmp/source.txt`" instructions collapse
  back to reading them yourself.** File paths exist to keep material out of an expensive
  context; here there is only one context and it already holds everything, so there is nothing
  to keep out. If the surface has no shell either, the source is whatever you read from the
  uploaded file — and `check_mechanics.py` can't run, so every check it would have made for
  free is back on you.

Every deliverable produced under this fallback must say so (see SKILL.md step 6) — never
report fallback results as if the cross-model harness ran.

## Reporting to the user

State plainly:
- generator model, gate-1 model, gate-2/3 model (or "same-model fallback" if no cross-model
  subagent was available), N requested vs N passing
- per-gate results, blind hit rate vs chance
- any question that failed 3 rounds and why
- **spawns used, by kind, and rewrite rounds per question.** Through round 1, expect **1
  inventory + `ceil(N/5)` generators + 2 judges**, plus one Sonnet spawn each time the
  mechanical screen names something to fix. Then 2 judge spawns and one generator spawn per
  failing question per rewrite round, and one final Sonnet spawn to assemble `answers.md`. A run
  that used many more is a bug in the loop, not thoroughness. Reporting it is what keeps the
  cost honest and visible to a user on a metered plan.
- whether the main session ever held **the source text, the fact list, or the question set** in
  working context. It should have held none of the three: the source stays in `/tmp/source.txt`,
  the facts in `facts.md`, the questions in `batchN.md`/`questions.md`, and the orchestrator
  moves paths, JSON verdicts and exit codes. If it read one of those files, or started
  rewriting questions itself, that is the expensive failure mode returning — say so, because
  the token count will show it and the cause won't be obvious otherwise.
- if fewer than N survived, say so rather than padding with recall questions
- if the same-model fallback ran, say so explicitly and note that pass results are
  provisional, not equivalent to a cross-model verdict
