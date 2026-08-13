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

## How the work is divided

**You are an orchestrator. You move file paths, not content.** The single largest cost in a run
is the context that accumulates around writing questions — larger than the judge harness (see
"Batched generation" in `references/judge-protocol.md`). Batching splits that across subagents;
what keeps it split is that **the source text, the fact list, and the question text never enter
your context at all.**

| Step | Where it runs | What you hold |
|---|---|---|
| Extract (a shell command) | you | the output path |
| Inventory facts → `facts.md` | Sonnet subagent | the path, and the batch count it reports |
| Write questions → `batchN.md`, ~5 each, parallel | Sonnet subagents (`model: sonnet`) | the paths |
| Merge (a shell command) | you | the path |
| Screen (`check_mechanics.py`) | you | its pass/fail output |
| Fix what the screen names | Sonnet subagent | the path |
| Gate 1, blind cue | Haiku subagent (`model: haiku`), no source | its JSON verdict |
| Gates 2+3, answerability and order | Opus subagent (`model: opus`), source once | its JSON verdict |
| Rewrites, one per failing question, parallel | Sonnet subagents (`model: sonnet`) | the paths |
| Assemble `answers.md` from gate 2's quotes | Sonnet subagent | the path |

**Do not read `/tmp/source.txt`, `facts.md`, `batchN.md`, or `questions.md`.** Every agent that
needs one is given the path and reads it itself. You need the *shape* of the run — how many
questions, which ones failed, which round each is on — and that fits in JSON verdicts and
script output. Reading any of those files pulls the expensive material back into the priciest
context in the run and undoes the split.

Two consequences worth stating, since they replace things you'd otherwise do by eye:

- **You cannot eyeball the set before delivery**, so `--assert-no-answers` is what guarantees
  `questions.md` carries no answers (step 6), and `--answers` is what verifies the key's
  citations (step 6). Both are gates, not reports.
- **You cannot hand-fix what the screen names**, so send `check_mechanics.py`'s output and the
  file path to a Sonnet subagent and let it edit the file in place.

Pass `model` explicitly on every spawn, generators included. A generator that inherits the
session model silently becomes whatever the session is, which is what this is avoiding.

**Order every subagent prompt cache-friendly:** invariant material first (the source, the
writing rules, the gate prompt), variable material last (which batch, which fact slice, which
question failed). Spawns then share a long identical prefix. This is a free bet rather than a
guarantee — caching is managed for you and subscription accounting for cache reads isn't
published — but the ordering costs nothing.

## Workflow

### 1. Extract

```bash
python3 scripts/extract_source.py SOURCE.pdf --pages 5-8,17-18 --out /tmp/source.txt
```

Handles pdf, pptx, docx, html, md, txt. **Do not read the output** — note the word count the
script prints and pass the path on. Subagents read it.

Check the word count for plausibility (a near-empty extraction means a scanned PDF needing OCR,
which the script says outright). For a long source, pass `--pages` so each generator later
receives only the pages its facts live on; on a 40-page deck that trimming saves more than
batch size does.

If the script can't run at all — no shell/Bash tool, or a missing dependency like
`pypdf` in a sandboxed environment (e.g. this skill uploaded to claude.ai's Chat tab,
not the Code tab) — read the source file directly instead of blocking on the script. On that
surface you are also the generator; see the fallback note in step 3.

**Then state the plan before spending anything:** N, batch count, the three models, and
expected spawns (1 inventory + `ceil(N/5)` generators + 2 judges for round 1). Above N=8, say
that cost grows faster than linearly — more questions means more round-1 failures, each dragging
another round — and offer to split delivery into two runs. Then do what was asked.

### 2. Inventory the facts — delegate it

Spawn **one Sonnet subagent** to read the extracted source and write `facts.md`: the discrete
facts the source teaches, where each appears, **pre-grouped under `## Batch 1`, `## Batch 2`…
headings, one group per `ceil(N/5)` batches, with no fact in two groups.** Chaining is what
makes a question third order, and you cannot chain what you have not enumerated.

Tell it to report back only: total facts found, and the batch count it wrote. Ask it to say so
explicitly if the source supports fewer than N questions — **N questions need roughly 3N
chainable facts.** A 7-page PDF often will not support 15 third-order questions; if it reports
thin material, cap N and tell the user. Never pad with recall questions.

Grouping belongs here, not with you: the agent that enumerated the facts knows which ones chain
together, and doing it here means the fact list never enters your context. Disjoint groups are
what stop two batches building the same concept.

### 3. Spawn the generators

