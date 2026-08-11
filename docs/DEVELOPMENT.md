# Development history

How this skill's rules were derived and validated.

Built and validated against two independent lecture decks; the examples below are
illustrative, not a domain requirement. Built test-first, per the `writing-skills`
discipline: a baseline (RED) run generated questions with no skill present, then a second,
independent agent took them blind — no source, no domain reasoning, surface heuristics
only.

**It scored 5/5.** Its own explanations named the tells: _"only option that gives a
mechanism," "by far the longest and most detailed," "others are short flat denials, each
contains an absolute word."_

Those failure modes are what the skill's rules encode against:

| #   | Failure                                            |
| --- | -------------------------------------------------- |
| F1  | Correct option longest / only one with a mechanism |
| F2  | Stem hands over the reasoning                      |
| F3  | "Predict X and why" bloats the correct option      |
| F4  | Distractors self-refute via absolutes              |
| F5  | Meta-language leaks into student-facing text       |
| F6  | No vignette framing                                |

**GREEN:** the same blind probe against a set written with the skill returned
`cue_used: "none"` on **every question** — no surface tell to name. The sourced gate
independently re-derived every keyed answer at 3+ hops each, `source_sufficient` on every
one, quoting the source for every link. (The blind judge still _guessed_ some correct — but
self-reported `used_domain_knowledge: true` on each, which is the measurement limit the
protocol is explicit about, not a cue leak.)

Reaching that took multiple rounds across two source decks, and the value was in the
failures. Each round found a defect the previous round's rules did not cover, and every one
is now encoded:

| Found                                                                                                        | Rule added                                                                                                    |
| ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| Exclusionary stems ("X and Y are normal") hand over an elimination path                                      | Positive findings only                                                                                        |
| Options from different categories let a reader sort by category                                              | Draw from one closed source category                                                                          |
| `barrel-shaped` → `cavity` was picked blind despite sharing no words                                         | No semantic echo, even paraphrased                                                                            |
| Three specific acts + one general capability cues the general one                                            | Level the generality                                                                                          |
| `Interfering` for the source's `mi/siRNA` was ungrounded                                                     | Use the source's own vocabulary                                                                               |
| A stem paraphrasing an abbreviation the source never expands imports outside knowledge                       | Check the stem's paraphrases too                                                                              |
| Regrounding one question dropped it from 4 hops to 2                                                         | The synonym _was_ the hop — change concepts                                                                   |
| A vignette needed a diagnosis label the source never states                                                  | Pick a concept the source spells out verbatim                                                                 |
| A closed category named by an antonym pair (`direct`/`indirect` agents) leaked through the labels themselves | Homogeneous form isn't enough — don't key to a member of a self-describing pair whose axis the stem describes |

Two findings are worth more than the individual rules. **The gates pull against each
other:** every fix that made a question unambiguous for the sourced judge handed the blind
judge a new shortcut. The resolution is always in the options, never the stem. And **the
strongest option sets are opaque labels** — enumerated abbreviations or codes with no
descriptive content — which score close to a 1.00 length ratio and give the blind judge
nothing at all to work with.

`scripts/check_mechanics.py` automates the mechanical subset (length parity, embedded
reasoning, absolutes, answer clustering) so judge tokens go to what only a judge can see. It
cannot see semantic echo — that needs the blind gate. See
[`references/question-anatomy.md`](../skills/study-question-generator/references/question-anatomy.md)
for the full rubric, patterns, and self-check checklist behind these rules.
