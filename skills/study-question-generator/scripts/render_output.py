#!/usr/bin/env python3
"""Render a question set from Markdown to print-ready HTML (and optionally DOCX).

HTML is self-contained (CSS inlined, no network fetches, no JS) so it opens on
any machine with a browser and prints to PDF via Cmd+P / Ctrl+P. That is the
lowest-friction path for a non-technical recipient: no Word, no LaTeX, no fonts
to install.

Handles the Markdown subset this skill emits: headings, paragraphs, bullet and
option lists, pipe tables, bold/italic/code, blockquotes and horizontal rules.
Written against the stdlib so HTML output never depends on pandoc being present.

Usage:
    render_output.py questions.md [--out questions.html] [--docx] [--title "..."]
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

CSS = """
:root { --ink:#1a1a1a; --muted:#565656; --rule:#d8d8d8; --accent:#0b5d8f;
        --shade:#f6f7f9; }
* { box-sizing: border-box; }
body {
  font: 16px/1.62 "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  color: var(--ink); background:#fff;
  max-width: 44rem; margin: 0 auto; padding: 3rem 1.5rem 5rem;
  -webkit-text-size-adjust: 100%;
}
h1 { font-size: 1.9rem; line-height:1.2; margin:0 0 .3rem; letter-spacing:-.01em; }
h1 + p { color: var(--muted); font-size:.95rem; margin:0 0 2.2rem;
  padding-bottom:1.2rem; border-bottom:2px solid var(--ink); }
h2 {
  font-size: 1.06rem; margin: 2.4rem 0 .9rem; padding-top:.9rem;
  border-top: 1px solid var(--rule); letter-spacing:.02em;
  text-transform: uppercase; font-weight:700; color: var(--accent);
}
h3 { font-size: 1rem; margin: 1.4rem 0 .5rem; }
p { margin: 0 0 .85rem; }
strong { font-weight: 700; }
code { font: .87em ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: var(--shade); padding: .1em .35em; border-radius: 3px; }
hr { border:0; border-top:1px solid var(--rule); margin:2.2rem 0; }
blockquote { margin:.9rem 0; padding:.1rem 0 .1rem 1rem;
  border-left:3px solid var(--rule); color:var(--muted); }
ul { margin:.2rem 0 1rem; padding-left:1.35rem; }
li { margin:.3rem 0; }

/* Distractor tables: the answer key leans on these heavily. */
table { border-collapse: collapse; width:100%; margin:.7rem 0 1.3rem;
  font-size:.93rem; break-inside: avoid; page-break-inside: avoid; }
th, td { border:1px solid var(--rule); padding:.42rem .6rem;
  text-align:left; vertical-align:top; }
th { background: var(--shade); font-weight:700; color:var(--accent);
  font-size:.82rem; text-transform:uppercase; letter-spacing:.02em; }
tbody tr:nth-child(even) td { background:#fbfbfc; }

/* Answer options: hanging letter, generous click/pencil room, never split. */
ul.options { list-style:none; padding-left:0; margin:.6rem 0 1.1rem; }
ul.options li {
  margin:0; padding:.42rem .6rem .42rem 2.35rem; position:relative;
  border-bottom:1px solid #efefef;
}
ul.options li .opt-letter {
  position:absolute; left:.55rem; top:.42rem;
  font-weight:700; color:var(--accent); font-variant-numeric:tabular-nums;
}
.question { break-inside: avoid; page-break-inside: avoid; }
.answer-line { margin:.2rem 0 1rem; font-weight:700; color:var(--accent); }
.footer { margin-top:3.5rem; padding-top:1rem; border-top:1px solid var(--rule);
  color:var(--muted); font-size:.82rem; }

@media print {
  @page { margin: 0.7in; }
  body { max-width:none; padding:0; font-size:11.5pt; }
  h1 { font-size:17pt; } h2 { font-size:11pt; }
  a { color: inherit; text-decoration: none; }
  .footer { font-size:8.5pt; }
}
"""

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
{body}
<p class="footer">{footer}</p>
</body>
</html>
"""

# "A. text" / "A) text", optionally already bulleted with "- ".
OPTION_RE = re.compile(r"^\s*(?:[-*]\s+)?([A-J])[.)]\s+(.*)$")
BULLET_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
# The delimiter row is what distinguishes a table from prose containing pipes.
TABLE_DELIM_RE = re.compile(r"^\s*\|(?:\s*:?-{1,}:?\s*\|)+\s*$")


def split_row(line: str) -> list[str]:
    """Split a pipe-table row into cells, honouring \\| escapes."""
    body = line.strip()
    body = body[1:] if body.startswith("|") else body
    body = body[:-1] if body.endswith("|") else body
    cells = re.split(r"(?<!\\)\|", body)
    return [c.strip().replace(r"\|", "|") for c in cells]


def render_table(header: str, rows: list[str]) -> str:
    """Build an HTML table from a Markdown header row plus its body rows."""
    head = split_row(header)
    ncols = len(head)
    parts = ["<table>", "<thead>", "<tr>"]
    parts += [f"<th>{inline(c)}</th>" for c in head]
    parts += ["</tr>", "</thead>", "<tbody>"]
    for row in rows:
        cells = split_row(row)
        # Pad or trim so a ragged row cannot break the column grid.
        cells = (cells + [""] * ncols)[:ncols]
        parts.append("<tr>")
        parts += [f"<td>{inline(c)}</td>" for c in cells]
        parts.append("</tr>")
    parts += ["</tbody>", "</table>"]
    return "\n".join(parts)


def inline(text: str) -> str:
    """Escape, then re-apply the inline Markdown we support."""
    out = html.escape(text, quote=False)
    # Code first: its contents must not be re-processed for emphasis.
    stash: list[str] = []

    def keep_code(m: re.Match) -> str:
        stash.append(m.group(1))
        return f"\x00{len(stash) - 1}\x00"

    out = re.sub(r"`([^`]+)`", keep_code, out)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", out)
    out = re.sub(r"(?<![\w_])_([^_\n]+)_(?![\w_])", r"<em>\1</em>", out)
    out = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', out)
    for i, code in enumerate(stash):
        out = out.replace(f"\x00{i}\x00", f"<code>{code}</code>")
    return out


def md_to_html(md: str) -> str:
    """Convert the Markdown subset this skill emits into HTML blocks."""
    lines = md.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    para: list[str] = []
    list_kind: str | None = None  # 'options' | 'bullets' | None
    in_question = False

    def flush_para() -> None:
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()

    def flush_list() -> None:
        nonlocal list_kind
        if list_kind:
            out.append("</ul>")
            list_kind = None

    def close_question() -> None:
        nonlocal in_question
        if in_question:
            out.append("</section>")
            in_question = False

    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        line = raw.rstrip()

        if not line.strip():
            flush_para()
            flush_list()
            continue

        # A table is a header row followed by a delimiter row; consume the block.
        if (TABLE_ROW_RE.match(line)
                and i < len(lines)
                and TABLE_DELIM_RE.match(lines[i].rstrip())):
            flush_para()
            flush_list()
            i += 1  # skip the delimiter
            body: list[str] = []
            while i < len(lines) and TABLE_ROW_RE.match(lines[i].rstrip()):
                body.append(lines[i].rstrip())
                i += 1
            out.append(render_table(line, body))
            continue

        heading = HEADING_RE.match(line)
        if heading:
            flush_para()
            flush_list()
            level = len(heading.group(1))
            text = heading.group(2).strip()
            if level == 2:
                # Each H2 starts a question; keep it whole across page breaks.
                close_question()
                out.append('<section class="question">')
                in_question = True
            out.append(f"<h{level}>{inline(text)}</h{level}>")
            continue

        if re.fullmatch(r"(?:---+|\*\*\*+|___+)", line.strip()):
            flush_para()
            flush_list()
            close_question()
            out.append("<hr>")
            continue

        if line.lstrip().startswith(">"):
            flush_para()
            flush_list()
            body = line.lstrip()[1:].strip()
            out.append(f"<blockquote>{inline(body)}</blockquote>")
            continue

        opt = OPTION_RE.match(line)
        if opt:
            flush_para()
            if list_kind != "options":
                flush_list()
                out.append('<ul class="options">')
                list_kind = "options"
            letter, text = opt.group(1), opt.group(2).strip()
            out.append(
                f'<li><span class="opt-letter">{letter}.</span>{inline(text)}</li>'
            )
            continue

        bullet = BULLET_RE.match(line)
        if bullet:
            flush_para()
            if list_kind != "bullets":
                flush_list()
                out.append("<ul>")
                list_kind = "bullets"
            out.append(f"<li>{inline(bullet.group(1).strip())}</li>")
            continue

        flush_list()
        para.append(line.strip())

    flush_para()
    flush_list()
    close_question()
    return "\n".join(out)


def derive_title(md: str, fallback: str) -> str:
    for line in md.split("\n"):
        m = re.match(r"^#\s+(.*)$", line.strip())
        if m:
            return m.group(1).strip()
    return fallback


def to_docx(md_path: Path, out_path: Path) -> Path | None:
    if not shutil.which("pandoc"):
        print("skipping --docx: pandoc not found (brew install pandoc)",
              file=sys.stderr)
        return None
    proc = subprocess.run(
        ["pandoc", str(md_path), "-o", str(out_path)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f"pandoc failed: {proc.stderr.strip()}", file=sys.stderr)
        return None
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Render question Markdown to print-ready HTML.")
    ap.add_argument("source", type=Path, help="Markdown file to render")
    ap.add_argument("--out", type=Path, help="output .html (default: alongside source)")
    ap.add_argument("--title", help="override the <title> / browser tab name")
    ap.add_argument("--docx", action="store_true",
                    help="also write a .docx via pandoc")
    ap.add_argument("--footer", default="", help="footer note (e.g. source citation)")
    args = ap.parse_args()

    if not args.source.exists():
        raise SystemExit(f"no such file: {args.source}")

    md = args.source.read_text(encoding="utf-8")
    title = args.title or derive_title(md, args.source.stem)
    out_path = args.out or args.source.with_suffix(".html")

    footer = args.footer or (
        "Print or save as PDF with Cmd+P (Mac) / Ctrl+P (Windows)."
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        PAGE.format(title=html.escape(title), css=CSS,
                    body=md_to_html(md), footer=html.escape(footer)),
        encoding="utf-8",
    )
    written = [out_path]

    if args.docx:
        docx = to_docx(args.source, out_path.with_suffix(".docx"))
        if docx:
            written.append(docx)

    for p in written:
        print(p)


if __name__ == "__main__":
    main()
