# study-question-generator

A Claude Code skill that turns study material — PDF, PowerPoint, article, lecture notes —
into third-order practice questions, then validates them with a cross-model judge before
delivery.

## Why

Most auto-generated practice questions are answerable without reading the material. The
correct option is the longest one, or the only one that explains itself, or the only one
that isn't absurd. A student who is good at test-taking and knows nothing scores well,
which means the question measured nothing.

This skill is built against that failure. Its rules come from analyzing a real medical
school review deck, and its judge harness exists to catch guessable questions before they
reach a student.

## Install

```bash
git clone <this repo> && cd study-question-generator
ln -s "$PWD/skills/study-question-generator" ~/.claude/skills/study-question-generator
```

Then in Claude Code: `/study-question-generator` — or just ask naturally
("make me 10 practice questions from this lecture").

## Usage

```
/study-question-generator ~/Downloads/lecture.pdf --n 10
```

The skill will ask for anything it needs. Point it at the content sections and exclude a
deck's own practice problems, or it will produce near-copies of them:

```
/study-question-generator lecture.pdf --n 10 --pages 5-8,17-18
```

Output is two files — questions (no answers) and an answer key with the full reasoning
chain per question — rendered to self-contained HTML that prints to PDF from any browser.
No Word or LaTeX required. `--docx` if the recipient wants to edit in Word.

## What "third order" means

Order is measured in **inference hops**: distinct facts a student must retrieve and chain.

| Order | Example |
|---|---|
| 1st | "Which polymerase synthesizes rRNA?" — one lookup |
| 2nd | Stem states that acetylation reduces histone charge; predict the effect on DNA binding — one applied relationship |
| **3rd** | Patient's heart rate crashes, epinephrine produces no response, labs show a nucleotide disorder — which nucleotide? |

The third-order example never says *cAMP*, *second messenger*, or *signal transduction*.
The student must supply the bridging mechanism. That absence is the whole design.

## The judge harness

Three gates, each a separate subagent on a **different model** than the one that wrote the
questions. A model grading its own questions reconstructs the reasoning it just used and
mistakes that fluency for quality.

1. **Blind-cue gate** — judge sees the questions with *no source material* and may use only
   test-taking heuristics. If it finds the keyed answer and can name the surface cue, the
   question fails and gets rewritten.
2. **Answerability gate** — a separate agent, *with* the source, must pick the keyed
   answer, reconstruct the reasoning chain, and quote the source passage for each link.
3. **Order audit** — hop count ≥3, answer term absent from the stem, every distractor a
   true source fact, option length parity.

Gates 1 and 2 must be different agents: one that has read the source cannot perform a
credible blind pass.

## Development

Built test-first, per the `writing-skills` discipline. The baseline (RED) run generated
questions with no skill present, then a second, independent agent took them blind — no
source, no domain reasoning, surface heuristics only.

**It scored 5/5.** Its own explanations named the tells: *"only option that gives a
mechanism," "by far the longest and most detailed," "others are short flat denials, each
contains an absolute word."*

Those six failure modes are what the skill's rules encode against:

| # | Failure |
|---|---|
| F1 | Correct option longest / only one with a mechanism |
| F2 | Stem hands over the reasoning |
| F3 | "Predict X and why" bloats the correct option |
| F4 | Distractors self-refute via absolutes |
| F5 | Meta-language leaks into student-facing text |
| F6 | No vignette framing |

## Layout

```
skills/study-question-generator/
  SKILL.md                      workflow + anti-guessability rules
  references/
    question-anatomy.md         order rubric, patterns, distractor taxonomy
    judge-protocol.md           judge prompts, gates, verdict shape
  scripts/
    extract_source.py           pdf/pptx/docx/html/md → text, with page filter
    render_output.py            md → print-ready HTML (+ docx via pandoc)
```

`extract_source.py` needs `pypdf` for PDFs; PPTX is parsed with the standard library.
`render_output.py` needs nothing for HTML, and pandoc only for `--docx`.
