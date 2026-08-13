#!/usr/bin/env python3
"""Mechanical pre-check for a question set. Run before spending judge tokens.

Catches the option-level defects that are cheap to detect with string rules:
length disparity, reasoning words inside options, the correct answer being the
longest, answer-position clustering, and answer terms leaking into the stem.

Judgment-dependent checks (hop count, whether a distractor is a true source
fact, whether two options are both defensible) still require the judge gates in
references/judge-protocol.md. This script does not replace them.

Length checks are skipped on enumerated-label sets (see MIN_LENGTH_FOR_RATIO) —
a ratio computed over 3- and 4-character acronyms is noise, and flagging it
trains readers to ignore the whole script. Skips are printed, never silent.

Usage:
    check_mechanics.py questions.md --key C,B,B,D,C
    check_mechanics.py questions.md --key key.json

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
OPTION_LINE = re.compile(r"^\s*([A-J])[.)]\s+(.+?)\s*$", re.M)

MAX_LENGTH_RATIO = 1.35
# Below this, a length ratio is noise. The best option sets are enumerated labels
# (BER/MMR/HR/NER, TFIID…TFIIH) where BER vs NHEJ is a "1.33 ratio" that no
# test-taker can act on — and question-anatomy.md recommends exactly those sets.
# Flagging them trained readers to ignore this script, which is how real defects
# ended up costing judge rounds.
MIN_LENGTH_FOR_RATIO = 12


def parse_key(spec: str, n_questions: int) -> dict[int, str]:
    path = Path(spec)
    if path.exists():
        data = json.loads(path.read_text())
        if isinstance(data, dict):
            return {int(k): v.strip().upper() for k, v in data.items()}
        return {i: str(v).strip().upper() for i, v in enumerate(data, start=1)}
    letters = [s.strip().upper() for s in spec.split(",") if s.strip()]
    if len(letters) != n_questions:
        raise SystemExit(
            f"--key has {len(letters)} answers but found {n_questions} questions"
        )
    return {i: l for i, l in enumerate(letters, start=1)}


def split_questions(text: str) -> list[tuple[str, str]]:
    """Return (heading, body) per '## ' section that contains options."""
    chunks = re.split(r"^##\s+", text, flags=re.M)[1:]
    out = []
    for chunk in chunks:
        heading, _, body = chunk.partition("\n")
        if OPTION_LINE.search(body):
            out.append((heading.strip(), body))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Mechanical question-set checks.")
    ap.add_argument("source", type=Path)
    ap.add_argument("--key", required=True,
                    help="comma list (C,B,B,D,C) or path to a JSON key")
    ap.add_argument("--max-ratio", type=float, default=MAX_LENGTH_RATIO)
    args = ap.parse_args()

    if not args.source.exists():
        raise SystemExit(f"no such file: {args.source}")

    questions = split_questions(args.source.read_text(encoding="utf-8"))
    if not questions:
        raise SystemExit("no questions found (expected '## ' headings with A./B. options)")

    key = parse_key(args.key, len(questions))
    failures: list[str] = []

    for i, (heading, body) in enumerate(questions, start=1):
        opts = OPTION_LINE.findall(body)
        stem = body[: body.index(opts[0][0] + ".")] if opts else body
        by_letter = {l: t for l, t in opts}
        lengths = [len(t) for _, t in opts]
        correct = key.get(i)

        label = f"Q{i}"
        problems: list[str] = []

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
        elif ratio > args.max_ratio:
            problems.append(
                f"length ratio {ratio:.2f} > {args.max_ratio} "
                f"(longest {max(lengths)}, shortest {min(lengths)} chars)"
            )

        for letter, text in opts:
            if REASON_WORDS.search(text):
                problems.append(f"option {letter} embeds reasoning")
            if ABSOLUTES.search(text):
                problems.append(f"option {letter} uses an absolute")

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

    # Set-wide: correct answers should not cluster in one position.
    spread = Counter(key[i] for i in sorted(key) if i <= len(questions))
    n = len(questions)
    print(f"\nanswer positions: {dict(spread)}")
    if n >= 4:
        worst = spread.most_common(1)[0]
        if worst[1] > max(2, round(n * 0.5)):
            failures.append("set")
            print(f"SET FAIL: '{worst[0]}' holds {worst[1]} of {n} answers — "
                  "redistribute positions")

    if failures:
        print(f"\n{len(failures)} problem(s). Fix these before running the judge gates.")
        sys.exit(1)
    print("\nMechanical checks passed. Now run the judge gates "
          "(references/judge-protocol.md) — they catch what this cannot: "
          "hop count, distractor truth, and multiple defensible answers.")


if __name__ == "__main__":
    main()
