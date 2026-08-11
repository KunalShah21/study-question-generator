#!/usr/bin/env python3
"""Extract plain text from study material for question generation.

Supports PDF, PPTX, DOCX, HTML, Markdown and plain text. Emits page/slide
markers so generated questions can cite where a fact came from.

Only dependency is pypdf (for PDF). PPTX is parsed with the stdlib zipfile +
xml modules; DOCX and HTML go through pandoc if it is installed.

Usage:
    extract_source.py FILE [FILE ...] [--pages 5-8,17-18] [--out FILE]

    --pages   Keep only these pages/slides (1-indexed, ranges allowed).
              Applies to PDF and PPTX. Use it to exclude a deck's existing
              practice questions so generated ones are not copies.
    --out     Write to FILE instead of stdout.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def parse_pages(spec: str) -> set[int]:
    """Parse "5-8,17,20-22" into {5,6,7,8,17,20,21,22}."""
    pages: set[int] = set()
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            lo, _, hi = chunk.partition("-")
            try:
                start, end = int(lo), int(hi)
            except ValueError:
                raise SystemExit(f"bad --pages range: {chunk!r}")
            if start > end:
                start, end = end, start
            pages.update(range(start, end + 1))
        else:
            try:
                pages.add(int(chunk))
            except ValueError:
                raise SystemExit(f"bad --pages value: {chunk!r}")
    return pages


def clean(text: str) -> str:
    """Normalize whitespace without destroying the line structure."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace(" ", " ").replace("​", "")
    # Collapse the ligature-ish spacing pypdf sometimes emits mid-word.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()


def extract_pdf(path: Path, keep: set[int] | None) -> str:
    try:
        import pypdf
    except ImportError:
        raise SystemExit(
            "PDF support needs pypdf. Install it with: pip install pypdf"
        )
    reader = pypdf.PdfReader(str(path))
    parts = []
    for i, page in enumerate(reader.pages, start=1):
        if keep and i not in keep:
            continue
        body = clean(page.extract_text() or "")
        if body:
            parts.append(f"--- page {i} ---\n{body}")
    if not parts:
        scope = " in the selected page range" if keep else ""
        raise SystemExit(
            f"{path.name}: no extractable text{scope}. If this is a scanned "
            "document it needs OCR first."
        )
    return "\n\n".join(parts)


def extract_pptx(path: Path, keep: set[int] | None) -> str:
    """Read slide text straight out of the OOXML package.

    Slides are named ppt/slides/slideN.xml; every text run is an <a:t> element.
    Sorting numerically matters because slide10 sorts before slide2 as a string.
    """
    parts = []
    with zipfile.ZipFile(path) as zf:
        slides = [n for n in zf.namelist()
                  if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
        slides.sort(key=lambda n: int(re.search(r"(\d+)", n).group(1)))

        notes_for = {}
        for name in zf.namelist():
            m = re.fullmatch(r"ppt/notesSlides/notesSlide(\d+)\.xml", name)
            if m:
                notes_for[int(m.group(1))] = name

        for i, name in enumerate(slides, start=1):
            if keep and i not in keep:
                continue
            runs = [
                (el.text or "")
                for el in ET.fromstring(zf.read(name)).iter(f"{A_NS}t")
            ]
            body = clean("\n".join(r for r in runs if r.strip()))

            note_name = notes_for.get(i)
            if note_name:
                note_runs = [
                    (el.text or "")
                    for el in ET.fromstring(zf.read(note_name)).iter(f"{A_NS}t")
                ]
                note = clean("\n".join(r for r in note_runs if r.strip()))
                # Speaker notes routinely hold the explanation a slide omits.
                if note:
                    body = f"{body}\n\n[speaker notes] {note}".strip()

            if body:
                parts.append(f"--- slide {i} ---\n{body}")
    if not parts:
        raise SystemExit(f"{path.name}: no slide text found.")
    return "\n\n".join(parts)


def extract_via_pandoc(path: Path) -> str:
    if not shutil.which("pandoc"):
        raise SystemExit(
            f"{path.suffix} support needs pandoc. Install it with: brew install pandoc"
        )
    proc = subprocess.run(
        ["pandoc", str(path), "-t", "plain", "--wrap=none"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"pandoc failed on {path.name}: {proc.stderr.strip()}")
    return clean(proc.stdout)


def extract(path: Path, keep: set[int] | None) -> str:
    if not path.exists():
        raise SystemExit(f"no such file: {path}")
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(path, keep)
    if suffix == ".pptx":
        return extract_pptx(path, keep)
    if suffix in {".docx", ".html", ".htm", ".odt", ".rtf", ".epub"}:
        return extract_via_pandoc(path)
    if suffix in {".md", ".markdown", ".txt", ".text", ""}:
        return clean(path.read_text(encoding="utf-8", errors="replace"))
    if suffix == ".ppt":
        raise SystemExit(
            ".ppt (legacy) is not supported. Open it in PowerPoint or Keynote "
            "and save as .pptx first."
        )
    raise SystemExit(f"unsupported file type: {suffix}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Extract study material to plain text.")
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--pages", help="keep only these pages/slides, e.g. 5-8,17")
    ap.add_argument("--out", type=Path, help="write here instead of stdout")
    args = ap.parse_args()

    keep = parse_pages(args.pages) if args.pages else None

    blocks = []
    for path in args.files:
        body = extract(path, keep)
        blocks.append(f"===== SOURCE: {path.name} =====\n\n{body}")
    text = "\n\n\n".join(blocks)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        words = len(text.split())
        print(f"wrote {args.out} ({words:,} words)", file=sys.stderr)
    else:
        sys.stdout.write(text + "\n")


if __name__ == "__main__":
    main()
