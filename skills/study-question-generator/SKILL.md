---
name: study-question-generator
description: Use when generating practice exam questions, quiz questions, or test questions from study material such as a PDF, PowerPoint, article, or lecture notes — especially when the request asks for third-order, higher-order, application-level, or comprehension-testing questions, or for board-style clinical vignettes.
---

# Study Question Generator

Turns source material into N third-order practice questions, then validates them with a
cross-model judge before delivery.

**Core principle: a question a student can answer without knowing the material tests
nothing.** Surface cues — a longer correct option, embedded reasoning, absurd
distractors — make questions guessable. The judge harness exists to catch exactly that,
and it is not optional.

## Inputs

Source file is required. Defaults: N=10, all pages, HTML output (`--docx` on request).
Ask only for what is missing.

**Exclude the source's own practice questions** if it has any — generating from them
produces copies. Pass `--pages` with the content sections only.

## Workflow

### 1. Extract

```bash
python3 scripts/extract_source.py SOURCE.pdf --pages 5-8,17-18 --out /tmp/source.txt
```

Handles pdf, pptx, docx, html, md, txt. Read the extracted text before writing anything.

### 2. Inventory the facts

List the discrete facts the source teaches and where each appears. Chaining is what makes
a question third order, and you cannot chain what you have not enumerated. N questions
need roughly 3N chainable facts — if the source is thinner, generate fewer.

### 3. Build a chain per question

Write the chain before any prose:

```
Q3: patient given epinephrine → no response
  → epinephrine signals via a second messenger
  → that messenger is cAMP
  → answer: cAMP  (3 hops)
```

**≤2 hops is not third order** — extend or drop it. Then write the vignette *backwards*
from the chain, removing every bridging fact.

### 4. Write to the rules

**Read `references/question-anatomy.md`** for the rubric, the three reusable patterns,
and the distractor taxonomy. Summary of the non-negotiables:

- **Stem:** vignette framing; observations only, never the mechanism the student must
  supply; answer term and its category absent; one question, never "predict X and why";
  some irrelevant detail; no meta-language (no order names, topics, or slide numbers).
- **Options:** 4–5, same grammatical form, terse; longest ≤ ~1.3× shortest; none contain
  `because`/`since`/`due to`; every distractor a **true source fact that answers a
  neighboring question**; vary the correct position across the set.

### 5. Validate — required

Read `references/judge-protocol.md` and run all three gates via subagents on a
**different model** than the one generating (Opus generating → judge with Sonnet;
Sonnet generating → judge with Opus; pass `model` explicitly to the Agent tool).

1. **Blind-cue gate** — judge sees questions with *no source*, uses only test-taking
   heuristics. Hitting the key with a named cue = FAIL, rewrite. Runs first.
2. **Answerability gate** — separate agent, *with* source, must pick the keyed answer,
   reconstruct the chain, and quote the source.
3. **Order audit** — hop count ≥3, answer absent from stem, distractors clean.

Gates 1 and 2 must be **separate agents**: one that has read the source cannot do a
credible blind pass.

Rewrite failures and re-run all three gates on them. Cap at 3 rounds per question, then
report it unresolved.

### 6. Deliver

Two markdown files, then render:

```bash
python3 scripts/render_output.py questions.md --footer "Source: lecture.pdf"
python3 scripts/render_output.py answers.md   --footer "Source: lecture.pdf"
```

- `questions.md` → **no answers anywhere** (verify before handing over)
- `answers.md` → correct option, the full reasoning chain, and why each distractor is
  wrong

HTML is self-contained and prints to PDF from any browser (Cmd+P) — no Word or LaTeX
needed. Add `--docx` if the recipient wants to edit in Word.

Report: generator model, judge model, N requested vs N passing, blind hit rate vs
chance, and anything unresolved.

## Red flags — stop and fix

| Red flag | Fix |
|---|---|
| Correct option is longest, or the only one explaining itself | Equalize length; move rationale to the key |
| An option contains `because` / `since` / `due to` | Strip it; one claim per option |
| A distractor is absurd ("Magnets") or absolute ("no effect") | Replace with a true source fact from a neighboring step |
| Stem states the mechanism or names the answer's category | Rewrite as observations only |
| Chain is ≤2 hops | Extend the chain or drop the question |
| Stem still answerable with options covered | Options leak — rewrite them |
| Wrote the stem before the chain | Chain first, vignette backwards from it |
| Source too thin for N | Cap N and say so; never pad with recall questions |
| "Questions look good, skip the judge" | Run all three gates. Not optional |
| Judge inherits the session model | Pass `model` explicitly — never same-model judging |
| One agent runs both blind and sourced gates | Use separate agents |
| Failures quietly dropped so the set looks clean | Report pass rate and every failure |
