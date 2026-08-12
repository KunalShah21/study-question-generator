#!/usr/bin/env bash
# Install the study-question-generator skill for Claude Code.
#
# Run it from a clone:      ./install.sh
# Or straight from GitHub:  curl -fsSL https://raw.githubusercontent.com/KunalShah21/study-question-generator/main/install.sh | bash
#
# Non-interactive by design — when piped, stdin is not a terminal, so nothing can be
# asked. Everything is controlled by flags.

set -euo pipefail

REPO_SLUG="KunalShah21/study-question-generator"
BRANCH="main"
SKILL_NAME="study-question-generator"
SKILL_SUBDIR="skills/$SKILL_NAME"

MODE=""        # link | copy | zip; empty = auto
DRY_RUN=0
TMPDIR_CREATED=""

cleanup() {
    if [ -n "$TMPDIR_CREATED" ] && [ -d "$TMPDIR_CREATED" ]; then
        rm -rf "$TMPDIR_CREATED"
    fi
}
trap cleanup EXIT

say()  { printf '%s\n' "$*"; }
step() { printf '==> %s\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die()  { printf 'error: %s\n' "$*" >&2; exit 1; }

run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '   [dry-run] %s\n' "$*"
    else
        "$@"
    fi
}

usage() {
    cat <<EOF
Install the $SKILL_NAME skill for Claude Code.

Usage: install.sh [options]

Options:
  --link      Symlink the skill instead of copying (requires a local clone)
  --copy      Copy the skill even when running from a local clone
  --zip       Build $SKILL_NAME.zip for uploading to claude.ai, instead of installing
  --dry-run   Print what would happen; change nothing
  --help      Show this message

With no options: symlinks when run from a clone (so git pull updates the skill),
copies when piped from the internet.

Destination: \${CLAUDE_CONFIG_DIR:-\$HOME/.claude}/skills/$SKILL_NAME
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --link)    MODE="link" ;;
        --copy)    MODE="copy" ;;
        --zip)     MODE="zip" ;;
        --dry-run) DRY_RUN=1 ;;
        --help|-h) usage; exit 0 ;;
        *)         die "unknown option: $1 (try --help)" ;;
    esac
    shift
done

# --- Where the skill goes ----------------------------------------------------

CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SKILLS_DIR="$CONFIG_DIR/skills"
DEST="$SKILLS_DIR/$SKILL_NAME"

# --- Are we running from a clone, or piped from curl? ------------------------
#
# When piped, bash reports its own path as the source: under bash 3.2,
# BASH_SOURCE[0] is literally "/bin/bash" — an existing file — so a plain
# [ -f "$self" ] test is not enough to tell the two cases apart. Screen out
# shell names first, then require the skill tree to actually sit beside us.

self="${BASH_SOURCE[0]:-$0}"
case "$(basename -- "$self")" in
    bash|sh|dash|zsh|ksh|-bash|-sh) self="" ;;
esac

SOURCE_DIR=""
if [ -n "$self" ] && [ -f "$self" ]; then
    candidate="$(cd "$(dirname -- "$self")" && pwd)"
    if [ -f "$candidate/$SKILL_SUBDIR/SKILL.md" ]; then
        SOURCE_DIR="$candidate"
    fi
fi

if [ -n "$SOURCE_DIR" ]; then
    step "Found the skill locally: $SOURCE_DIR/$SKILL_SUBDIR"
    : "${MODE:=link}"
else
    step "Downloading $REPO_SLUG ($BRANCH)"
    command -v curl >/dev/null 2>&1 || die "curl is required to download the skill"
    command -v tar  >/dev/null 2>&1 || die "tar is required to unpack the skill"

    TMPDIR_CREATED="$(mktemp -d 2>/dev/null || mktemp -d -t sqg)"
    # --strip-components=3 lands the skill's *contents* directly in $TMPDIR_CREATED/skill:
    #   study-question-generator-main/skills/study-question-generator/SKILL.md
    #   ^1                            ^2     ^3                      -> SKILL.md
    mkdir -p "$TMPDIR_CREATED/skill"
    curl -fsSL "https://codeload.github.com/$REPO_SLUG/tar.gz/refs/heads/$BRANCH" \
        | tar -xz -C "$TMPDIR_CREATED/skill" --strip-components=3 \
        || die "download failed — is the network up, and is $REPO_SLUG reachable?"

    [ -f "$TMPDIR_CREATED/skill/SKILL.md" ] \
        || die "downloaded archive did not contain $SKILL_SUBDIR/SKILL.md"

    SOURCE_DIR="$TMPDIR_CREATED"
    SKILL_SUBDIR="skill"
    if [ "$MODE" = "link" ]; then
        die "--link needs a local clone; the download lives in a temp dir that is deleted on exit"
    fi
    MODE="${MODE:-copy}"
fi

SRC="$SOURCE_DIR/$SKILL_SUBDIR"

# --- Preflight: one hard requirement, two optional extras --------------------

PYTHON=""
for cand in python3 /usr/bin/python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then
        if "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
            PYTHON="$(command -v "$cand")"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    found=""
    for cand in python3 /usr/bin/python3 python; do
        if command -v "$cand" >/dev/null 2>&1; then
            found="$found  $cand -> $("$cand" -V 2>&1)"$'\n'
        fi
    done
    if [ -n "$found" ]; then
        die "the skill's scripts need Python 3.9 or newer. Found:"$'\n'"$found"
    fi
    die "the skill's scripts need Python 3.9 or newer, and no python was found on PATH"
