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

Three gates, each a separate subagent on a **different model** than the one that wrote the
questions — a model grading its own questions reconstructs the reasoning it just used and
mistakes that fluency for quality. Model pairing: Opus generates → judge with Sonnet;
Sonnet generates → judge with Opus; Haiku never judges the answerability gate, since a
capability gap there reads as a false question defect.

1. **Blind-cue gate** — judge sees the questions with _no source material_ and may use only
   test-taking heuristics. If it finds the keyed answer and can name the surface cue, the
   question fails and gets rewritten.
2. **Answerability gate** — a separate agent, _with_ the source, must pick the keyed
   answer, reconstruct the reasoning chain, and quote the source passage for each link.
3. **Order audit** — hop count ≥3, answer term absent from the stem, the stem answerable on
   its own once the options are covered, every distractor a true source fact.

Gates 1 and 2 must be different agents: one that has read the source cannot perform a
credible blind pass. Gate 3 runs as a second turn in the gate-2 agent, which already has the
source loaded — two spawns per round, not three.

**Cost.** Judge spawns are what this skill spends, so the loop is scoped: round 1 judges the
full set, later rounds judge only the questions that failed, a clean round ends the loop, and
each question is capped at 3 rewrite rounds. The free `check_mechanics.py` screen has to pass
before any judge is spawned, and it re-checks the whole set — parity, absolutes, answer-position
clustering — after every edit. Those checks live only in the script: the judge prompts
deliberately don't re-ask for them, since a judge re-deriving a threshold the script already
enforced can only disagree with it, and every disagreement costs a rewrite round. Each run
reports the spawns it used.

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
- `answers.md` — the correct option, the full reasoning chain, and why every distractor is
  wrong, **with a source citation on every hop and every distractor**: the page or slide
  number plus the source's own words. The answerability gate already quotes the source for
  each link; those quotes carry through into the key instead of being discarded, so a
  student (or anyone auditing the key) can check every claim against the original material.
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
    check_mechanics.py          pre-judge screen: parity, absolutes, answer clustering
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
