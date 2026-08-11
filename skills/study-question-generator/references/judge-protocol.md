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

Answer using ONLY test-taking heuristics: option length, grammatical parallelism,
how much detail an option gives, whether an option contains absolutes (never, no
effect, entirely), whether an option embeds its own justification, and which option
"looks like" what an exam writer would mark correct.

For each question: state your guess and name the specific surface cue that led you
there, or "none" if you were genuinely guessing at random.

{questions with options, no answers}

Return one JSON array and no prose:
[{"question_id": 1, "blind_guess": "C", "cue_used": "longest option; only one with a
mechanism", "confidence": "high|medium|none"}]
```

**Scoring.** With *k* options, random guessing yields ≈1/*k*.

| Result | Verdict |
|---|---|
| Guess ≠ key | PASS |
| Guess = key, `confidence: none` | PASS (coincidence) |
| Guess = key **and** a real cue named | **FAIL — rewrite** |
| Set-wide hit rate ≫ 1/*k* | **FAIL the set** — systemic tell, likely length parity or position clustering |

Also fail the set if correct answers cluster in one position, even when individual
questions pass.

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
May reuse the gate-2 agent, which already has the source loaded.

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
   - *Blind-guessable* → equalize option length; move rationale to the key; replace
     absolutes with true-but-wrong-step facts.
   - *Two defensible answers* → narrow with "most directly"/"most likely," or replace
     the competing option.
   - *Order too low* → remove the bridging fact from the stem, or extend the chain.
   - *Answer in stem* → rewrite as observations only.
   - *Ungrounded* → replace with a fact the source states.
3. Re-run **all three gates** on rewrites. A rewrite is a new question, not a patch;
   fixing length parity can easily introduce a second defensible answer.
4. Cap at 3 rewrite rounds per question. Beyond that, report it as unresolved with the
   reason instead of grinding — some source material simply cannot support a
   third-order question on that concept.

## Reporting to the user

State plainly:
- generator model, judge model, N requested vs N passing
- per-gate results, blind hit rate vs chance
- any question that failed 3 rounds and why
- if fewer than N survived, say so rather than padding with recall questions