Spawn one Sonnet subagent per batch, **all in one message so they run in parallel.** Each one
writes its questions to its own file — `batch1.md`, `batch2.md`, … — and returns **only its
answer key** (`Q1: D, Q2: B, …`) and a one-line note on anything it couldn't build. Question
text goes to disk, not through you.

Each generator prompt must be self-contained. Invariant material first, so the spawns share a
cacheable prefix:

1. the writing rules from step 4 below, **pasted verbatim** (plus the relevant parts of
   `references/question-anatomy.md`)
2. the chain-first instruction and output format below
3. `Read /tmp/source.txt for the source material. Read facts.md and use ONLY the facts under
   the "## Batch N" heading you are given — the other batches belong to other agents.`
4. `Read only the two files named above. Do not invoke the study-question-generator skill and
   do not read any of its files — this prompt plus those files are everything you need.` — a
   generator that loads the skill re-reads ~5,600 tokens of rules on every batch spawn, which
   is much of what batching just saved
5. *then* the variable part: its batch number, its output filename, and a target
   answer-position spread for its batch so the merged set doesn't cluster on a letter

Every generator writes the chain **before** any prose:

```
Q3: patient given epinephrine → no response
  → epinephrine signals via a second messenger
  → that messenger is cAMP
  → answer: cAMP  (3 hops)
```

**≤2 hops is not third order** — extend or drop it. Then write the vignette *backwards*
from the chain, removing every bridging fact. **The chain is scratch work — it must not appear
in the batch file**, which is student-facing (step 6 gates this).

Then merge with a shell command, not by reading the batches:

```bash
cat batch*.md > questions.md
```

