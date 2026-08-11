---
name: study-question-generator
description: Use when generating practice exam questions, quiz questions, or test questions from study material such as a PDF, PowerPoint, article, or lecture notes — especially when the request asks for third-order, higher-order, application-level, or comprehension-testing questions, or for board-style clinical vignettes.
---

# Study Question Generator

Turns source material into N third-order practice questions, then validates them with a
cross-model judge before delivery.

**Core principle: a question a student can answer without knowing the material tests
nothing.** Surface cues — a longer correct option, embedded reasoning, absurd
distractors — make questions guessable. The judge harness catches exactly that, and it is
not optional.

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

If the script can't run at all — no shell/Bash tool, or a missing dependency like
`pypdf` in a sandboxed environment (e.g. this skill uploaded to claude.ai's Chat tab,
not the Code tab) — read the source file directly instead of blocking on the script.

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

**Read `references/question-anatomy.md`** — the rubric, the reusable patterns, and the
distractor taxonomy. The four non-negotiables:

- **Stem:** vignette; observations only; the answer term and its category absent; one
  question; no meta-language. **It rules nothing out** — strike any
  `normal`/`identical`/`unaffected` clause the mechanism doesn't need.
- **Options:** 4–5 from **one closed source category**, in the source's own vocabulary,
  identical grammatical form, same level of generality. Best case is an enumerated label set
  with no descriptive content (`TFIID…TFIIH`, `Asn/Gln/Ser/Thr/Tyr`) — nothing to cue on.
- **Every distractor a true source fact** that answers a neighboring question. Longest
  ≤ ~1.3× shortest, no `because`/`since`/`due to`, vary the correct position.
- **No semantic echo:** the key must not paraphrase the stem. `barrel-shaped` → `cavity` and
  `add and remove` → `adjusting` were each picked blind despite sharing no words.

Resolve ambiguity in the options, never by narrating exclusions in the stem.

Then pre-screen mechanically before spending judge tokens:

```bash
python3 scripts/check_mechanics.py questions.md --key C,A,D,B,C
```

### 5. Validate — required

**Check first whether the Agent tool can spawn a subagent on a specific model.** In
Claude Code — the terminal, the Desktop app's Code tab, or claude.ai/code in a browser,
all three are the same engine — it can, so use the cross-model harness below exactly as
written, nothing changes. If it can't (e.g. this skill is running as an uploaded Skill on
claude.ai's plain Chat tab, a single conversation with no ability to hand off to a
separate model), run the **same-model fallback** in `references/judge-protocol.md`
instead, and mark every deliverable accordingly (see step 6). The fallback is strictly
weaker — use it only when the cross-model harness genuinely isn't available, never as a
shortcut.

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
  wrong — **with a source citation on every hop and every distractor** (slide/page number
  plus the source's own words). Gate 2 already quoted the source for each link; carry those
  quotes into the key instead of discarding them. An uncited key can't be checked by the
  student and hides the moment a hop drifted into outside knowledge.
- Verify citations mechanically before delivering: every quoted string must appear verbatim
  in the extracted text, under the slide/page it is attributed to.
- A question that failed a gate ships with that failure marked **on the question itself**
  in the key, not only in the chat report — the file outlives the conversation.
- If step 5 ran the same-model fallback instead of the cross-model harness, say so at the
  top of `answers.md`: *"⚠️ Validated by same-model self-critique only — no cross-model
  judge was available in this environment. Treat pass results with less confidence than a
  Claude Code run."*

HTML is self-contained and prints to PDF from any browser (Cmd+P) — no Word or LaTeX
needed. Add `--docx` if the recipient wants to edit in Word.

Report: generator model, judge model (or "same-model fallback" if that's what ran), N
requested vs N passing, blind hit rate vs chance, and anything unresolved.

## Red flags — stop and fix

| Red flag | Fix |
|---|---|
| Correct option is longest, or the only one explaining itself; any option has `because`/`since`/`due to` | Equalize length; rationale belongs in the key |
| A distractor is absurd ("Magnets") or absolute ("no effect") | Replace with a true source fact from a neighboring step |
| Stem states the mechanism, names the answer's category, or says a step is `normal`/`identical`/`unaffected` | Observations only. That clause is an elimination path for guessers |
| "The stem needs that clause or the answer is ambiguous" | Fix the options instead — a homogeneous set is unambiguous without exclusions |
| Options span categories, use a synonym the source never uses, or mix one general capability with three specific acts | Redraw from one closed category, in the source's words, at one level of generality |
| The correct option restates the stem in different words | Rewrite in the source's vocabulary — semantic echo is invisible to `check_mechanics.py` |
| Stem paraphrases an abbreviation the source never expands (`HATs` → "add acetyl groups") | Use the source's own phrase; expanding it silently imports outside knowledge |
| Chain is ≤2 hops, or the stem is still answerable with options covered | Extend the chain / rewrite the leaking options, or drop it |
| Hop count dropped after you fixed grounding | The removed synonym *was* the third hop — change concepts, don't restore it |
| Third rewrite still fails | Replace the concept. Some option sets are permanently cued (five transcript parts = two pairs + one odd) |
| Wrote the stem before the chain | Chain first, vignette backwards from it |
| Source too thin for N | Cap N and say so; never pad with recall questions |
| "Questions look good, skip the judge" | Run all three gates. Not optional |
| Judge inherits the session model, or one agent runs both the blind and sourced gates | Pass `model` explicitly; use separate agents |
| Failures quietly dropped so the set looks clean | Report pass rate and every failure |
| Answer key states a chain with no citation | Cite the slide/page and quote the source per hop — Gate 2 produced those quotes already |
| A gate failure is mentioned only in chat | Mark it in the key too; the student reads the file, not the transcript |
| Same-model fallback used when a cross-model subagent was actually available | Never take the weaker path as a shortcut; use it only when the environment genuinely can't spawn a different-model subagent |
| Fallback ran but the key doesn't disclose it | State it at the top of `answers.md`, not only in chat |
