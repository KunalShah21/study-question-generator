#!/usr/bin/env python3
"""Mechanical pre-check for a question set. Run before spending judge tokens.

Catches the option-level defects that are cheap to detect with string rules:
length disparity, reasoning words inside options, the correct answer being the
longest, answer-position clustering, and answer terms leaking into the stem.

With --source it also checks two things that otherwise cost a paid judge round:

  * Option vocabulary grounding. Every option must name its concept in the
    source's own words. A set drawn from the right category still fails gate 2
    with source_sufficient: false when it renames a member — the source said
    "mi/siRNA" and the option said "Interfering transcripts". Those rewrites are
    the expensive kind: they collapse hop count and burn the 3-round cap.
    Checked on options only. Stems are *supposed* to describe a vignette in
    fresh words, so scanning them would flag every good question.
  * Citation verification (with --answers). SKILL.md requires every hop and
    distractor in the key to carry a page/slide citation quoting the source, and
    requires it verified mechanically. This is that verification.

Judgment-dependent checks (hop count, semantic echo, whether a distractor is a
true source fact, whether two options are both defensible) still require the
judge gates in references/judge-protocol.md. This script does not replace them.

Length checks are skipped on enumerated-label sets (see MIN_LENGTH_FOR_RATIO) —
a ratio computed over 3- and 4-character acronyms is noise, and flagging it
trains readers to ignore the whole script. Skips are printed, never silent, and
so is every check skipped for a missing --source or --answers.

--assert-no-answers is the delivery gate for questions.md: it fails if the
student-facing file contains an answer marker, a rationale, or the chain
scaffolding generators write while drafting. The orchestrator hands questions
between subagents as file paths and never reads the set itself, so "check it by
eye before delivering" is no longer available — this is that check.

Options may be written "A. text", "A) text", or bulleted "- A. text"; the
grammar matches render_output.py's so a file that renders also checks.

Usage:
    check_mechanics.py questions.md --key C,B,B,D,C
    check_mechanics.py questions.md --key key.json
    check_mechanics.py questions.md --key C,B,B,D,C --source /tmp/source.txt
    check_mechanics.py questions.md --key C,B,B,D,C --source /tmp/source.txt \\
        --answers answers.md
    check_mechanics.py questions.md --key C,B,B,D,C --assert-no-answers

Exit status is 1 if any check fails, so it can gate a pipeline.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

# Words that smuggle justification into an option.
REASON_WORDS = re.compile(
    r"\b(because|since|due to|therefore|thus|which leads to|resulting in|"
    r"so that|as a result)\b",
    re.I,
)
# Absolutes that mark an option as a throwaway.
ABSOLUTES = re.compile(
    r"\b(never|always|no effect|entirely|completely unrelated|none of|"
    r"interchangeable|nothing)\b",
    re.I,
)
# "A. text" / "A) text" / "- A. text". Kept in step with render_output.py's
# OPTION_RE: a set that renders must also be checkable, or the free screen gets
# skipped and its defects reach the judge instead.
OPTION_LINE = re.compile(r"^[ \t]*(?:[-*+][ \t]+)?([A-J])[.)][ \t]+(.+?)[ \t]*$", re.M)

MAX_LENGTH_RATIO = 1.35
# Below this, a length ratio is noise. The best option sets are enumerated labels
# (BER/MMR/HR/NER, TFIID…TFIIH) where BER vs NHEJ is a "1.33 ratio" that no
# test-taker can act on — and question-anatomy.md recommends exactly those sets.
# Flagging them trained readers to ignore this script, which is how real defects
# ended up costing judge rounds.
MIN_LENGTH_FOR_RATIO = 12

# Page/slide banners emitted by extract_source.py. Kept in step with the f-strings
# there ("--- page {i} ---", "--- slide {i} ---") so citations can be checked
# against the page they claim.
MARKER_RE = re.compile(r"^-{3}\s*(?:page|slide)\s+(\d+)\s*-{3}\s*$", re.M | re.I)
# A quoted passage in the answer key. Straight or curly, and long enough that a
# stray quoted word is not treated as a citation.
QUOTE_RE = re.compile(r"[\"“]([^\"“”]{12,})[\"”]")
CITATION_RE = re.compile(r"\b(?:page|slide|pg?\.)\s*(\d+)", re.I)
# Generic English that carries no domain meaning. Without this, grounding flags
# "increased" or "following" — noise, and this script's whole value is that its
# failures are worth acting on.
#
# The list is deliberately generous, including generic effect/process nouns
# (disruption, formation, impairment). A source saying a ring "prevents" a
# conformation while the option says "disruption" is a wording difference no
# sourced judge fails on, and the asymmetry matters: a false positive here costs
# a rewrite round chasing nothing, while a false negative costs nothing at all —
# gate 2 still runs. Domain nouns are what this check exists to catch, and
# derivational forms of words the source *does* use already pass via the suffix
# trimming in ungrounded_words().
COMMON_WORDS = frozenset("""
accumulation activation blocked breakdown building degradation depletion
disrupt disrupted disrupting disruption disrupts elongation formation
impairment inhibition interaction loosened production prevented prevents
release stability tightened unstable
""".split()) | frozenset("""
absence achieved addition additional affected altered although amount another
appears applied approach approximately assays association available becomes
before begins behavior between binding briefly cannot causes changes commonly
compared complete condition considered contains continues correct decrease
decreased decreases despite develops different directly disorder disrupted
during effect effects either elevated enhanced entirely equally established
eventually evidence example expected experiment experiments explains failure
finding findings follows following formation friction function functional
functions further gathered general greater higher however impact impaired
important improved include includes including increase increased increases
indicates instead interaction internal involved involves largely leading
levels likely limited located longer lowered maintained marked measured
mechanism minutes moderate multiple nearly necessary normal noted notes
observed obtained occurring occurs original outside particular partially
patient patients pattern performed perhaps period possible potential
precisely presence present presents prevented previous primarily probably
process processes produce produced produces product progress prompted
provided rapidly reduced reduces reduction related relative remains removed
repeated reported requires resistant respond response responsible resulting
results returned reveals revealed sample second section separate sequence
several severe shortly showed shows significant similar single slightly
smaller specific started statement stated states studies subject sudden
sufficient suggest suggests support supported symptoms therapy through
together toward treated treatment typical typically unable unchanged
underlying unrelated usually various without
""".split())
MIN_GROUNDING_WORD = 6
# Shortest stem we will accept when testing an inflected form. "transcripts"
# should match a source that writes "transcript"; trimming below five characters
# starts matching unrelated words.
MIN_STEM_LEN = 5

# Answer-key tells that must never appear in the student-facing file. Generators
# draft a chain before the prose (SKILL.md step 3) and a batch that ships its
# scratch work leaks the answer, so the chain arrows are here too.
ANSWER_LEAK = [
    (re.compile(r"^\s*(?:answer|correct answer|key)\s*[:\-–—]", re.I | re.M),
     "an answer line"),
    (re.compile(r"^\s*##.*\s[-–—]\s*[A-J]\s*$", re.M),
     "a heading ending in an answer letter"),
    (re.compile(r"\*\*?(?:answer|correct)\*\*?\s*[:\-–—]?\s*[A-J]\b", re.I),
     "a bolded answer"),
    (re.compile(r"^\s*(?:rationale|explanation|why\s+(?:the\s+)?(?:others?|"
                r"distractors?)\b)", re.I | re.M),
     "a rationale section"),
    (re.compile(r"\((?:\d+\s*hops?|hop\s*count\b)", re.I), "a hop count"),
    (re.compile(r"^\s*(?:→|->)", re.M), "chain scaffolding"),
    (re.compile(r"\bsource_sufficient\b|\bblind_guess\b|\bverdict\b", re.I),
     "judge JSON"),
    (re.compile(r"^\s*(?:page|slide)\s+\d+\s*[:\-–—]", re.I | re.M),
     "a source citation (those belong in answers.md)"),
]


def parse_key(spec: str, n_questions: int) -> dict[int, str]:
    path = Path(spec)
    if path.exists():
        data = json.loads(path.read_text())
        if isinstance(data, dict):
            key = {int(k): v.strip().upper() for k, v in data.items()}
        else:
            key = {i: str(v).strip().upper() for i, v in enumerate(data, start=1)}
    else:
        letters = [s.strip().upper() for s in spec.split(",") if s.strip()]
        key = {i: l for i, l in enumerate(letters, start=1)}
    # Checked on both paths: a short JSON key would otherwise degrade to a
    # per-question "no key entry" instead of naming the actual mistake.
    if len(key) != n_questions:
        raise SystemExit(
            f"--key has {len(key)} answers but found {n_questions} questions"
        )
    return key


def split_questions(text: str) -> list[tuple[str, str]]:
    """Return (heading, body) per '## ' section that contains options."""
    chunks = re.split(r"^##\s+", text, flags=re.M)[1:]
    out = []
    for chunk in chunks:
        heading, _, body = chunk.partition("\n")
        if OPTION_LINE.search(body):
            out.append((heading.strip(), body))
    return out


def split_by_marker(text: str) -> dict[int, str]:
    """Map page/slide number -> that page's text, using extract_source.py markers.

    Pages accumulate rather than overwrite: a multi-file extraction can repeat
    "--- page 1 ---" once per source, and dropping the earlier one would report a
    real quote as fabricated.
    """
    pages: dict[int, str] = {}
    hits = list(MARKER_RE.finditer(text))
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        n = int(m.group(1))
        pages[n] = pages.get(n, "") + "\n" + text[m.end():end]
    return pages


def normalize(text: str) -> str:
    """Fold whitespace and quote characters so extraction artifacts don't read as
    fabrication. A PDF line-wrapped mid-sentence is the same passage."""
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("—", "-").replace("–", "-")
    return re.sub(r"\s+", " ", text).strip().lower()


def source_vocabulary(source_text: str) -> set[str]:
    return {
        w.lower()
        for w in re.findall(rf"[A-Za-z]{{{MIN_GROUNDING_WORD},}}", source_text)
    }


def ungrounded_words(text: str, vocab: set[str]) -> list[str]:
    """Words in an option that the source never uses.

    Inflections are tolerated by trimming the tail: a source saying "transcript"
    grounds an option saying "transcripts". Suffix-trimming is deliberately crude
    — a false pass here costs nothing (the judge still runs), while a false
    failure costs a rewrite round chasing a word the source did use.
    """
    missing = []
    for word in re.findall(rf"[A-Za-z]{{{MIN_GROUNDING_WORD},}}", text):
        low = word.lower()
        if low in COMMON_WORDS or low in vocab:
            continue
        if any(
            low[:cut] in vocab or any(v.startswith(low[:cut]) for v in vocab)
            for cut in range(len(low) - 1, MIN_STEM_LEN - 1, -1)
        ):
            continue
        missing.append(word)
    return sorted(set(missing))


def check_citations(answers_path: Path, source_text: str) -> list[str]:
    """Every quoted passage in the key must appear in the source, under the page
    it is attributed to. Returns a list of problem descriptions."""
    problems: list[str] = []
    pages = split_by_marker(source_text)
    whole = normalize(source_text)
    normalized_pages = {n: normalize(t) for n, t in pages.items()}

    for lineno, line in enumerate(
        answers_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        for quote in QUOTE_RE.findall(line):
            needle = normalize(quote)
            if needle not in whole:
                problems.append(
                    f"{answers_path.name}:{lineno}: quoted passage not found in "
                    f"source: {quote[:60]!r}"
                )
                continue
            # Found somewhere — now hold it to the page it was attributed to.
            cited = [int(n) for n in CITATION_RE.findall(line)]
            if not cited:
                problems.append(
                    f"{answers_path.name}:{lineno}: quote has no page/slide "
                    f"citation: {quote[:60]!r}"
                )
            elif normalized_pages and not any(
                needle in normalized_pages.get(n, "") for n in cited
            ):
                found = sorted(
                    n for n, t in normalized_pages.items() if needle in t
                )
                where = f"; it is on {found}" if found else ""
                problems.append(
                    f"{answers_path.name}:{lineno}: quote attributed to "
                    f"{'/'.join(str(c) for c in cited)} is not there{where}: "
                    f"{quote[:60]!r}"
                )
    return problems


def check_no_answers(text: str) -> list[str]:
    """Answer-key material found in the student-facing file."""
    problems = []
    for pattern, label in ANSWER_LEAK:
        m = pattern.search(text)
        if m:
            line = text[: m.start()].count("\n") + 1
            snippet = m.group(0).strip().replace("\n", " ")[:50]
            problems.append(f"line {line}: {label} — {snippet!r}")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description="Mechanical question-set checks.")
    ap.add_argument("source", type=Path)
    ap.add_argument("--key", required=True,
                    help="comma list (C,B,B,D,C) or path to a JSON key")
    ap.add_argument("--source", dest="source_text", type=Path,
                    help="extracted source text; enables option-vocabulary "
                         "grounding checks")
    ap.add_argument("--answers", type=Path,
                    help="answer key; with --source, verifies every quoted "
                         "passage against the page it cites")
    ap.add_argument("--assert-no-answers", action="store_true",
                    help="fail if the question file contains answers, "
                         "rationales or chain scaffolding (run before delivery)")
    args = ap.parse_args()

    if not args.source.exists():
        raise SystemExit(f"no such file: {args.source}")

    if args.answers and not args.source_text:
        raise SystemExit("--answers needs --source to check quotes against")

    source_text = ""
    vocab: set[str] = set()
    if args.source_text:
        if not args.source_text.exists():
            raise SystemExit(f"no such file: {args.source_text}")
        source_text = args.source_text.read_text(encoding="utf-8")
        vocab = source_vocabulary(source_text)
        if not vocab:
            raise SystemExit(f"{args.source_text}: no words found — wrong file?")

    question_text = args.source.read_text(encoding="utf-8")
    questions = split_questions(question_text)
    if not questions:
        raise SystemExit("no questions found (expected '## ' headings with A./B. options)")

    key = parse_key(args.key, len(questions))
    failures: list[str] = []
    option_counts: list[int] = []

    for i, (heading, body) in enumerate(questions, start=1):
        opts = OPTION_LINE.findall(body)
        # Slice the stem at where the first option line actually starts. Searching
        # the body for the letter instead ("A.") crashes on "A)" sets and, worse,
        # silently truncates the stem at an incidental "hemoglobin A." — hiding
        # the rest of it from the echo check below.
        first = OPTION_LINE.search(body)
        stem = body[: first.start()] if first else body
        by_letter = {l: t for l, t in opts}
        lengths = [len(t) for _, t in opts]
        correct = key.get(i)

        label = f"Q{i}"
        problems: list[str] = []
        option_counts.append(len(opts))

        if len(opts) < 3:
            problems.append(f"only {len(opts)} options")

        ratio = max(lengths) / min(lengths)
        # Short enumerated labels carry no actionable length cue — see
        # MIN_LENGTH_FOR_RATIO. Say so rather than staying silent, or a skipped
        # check reads as a passed one.
        ratio_meaningful = max(lengths) > MIN_LENGTH_FOR_RATIO
        notes: list[str] = []
        if not ratio_meaningful:
            notes.append(
                f"length checks skipped: longest option is {max(lengths)} chars "
                f"(≤{MIN_LENGTH_FOR_RATIO}), an enumerated-label set"
            )
        elif ratio > MAX_LENGTH_RATIO:
            problems.append(
                f"length ratio {ratio:.2f} > {MAX_LENGTH_RATIO} "
                f"(longest {max(lengths)}, shortest {min(lengths)} chars)"
            )

        for letter, text in opts:
            if REASON_WORDS.search(text):
                problems.append(f"option {letter} embeds reasoning")
            if ABSOLUTES.search(text):
                problems.append(f"option {letter} uses an absolute")
            # Options only — a stem is meant to describe a vignette in its own
            # words, so checking it here would flag every well-written question.
            if vocab:
                missing = ungrounded_words(text, vocab)
                if missing:
                    problems.append(
                        f"option {letter} uses wording the source never does: "
                        f"{', '.join(missing)} — name it the source's way"
                    )

        if correct is None:
            problems.append("no key entry")
        elif correct not in by_letter:
            problems.append(f"key says {correct} but no such option")
        else:
            if (
                ratio_meaningful
                and len(by_letter[correct]) == max(lengths)
                and ratio > 1.05
            ):
                problems.append(f"correct option {correct} is the longest")
            # A distinctive content word from the answer showing up in the stem
            # usually means the stem gave the game away.
            answer_words = {
                w.lower() for w in re.findall(r"[A-Za-z]{6,}", by_letter[correct])
            }
            stem_words = {w.lower() for w in re.findall(r"[A-Za-z]{6,}", stem)}
            leaked = sorted(answer_words & stem_words)
            if leaked:
                problems.append(f"stem echoes answer wording: {', '.join(leaked)}")

        if problems:
            failures.append(label)
            print(f"{label}: FAIL")
            for p in problems:
                print(f"    - {p}")
        else:
            print(f"{label}: ok  (n={len(opts)} ratio={ratio:.2f} key={correct})")
        for note in notes:
            print(f"    note: {note}")

    # Set-wide: correct answers should not cluster in one position. This check is
    # load-bearing — after round 1 the judge protocol stops re-running a full-set
    # blind pass and relies on this to catch clustering introduced by a rewrite.
    # So threshold against chance (n/k answers per letter), not against half the
    # set: "> n/2" only fires at 6-of-10, which no real set reaches, and a rule
    # that never fires is not a substitute for the pass it replaced.
    spread = Counter(key[i] for i in sorted(key) if i <= len(questions))
    n = len(questions)
    print(f"\nanswer positions: {dict(spread)}")
    if n >= 4:
        # Smallest option count in the set — the most forgiving k, so a spread
        # that plain guessing would produce anyway is never flagged.
        k = min(option_counts) if option_counts else 4
        limit = max(2, n // k + 1)
        worst = spread.most_common(1)[0]
        if worst[1] > limit:
            failures.append("set")
            print(f"SET FAIL: '{worst[0]}' holds {worst[1]} of {n} answers "
                  f"(chance is ~{n / k:.1f} across {k} options) — "
                  "redistribute positions")

    # Delivery gate for the student-facing file. Nobody reads this set by eye
    # any more, so a leaked answer has to fail loudly here or not at all.
    if args.assert_no_answers:
        leaks = check_no_answers(question_text)
        print()
        if leaks:
            failures.append("answer leak")
            print(f"ANSWER LEAK in {args.source.name} — this file goes to the "
                  "student:")
            for p in leaks:
                print(f"    - {p}")
        else:
            print(f"no answers leaked: ok  ({args.source.name} is safe to hand over)")

    # Citations. Needs both files, so it runs after the per-question loop.
    if args.answers:
        if not args.answers.exists():
            raise SystemExit(f"no such file: {args.answers}")
        cite_problems = check_citations(args.answers, source_text)
        print()
        if cite_problems:
            failures.append("citations")
            print("CITATION FAIL:")
            for p in cite_problems:
                print(f"    - {p}")
        elif MARKER_RE.search(source_text):
            print("citations: ok  (every quoted passage found under its cited page)")
        else:
            print("citations: ok  (every quoted passage found in the source; see "
                  "the page-marker note below)")

    # A skipped check must never read as a passed one — same reason the
    # length-ratio skip prints a note above.
    if not args.source_text:
        print("\nnote: no --source given, so option-vocabulary grounding and "
              "citation checks were SKIPPED. Gate 2 pays for what they catch.")
    elif not args.answers:
        print("\nnote: no --answers given, so citation verification was SKIPPED. "
              "Run it again with --answers before delivering.")
    if args.source_text and not MARKER_RE.search(source_text):
        print("note: source has no '--- page N ---' markers, so quotes were "
              "checked against the whole text, not the page they cite. Extract "
              "with scripts/extract_source.py to get per-page checking.")

    if failures:
        print(f"\n{len(failures)} problem(s). Fix these before running the judge gates.")
        sys.exit(1)
    print("\nMechanical checks passed. Now run the judge gates "
          "(references/judge-protocol.md) — they catch what this cannot: "
          "hop count, semantic echo, distractor truth, and multiple defensible "
          "answers.")


if __name__ == "__main__":
    main()