*Fallback:* on a surface with no subagents (claude.ai's Chat tab), you are the generator and the
inventory agent — do steps 2–4 yourself in one context and expect the cost this whole structure
exists to avoid. Keeping N small is the only lever there.

### 4. The rules the generators write to

**Read `references/question-anatomy.md`** — the rubric, the reusable patterns, and the
distractor taxonomy. The four non-negotiables, which go into every generator prompt:

- **Stem:** vignette; observations only; the answer term and its category absent; one
  question; no meta-language. **It rules nothing out** — strike any
  `normal`/`identical`/`unaffected` clause the mechanism doesn't need.
- **Options:** 4–5 from **one closed source category**, in the source's own vocabulary,
  identical grammatical form, same level of generality. **Default to an enumerated label set
  with no descriptive content** (`TFIID…TFIIH`, `Asn/Gln/Ser/Thr/Tyr`) — nothing to cue on, a
  1.00 length ratio, and a whole class of blind-cue failures gone before it can happen. Prose
  options need a reason.
- **Every distractor a true source fact** that answers a neighboring question. Longest
  ≤ ~1.3× shortest, no `because`/`since`/`due to`, vary the correct position.
- **No semantic echo:** the key must not paraphrase the stem. `barrel-shaped` → `cavity` and
  `add and remove` → `adjusting` were each picked blind despite sharing no words.

Resolve ambiguity in the options, never by narrating exclusions in the stem.

Then pre-screen the **merged** set mechanically, before spending judge tokens:

```bash
python3 scripts/check_mechanics.py questions.md --key C,A,D,B,C --source /tmp/source.txt
```

**This is a gate, not a report.** It exits non-zero on failure — fix what it names and re-run
until it exits 0 *before* spawning any judge. A judge round costs thousands of tokens to find
what this finds in milliseconds for free. Re-run it on the **whole set** after every edit,
including every rewrite round in step 5: it re-checks parity, absolutes and answer-position
clustering across all questions, which is what makes the scoped re-judging in step 5 safe and
what catches clustering introduced by merging independent batches.

**Fixing is delegated too.** Send the script's output verbatim, plus the path to `questions.md`,
to a Sonnet subagent and have it edit the file in place — you never open the file. Its output is
already precise about what is wrong and where (`option C uses wording the source never does:
Interfering`), so the fixing agent needs the failure text and nothing else. Re-run the script
yourself afterwards; the exit code is the only thing you need back.

**Always pass `--source`.** It adds option-vocabulary grounding: any option naming a concept in
words the source never uses is caught here for free instead of coming back from gate 2 as
`source_sufficient: false` — and those are the most expensive rewrites there are, the ones that
collapse hop count and burn the 3-round cap. A missing option word means *rename it the
source's way*, never pad or truncate a source-verbatim name to satisfy the checker.

It skips length checks on enumerated-label sets (all options ≤12 chars) and prints a note
saying so — a ratio over 3-character acronyms is noise. Every skipped check announces itself,
including the ones skipped for a missing `--source`. Semantic echo and hop count are invisible
to it; that is what the judge is for.

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

Read `references/judge-protocol.md` and run all three gates via subagents, **never on the
model that wrote the questions**. Gate 1 → Haiku, gates 2+3 → Opus, generators → Sonnet; pass
`model` explicitly every time.

1. **Blind-cue gate** (`model: haiku`) — judge sees questions with *no source*, uses only
   test-taking heuristics. FAIL only when the blind guess **matches the key** *and* a real
   surface cue is named. A named cue on a *wrong* guess is a PASS — do not rewrite it. Haiku is
   right here precisely because the gate forbids domain reasoning.
2. **Answerability gate** (`model: opus`) — separate agent, *with* source, must pick the keyed
   answer, reconstruct the chain, and quote the source. Needs a capable model: a judge that
   fails a hard question for lack of capability reads as a false question defect.
3. **Order audit** — hop count ≥3, answer absent from stem, distractors clean. Run this in
   the **same agent as gate 2**, which already has the source loaded.

**Spawn gate 1 and the gate-2/3 agent in one message, in parallel.** Nothing reads gate 1's
output before gates 2+3 run, so sequencing them only doubles wall clock.

**Judges read the files; you don't paste the questions in.** Tell gate 1 to read `questions.md`
(never the source, never the key) and the gate-2/3 agent to read `questions.md` and
`/tmp/source.txt`. Both return JSON verdicts — that JSON is all you hold. Interpolating the set
into each prompt would route every question back through your context, which is what step 3's
file handoff avoided.

Gates 1 and 2 must be **separate agents**: one that has read the source cannot do a
credible blind pass. Gate 3 sharing gate 2's agent is fine — both are sourced passes.

**Judge the pooled set, never per batch.** Gates 2+3 would otherwise re-send the whole source
once per batch, and gate 1's set-wide hit-rate check would run over 5 questions instead of N,
which is too small to mean anything.

**The rewrite loop — two judge agents per round, and it stops.** A set that costs 24 spawns
instead of 4 is not more validated, just slower and more expensive.

| Round | What gets judged | Cost |
|---|---|---|
| 1 | The full set — gate 1's set-wide hit-rate check needs it | 2 spawns, in parallel (gate 1; gates 2+3 share one) |
| 2+ | **Only the questions that failed.** Never re-judge one that passed | 2 spawns, tiny payload |
| after every edit | `check_mechanics.py --source` on the **whole set** — parity, absolutes, clustering, grounding | free |
| a round comes back clean | **stop.** No confirmation round | — |

**Rewrites go to parallel Sonnet subagents, one per failing question** — not into your own
context, which would pull the whole set back into the expensive place. Give each one the path to
`questions.md`, the question number, the source path, and the specific failure reason from the
judge's JSON; it edits that question in place. You hold question numbers and reasons, never
question text.

**Cap at 3 rewrite rounds per question** — count them out loud, per question. At the cap,
replace the concept or report the question unresolved; never silently drop it.

Pass `references/judge-protocol.md`'s prompts to the judge verbatim; they are self-contained,
so tell each judge — and each generator — **not** to load this skill or its reference files.

### 6. Deliver

`questions.md` already exists. **Delegate writing `answers.md`** to a Sonnet subagent: give it
the paths to `questions.md` and `/tmp/source.txt`, the final key, and **gate 2's `source_quotes`
JSON**, which already contains a quoted source passage per hop. Assembling a key from those
quotes is transcription, not judgment — and it is the last place the whole set would otherwise
pass through your context.

Then gate both files. These two commands are what replace reading them yourself:

```bash
python3 scripts/check_mechanics.py questions.md --key C,A,D,B,C --assert-no-answers
python3 scripts/check_mechanics.py questions.md --key C,A,D,B,C \
    --source /tmp/source.txt --answers answers.md
```

The first fails if `questions.md` contains an answer line, a rationale, a hop count, or the chain
arrows a generator used as scratch work. The second fails on a fabricated quote or one attributed
to the wrong page. Both must exit 0 before you hand anything over; if either fails, send its
output to a Sonnet subagent to fix in place and re-run.

Then render:

```bash
python3 scripts/render_output.py questions.md --footer "Source: lecture.pdf"
python3 scripts/render_output.py answers.md   --footer "Source: lecture.pdf"
```

- `questions.md` → **no answers anywhere** — which `--assert-no-answers` above is what
  guarantees, since you never read the file
- `answers.md` → correct option, the full reasoning chain, and why each distractor is
  wrong — **with a source citation on every hop and every distractor** (slide/page number
  plus the source's own words). Gate 2 already quoted the source for each link; carry those
  quotes into the key instead of discarding them. An uncited key can't be checked by the
  student and hides the moment a hop drifted into outside knowledge — which is why `--answers`
  is a gate. Do not hand-check what it checks.
- A question that failed a gate ships with that failure marked **on the question itself**
  in the key, not only in the chat report — the file outlives the conversation.
- If step 5 ran the same-model fallback instead of the cross-model harness, say so at the
  top of `answers.md`: *"⚠️ Validated by same-model self-critique only — no cross-model
  judge was available in this environment. Treat pass results with less confidence than a
  Claude Code run."*

HTML is self-contained and prints to PDF from any browser (Cmd+P) — no Word or LaTeX
needed. Add `--docx` if the recipient wants to edit in Word.

Report: generator model, gate-1 model, gate-2/3 model (or "same-model fallback" if that's what
ran), N requested vs N passing, blind hit rate vs chance, **generator and judge spawns used,
rewrite rounds per question**, and anything unresolved.

## Red flags — stop and fix

| Red flag | Fix |
|---|---|
| Correct option is longest, or the only one explaining itself; any option has `because`/`since`/`due to` | Equalize length; rationale belongs in the key |
| A distractor is absurd ("Magnets") or absolute ("no effect") | Replace with a true source fact from a neighboring step |
| Stem states the mechanism, names the answer's category, or says a step is `normal`/`identical`/`unaffected` | Observations only. That clause is an elimination path for guessers |
| "The stem needs that clause or the answer is ambiguous" | Fix the options instead — a homogeneous set is unambiguous without exclusions |
| Options span categories, use a synonym the source never uses, or mix one general capability with three specific acts | Redraw from one closed category, in the source's words, at one level of generality |
| You wrote the questions yourself instead of spawning generator subagents | The generating context is the largest cost in a run. Orchestrate: slice the inventory, spawn Sonnet batches, merge |
| You rewrote a failing question in your own context | Same reason. One Sonnet subagent per failing question, in parallel |
| Generator or judge spawned without an explicit `model` | It inherits the session model — the generator silently becomes Opus, or the judge silently becomes the generator's model |
| Generator prompt didn't include the writing rules, or pointed at `question-anatomy.md` instead | Paste them. A generator that loads the skill re-reads ~5,600 tokens per batch |
| Batches judged separately | Judge the pooled set: per-batch judging re-sends the source per batch and makes gate 1's set-wide check meaningless |
| Two batches given overlapping fact slices | Disjoint slices only, or you pay a judge round to find duplicate concepts |
| `check_mechanics.py` run without `--source` | Option-vocabulary grounding is skipped, and gate 2 pays for it with the most expensive class of rewrite |
| Gate 1 and gates 2+3 spawned sequentially | Spawn both in one message. Nothing reads gate 1's output until the consolidated verdict |
| The correct option restates the stem in different words | Rewrite in the source's vocabulary — semantic echo is invisible to `check_mechanics.py` |
| Stem paraphrases an abbreviation the source never expands (`HATs` → "add acetyl groups") | Use the source's own phrase; expanding it silently imports outside knowledge |
| Chain is ≤2 hops | Extend the chain, or drop the question |
| With the options covered, a reader who knows the source can't produce the answer | The option list is carrying the question. Rewrite the stem to stand alone |
| Hop count dropped after you fixed grounding | The removed synonym *was* the third hop — change concepts, don't restore it |
| Third rewrite still fails | Replace the concept. Some option sets are permanently cued (five transcript parts = two pairs + one odd) |
| Wrote the stem before the chain | Chain first, vignette backwards from it |
| Source too thin for N | Cap N and say so; never pad with recall questions |
| "Questions look good, skip the judge" | Run all three gates. Not optional |
| Rewriting a question because the blind judge named a cue, though its guess was wrong | That's a PASS. Rewriting it makes the question worse for nothing |
| Judge spawned without being told to skip the skill | It will load generation rules it never uses. The gate prompts are self-contained |
| One agent runs **gate 1 and gate 2** | Gate 1 must be its own agent with no source; gates 2 and 3 share one by design |
| Answer key hand-checked against the source instead of with `--answers` | The script names fabricated quotes and wrong-page attributions for free |
| Failures quietly dropped so the set looks clean | Report pass rate and every failure |
| Answer key states a chain with no citation | Cite the slide/page and quote the source per hop — Gate 2 produced those quotes already |
| A gate failure is mentioned only in chat | Mark it in the key too; the student reads the file, not the transcript |
| Same-model fallback used when a cross-model subagent was actually available | Never take the weaker path as a shortcut; use it only when the environment genuinely can't spawn a different-model subagent |
| Fallback ran but the key doesn't disclose it | State it at the top of `answers.md`, not only in chat |