fi
step "Python: $PYTHON ($("$PYTHON" -V 2>&1))"

if "$PYTHON" -c 'import pypdf' 2>/dev/null; then
    say "    pypdf: installed (PDF sources supported)"
else
    say "    pypdf: not installed — PDF sources will not extract."
    say "           Install with: \"$PYTHON\" -m pip install pypdf"
    say "           PPTX, DOCX, HTML, Markdown and text sources work without it."
fi

if command -v pandoc >/dev/null 2>&1; then
    say "    pandoc: installed (DOCX input and --docx output supported)"
else
    say "    pandoc: not installed — DOCX/HTML input and --docx output unavailable."
    say "            HTML output, which prints to PDF from any browser, works without it."
fi

# --- --zip: build an upload for claude.ai and stop ---------------------------

if [ "$MODE" = "zip" ]; then
    command -v zip >/dev/null 2>&1 || die "zip is required for --zip"
    OUT_ZIP="$PWD/$SKILL_NAME.zip"
    step "Building $OUT_ZIP"
    # claude.ai wants the skill folder at the zip root, so zip from its parent.
    parent="$(cd "$(dirname -- "$SRC")" && pwd)"
    base="$(basename -- "$SRC")"
    if [ "$base" != "$SKILL_NAME" ]; then
        # A fetched copy lives in .../skill; stage it under the real name first.
        staging="$(mktemp -d 2>/dev/null || mktemp -d -t sqgzip)"
        run cp -R "$SRC" "$staging/$SKILL_NAME"
        parent="$staging"
    fi
    run rm -f "$OUT_ZIP"
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '   [dry-run] cd %s && zip -qr %s %s\n' "$parent" "$OUT_ZIP" "$SKILL_NAME"
    else
        ( cd "$parent" && zip -qr "$OUT_ZIP" "$SKILL_NAME" )
        say ""
        say "Upload $OUT_ZIP at claude.ai -> Settings -> Features -> Skills."
        say "Note: the Chat tab self-critiques instead of using a separate judge model."
    fi
    exit 0
fi

# --- Install ----------------------------------------------------------------

# Only ever touch $DEST. Sibling skills in $SKILLS_DIR are none of our business.
if [ -L "$DEST" ]; then
    current="$(cd "$(dirname -- "$DEST")" && readlink "$(basename -- "$DEST")")"
    resolved=""
    if [ -d "$DEST" ]; then
        resolved="$(cd -P "$DEST" && pwd)"
    fi
    want="$(cd -P "$SRC" && pwd)"
    if [ -n "$resolved" ] && [ "$resolved" = "$want" ]; then
        step "Already installed: $DEST -> $current"
        NEEDS_INSTALL=0
    else
        step "Replacing existing symlink at $DEST (-> ${current:-broken})"
        NEEDS_INSTALL=1
        REPLACE_KIND="symlink"
    fi
elif [ -e "$DEST" ]; then
    step "Backing up existing directory at $DEST"
    NEEDS_INSTALL=1
    REPLACE_KIND="dir"
else
    NEEDS_INSTALL=1
    REPLACE_KIND="none"
fi

if [ "${NEEDS_INSTALL:-1}" -eq 1 ]; then
    run mkdir -p "$SKILLS_DIR"

    case "${REPLACE_KIND:-none}" in
        symlink)
            run rm -f "$DEST"
            ;;
        dir)
            n=1
            while [ -e "$DEST-backup-$n" ]; do n=$((n + 1)); done
            run mv "$DEST" "$DEST-backup-$n"
            say "    previous install kept at $DEST-backup-$n"
            ;;
    esac

    if [ "$MODE" = "link" ]; then
        step "Linking $DEST -> $SRC"
        run ln -s "$(cd -P "$SRC" && pwd)" "$DEST"
    else
        step "Copying the skill to $DEST"
        run cp -R "$SRC" "$DEST"
        # check_mechanics.py ships 644 while its siblings ship 755, though all
        # three carry a #!/usr/bin/env python3 line. Normalize what we installed.
        if [ "$DRY_RUN" -eq 1 ]; then
            printf '   [dry-run] chmod 755 %s/scripts/*.py\n' "$DEST"
        else
            chmod 755 "$DEST"/scripts/*.py
        fi
    fi
fi

# --- Verify -----------------------------------------------------------------

if [ "$DRY_RUN" -eq 1 ]; then
    say ""
    say "Dry run complete. Nothing was changed."
    exit 0
fi

step "Verifying the install"
missing=""
for f in \
    SKILL.md \
    references/question-anatomy.md \
    references/judge-protocol.md \
    scripts/extract_source.py \
    scripts/check_mechanics.py \
    scripts/render_output.py
do
    [ -f "$DEST/$f" ] || missing="$missing $f"
done
[ -z "$missing" ] || die "install is incomplete, missing:$missing"

"$PYTHON" "$DEST/scripts/render_output.py" --help >/dev/null 2>&1 \
    || die "$DEST/scripts/render_output.py failed to run under $PYTHON"

say ""
say "Installed: $DEST"
say ""
say "Open Claude Code and type /$SKILL_NAME, or just ask for practice questions"
say "from a file. The skill will ask for anything else it needs."
