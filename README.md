# study-question-generator

A Claude Code skill that turns study material — PDF, PowerPoint, article, lecture notes —
into third-order practice questions validated to be unanswerable by guessing alone.

## Why

Most auto-generated practice questions are answerable without reading the material. The
correct option is the longest one, or the only one that explains itself, or the only one
that isn't absurd. A student who is good at test-taking and knows nothing scores well,
which means the question measured nothing.

This skill's rules were derived by analyzing a real lecture deck for exactly these tells,
then validated against two independent decks with a cross-model judge harness that catches
guessable questions before they reach a student. The rules themselves apply to any subject.

## Install

One line, in a terminal. Mac/Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/KunalShah21/study-question-generator/main/install.sh | bash
```

Windows, in PowerShell:

```powershell
irm https://raw.githubusercontent.com/KunalShah21/study-question-generator/main/install.ps1 | iex
```

It installs into `~/.claude/skills/` (`%USERPROFILE%\.claude\skills\` on Windows), checks
that Python 3.9+ is present, tells you which optional extras you're missing and what each
one costs, and runs a smoke test. Then open Claude Code and type
`/study-question-generator`, or just ask for practice questions from a file.

Piping a script from the internet into your shell deserves a look first — it's
[install.sh](install.sh) / [install.ps1](install.ps1), and `--help`, `--dry-run`, `--link`,
`--copy` and `--zip` are all there.

<details>
<summary>Using git, or installing by hand</summary>

Clone it and the installer symlinks instead of copying, so `git pull` updates the skill:

```bash
git clone https://github.com/KunalShah21/study-question-generator.git
cd study-question-generator && ./install.sh
```

Or skip the script entirely: on this repo's GitHub page hit **Code → Download ZIP**, unzip,
and move the `skills/study-question-generator` folder into `~/.claude/skills/` (Mac/Linux)
or `%USERPROFILE%\.claude\skills\` (Windows).

</details>

<details>
<summary>No Claude Code? Use claude.ai's Chat tab (weaker validation)</summary>

Requires a Pro, Max, Team, or Enterprise plan with code execution enabled.

1. `./install.sh --zip` builds `study-question-generator.zip` with the folder at the zip
   root, which is the layout the uploader wants. (By hand: zip up just the
   `study-question-generator` folder, not the whole repo.)
2. **Settings → Features → Skills** on claude.ai, and upload that zip.
3. Ask Claude for practice questions from a document you upload.

> ⚠️ This surface can't hand validation to a separate model, so it self-critiques
> instead — weaker, and disclosed in the delivered answer key. Use Claude Code when you can.

</details>

## Usage

```
/study-question-generator ~/Downloads/lecture.pdf --n 10
```

The skill will ask for anything it needs. Point it at the content sections and exclude a
deck's own practice problems, or it will produce near-copies of them:

```
/study-question-generator lecture.pdf --n 10 --pages 5-8,17-18
```

## What "third order" means

Order is measured in **inference hops**: distinct facts a student must retrieve and chain.

| Order   | Example                                                                                                             |
| ------- | ------------------------------------------------------------------------------------------------------------------- |
| 1st     | "Which polymerase synthesizes rRNA?" — one lookup                                                                   |
| 2nd     | Stem states that acetylation reduces histone charge; predict the effect on DNA binding — one applied relationship   |
| **3rd** | Patient's heart rate crashes, epinephrine produces no response, labs show a nucleotide disorder — which nucleotide? |

The third-order example (one worked case, not a domain requirement) never says _cAMP_,
_second messenger_, or _signal transduction_. The student must supply the bridging
mechanism. That absence is the whole design.

## The judge harness

Three gates, each a separate subagent, and **never on the model that wrote the questions** — a
model grading its own questions reconstructs the reasoning it just used and mistakes that
fluency for quality.

1. **Blind-cue gate** (Haiku 4.5) — judge sees the questions with _no source material_ and may
   use only test-taking heuristics. If it finds the keyed answer and can name the surface cue,
   the question fails and gets rewritten. The cheapest model does this one identically, because
   the gate forbids reasoning about the subject at all.
2. **Answerability gate** (Opus 5) — a separate agent, _with_ the source, must pick the keyed
   answer, reconstruct the reasoning chain, and quote the source passage for each link. This one
   needs a capable model: a judge that fails a hard question for lack of capability reads as a
   false question defect.
3. **Order audit** (same agent as gate 2) — hop count ≥3, answer term absent from the stem, the
   stem answerable on its own once the options are covered, every distractor a true source fact.

Gates 1 and 2 must be different agents: one that has read the source cannot perform a
credible blind pass. Gate 3 runs as a second turn in the gate-2 agent, which already has the
source loaded — two spawns per round, not three — and the two agents are spawned in parallel,
since nothing reads gate 1's output until the verdicts are combined.

Each judge is given **file paths and reads them itself** — gate 1 the question file only, gates
2+3 the questions and the source. The question set is never pasted into a prompt, which is what
keeps it out of the orchestrating session's context (see **Cost** below).

**Cost.** The dominant cost of a run is not the judges: it's writing the questions. Written
turn-by-turn in one conversation, every new question is drafted with the source, the fact
inventory, and all previous questions in context, so cost grows roughly quadratically in the
number of questions.

So the main session orchestrates and **moves file paths rather than content**. The extracted
source, the fact inventory, and the question text never enter it: extraction and merging are
shell commands, the fact inventory is written to a file by its own Sonnet subagent, questions are
written to one file per batch by **parallel Sonnet subagents of ~5 questions each**, and the
judges are handed paths to read. What the orchestrator holds is paths, JSON verdicts, and exit
codes. Judging stays pooled over the whole set, which keeps the source read once and keeps the
blind gate's set-wide check statistically meaningful.

That has a consequence worth being explicit about: **nobody looks at the set before it ships.**
So the two things a human would have caught by eye are mechanical gates instead —
`--assert-no-answers` fails the run if the student-facing file contains an answer, a rationale,
or the chain scaffolding a generator drafted with, and `--answers` fails it on a fabricated or
misattributed quote in the key. Neither is a report; both exit non-zero.

The judge loop is scoped on top of that: round 1 judges the full set, later rounds judge only
the questions that failed, a clean round ends the loop, each question is capped at 3 rewrite
rounds, and rewrites go to parallel Sonnet subagents rather than back into the orchestrator's
context. The free `check_mechanics.py` screen has to pass before any judge is spawned, and it
re-checks the whole set — parity, absolutes, answer-position clustering, and option vocabulary
against the source — after every edit. Those checks live only in the script: the judge prompts
deliberately don't re-ask for them, since a judge re-deriving a threshold the script already
enforced can only disagree with it, and every disagreement costs a rewrite round. Each run
reports the spawns it used and the rewrite rounds per question.

One caveat the protocol is explicit about: a frontier model cannot fully suppress what it
knows, so the blind judge will sometimes answer from domain knowledge and back-fill a
plausible-sounding "cue." Only treat a cue as real if a reader with zero subject knowledge
could have seen it — the judge is asked to report `used_domain_knowledge` for that reason.

A cue on its own is also not a failure: the guess has to actually **land on the keyed answer**.
In one real run the blind judge named a surface cue on 8 of 10 questions — "longest option",
"only one containing a digit" — and only one of those guesses was right. The other seven were
cues that led nowhere, and rewriting those questions would have made them worse. Failures get up
to 3 rewrite-and-regate rounds before being reported unresolved rather than silently dropped.

## Output & citations

Delivery is two Markdown files, each rendered to self-contained HTML that prints to PDF
from any browser (Cmd+P / Ctrl+P) — no Word or LaTeX required. Pass `--docx` if the
recipient wants to edit in Word.

- `questions.md` — the vignette and options only, **no answers anywhere**.
  `check_mechanics.py --assert-no-answers` enforces that before delivery: an answer line, a
  heading ending in an answer letter, a rationale section, a hop count, or a leftover chain
  arrow fails the run and names the line it's on.
- `answers.md` — the correct option, the full reasoning chain, and why every distractor is
  wrong, **with a source citation on every hop and every distractor**: the page or slide
  number plus the source's own words. The answerability gate already quotes the source for
  each link; those quotes carry through into the key instead of being discarded, so a
  student (or anyone auditing the key) can check every claim against the original material.
  `check_mechanics.py --answers` verifies them before delivery: a quote that isn't in the
  source, or is attributed to the wrong page, fails the run.
- A question that fails a gate ships with that failure marked **on the question itself** in
  the key, not only reported in chat — the file outlives the conversation.

## Layout

```
skills/study-question-generator/
  SKILL.md                      workflow + anti-guessability rules
  references/
    question-anatomy.md         order rubric, patterns, distractor taxonomy
    judge-protocol.md           judge prompts, gates, verdict shape
  scripts/
    extract_source.py           pdf/pptx/docx/html/md → text, with page filter
    check_mechanics.py          pre-judge screen: parity, absolutes, answer clustering,
                                option vocabulary vs source. Also the delivery gates:
                                answer-key citations, and answer leaks in the question file
    render_output.py            md → print-ready HTML (+ docx via pandoc)
```

`extract_source.py` needs `pypdf` for PDFs; PPTX is parsed with the standard library.
`render_output.py` needs nothing for HTML, and pandoc only for `--docx`.

## Contributing

This is meant to be a small, readable skill anyone can pick up and point at their own
material — a lecture, an article, a textbook chapter. If you try it and the judge harness
lets a guessable question through, that's exactly the kind of counter-example this project
wants: open an issue with the question and the cue a blind reader used. PRs that tighten
`question-anatomy.md` or `judge-protocol.md` with a new finding are welcome. See
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for how the current rules were derived.

## License

MIT — see [LICENSE](LICENSE).
