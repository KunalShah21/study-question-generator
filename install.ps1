<#
Install the study-question-generator skill for Claude Code on Windows.

Run it from a clone:      .\install.ps1
Or straight from GitHub:  irm https://raw.githubusercontent.com/KunalShah21/study-question-generator/main/install.ps1 | iex

Non-interactive by design — when piped, nothing can be asked. Everything is controlled
by switches. Written for PowerShell 5.1 (the version shipped with Windows), so no
ternaries, no null-coalescing.
#>

[CmdletBinding()]
param(
    [switch]$Link,
    [switch]$Copy,
    [switch]$Zip,
    [switch]$DryRun,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

$RepoSlug  = 'KunalShah21/study-question-generator'
$Branch    = 'main'
$SkillName = 'study-question-generator'

function Write-Step { param($Message) Write-Host "==> $Message" }
function Write-Info { param($Message) Write-Host "    $Message" }
function Die {
    param($Message)
    Write-Host "error: $Message" -ForegroundColor Red
    exit 1
}

# Native commands that write to stderr throw a NativeCommandError under
# $ErrorActionPreference = 'Stop', so probe external tools with it relaxed.
function Invoke-Native {
    param([string]$Exe, [string[]]$Arguments)
    $saved = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = & $Exe @Arguments 2>&1
        return [pscustomobject]@{ Output = ($out -join ' ').Trim(); ExitCode = $LASTEXITCODE }
    } finally {
        $ErrorActionPreference = $saved
    }
}

function Show-Usage {
    Write-Host @"
Install the $SkillName skill for Claude Code.

Usage: install.ps1 [options]

Options:
  -Link      Symlink the skill instead of copying (requires a local clone)
  -Copy      Copy the skill even when running from a local clone
  -Zip       Build $SkillName.zip for uploading to claude.ai, instead of installing
  -DryRun    Print what would happen; change nothing
  -Help      Show this message

With no options: symlinks when run from a clone (so git pull updates the skill),
copies when piped from the internet. Symlinks on Windows need Developer Mode or an
elevated prompt; if creating one fails, this falls back to copying.

Destination: %CLAUDE_CONFIG_DIR%\skills\$SkillName
         or: %USERPROFILE%\.claude\skills\$SkillName
"@
}

if ($Help) { Show-Usage; exit 0 }

# --- Where the skill goes ----------------------------------------------------

$configDir = $env:CLAUDE_CONFIG_DIR
if ([string]::IsNullOrWhiteSpace($configDir)) {
    $configDir = Join-Path $env:USERPROFILE '.claude'
}
$skillsDir = Join-Path $configDir 'skills'
$dest      = Join-Path $skillsDir $SkillName

# --- Are we running from a clone, or piped from irm? -------------------------
#
# When the script is piped through iex there is no file on disk, so
# $PSCommandPath is empty. Require both a real path and the skill tree beside it.

$sourceDir = $null
if (-not [string]::IsNullOrWhiteSpace($PSCommandPath) -and (Test-Path -LiteralPath $PSCommandPath -PathType Leaf)) {
    $candidate = Split-Path -Parent $PSCommandPath
    $probe = Join-Path $candidate (Join-Path 'skills' (Join-Path $SkillName 'SKILL.md'))
    if (Test-Path -LiteralPath $probe -PathType Leaf) {
        $sourceDir = $candidate
    }
}

$tempRoot = $null
$src = $null

if ($sourceDir) {
    $src = Join-Path $sourceDir (Join-Path 'skills' $SkillName)
    Write-Step "Found the skill locally: $src"
    $fetched = $false
} else {
    Write-Step "Downloading $RepoSlug ($Branch)"
    if ($Link) {
        Die '-Link needs a local clone; the download lives in a temp dir that is deleted on exit'
    }
    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("sqg-" + [System.Guid]::NewGuid().ToString('N').Substring(0, 8))
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    $zipPath = Join-Path $tempRoot 'repo.zip'
    try {
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri "https://codeload.github.com/$RepoSlug/zip/refs/heads/$Branch" -OutFile $zipPath -UseBasicParsing
        Expand-Archive -LiteralPath $zipPath -DestinationPath $tempRoot -Force
    } catch {
        Die "download failed — is the network up, and is $RepoSlug reachable? ($($_.Exception.Message))"
    }
    # The archive's top-level folder is <repo>-<branch>; find the skill under it
    # rather than hardcoding the name.
    $found = Get-ChildItem -Path $tempRoot -Directory |
        ForEach-Object { Join-Path $_.FullName (Join-Path 'skills' $SkillName) } |
        Where-Object { Test-Path -LiteralPath (Join-Path $_ 'SKILL.md') -PathType Leaf } |
        Select-Object -First 1
    if (-not $found) { Die "downloaded archive did not contain skills\$SkillName\SKILL.md" }
    $src = $found
    $fetched = $true
}

# Decide install mode.
$mode = 'link'
if ($fetched) { $mode = 'copy' }
if ($Copy) { $mode = 'copy' }
if ($Link) { $mode = 'link' }
if ($Zip)  { $mode = 'zip' }

# --- Preflight: one hard requirement, two optional extras --------------------

$python = $null
$attempts = @()
foreach ($cand in @('python', 'python3', 'py')) {
    $exe = Get-Command $cand -ErrorAction SilentlyContinue
    if (-not $exe) { continue }
    $argPrefix = @()
    if ($cand -eq 'py') { $argPrefix = @('-3') }
    $check = Invoke-Native $exe.Source ($argPrefix + @('-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'))
    if ($check.ExitCode -eq 0) {
        $python = $exe.Source
        $pythonArgs = $argPrefix
        break
    }
    $reported = (Invoke-Native $exe.Source ($argPrefix + @('-V'))).Output
    $attempts += "  $cand -> $reported"
}

if (-not $python) {
    if ($attempts.Count -gt 0) {
        Die ("the skill's scripts need Python 3.9 or newer. Found:`n" + ($attempts -join "`n"))
    }
    Die "the skill's scripts need Python 3.9 or newer, and no python was found on PATH. Install it from https://www.python.org/downloads/ or the Microsoft Store."
}

$pythonVersion = (Invoke-Native $python ($pythonArgs + @('-V'))).Output
Write-Step "Python: $python ($pythonVersion)"

if ((Invoke-Native $python ($pythonArgs + @('-c', 'import pypdf'))).ExitCode -eq 0) {
    Write-Info 'pypdf: installed (PDF sources supported)'
} else {
    Write-Info 'pypdf: not installed — PDF sources will not extract.'
    Write-Info "       Install with: `"$python`" -m pip install pypdf"
    Write-Info '       PPTX, DOCX, HTML, Markdown and text sources work without it.'
}

if (Get-Command pandoc -ErrorAction SilentlyContinue) {
    Write-Info 'pandoc: installed (DOCX input and --docx output supported)'
} else {
    Write-Info 'pandoc: not installed — DOCX/HTML input and --docx output unavailable.'
    Write-Info '        HTML output, which prints to PDF from any browser, works without it.'
}

# --- -Zip: build an upload for claude.ai and stop ----------------------------

if ($mode -eq 'zip') {
    $outZip = Join-Path (Get-Location).Path "$SkillName.zip"
    Write-Step "Building $outZip"
    # claude.ai wants the skill folder at the zip root, so compress the folder itself.
    if ($DryRun) {
        Write-Info "[dry-run] Compress-Archive -Path $src -DestinationPath $outZip"
    } else {
        if (Test-Path -LiteralPath $outZip) { Remove-Item -LiteralPath $outZip -Force }
        Compress-Archive -Path $src -DestinationPath $outZip
        Write-Host ''
        Write-Host "Upload $outZip at claude.ai -> Settings -> Features -> Skills."
        Write-Host 'Note: the Chat tab self-critiques instead of using a separate judge model.'
    }
    if ($tempRoot -and (Test-Path -LiteralPath $tempRoot)) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
    exit 0
}

# --- Install ----------------------------------------------------------------

# Only ever touch $dest. Sibling skills in $skillsDir are none of our business.
$srcFull = (Resolve-Path -LiteralPath $src).Path
$needsInstall = $true
$replaceKind = 'none'

$existing = Get-Item -LiteralPath $dest -ErrorAction SilentlyContinue
if ($existing) {
    $isLink = $existing.Attributes -band [System.IO.FileAttributes]::ReparsePoint
    if ($isLink) {
        # In PS 5.1 .Target is a collection; in 6+ it is a string. Normalize.
        $target = $existing.Target | Select-Object -First 1
        $resolvedTarget = $null
        if ($target) {
            $rp = Resolve-Path -LiteralPath $target -ErrorAction SilentlyContinue
            if ($rp) { $resolvedTarget = $rp.Path }
        }
        if ($resolvedTarget -and ($resolvedTarget -eq $srcFull)) {
            Write-Step "Already installed: $dest -> $target"
            $needsInstall = $false
        } else {
            Write-Step "Replacing existing link at $dest (-> $target)"
            $replaceKind = 'link'
        }
    } else {
        Write-Step "Backing up existing directory at $dest"
        $replaceKind = 'dir'
    }
}

if ($needsInstall) {
    if (-not $DryRun) { New-Item -ItemType Directory -Path $skillsDir -Force | Out-Null }

    if ($replaceKind -eq 'link') {
        if ($DryRun) { Write-Info "[dry-run] remove link $dest" }
        else { Remove-Item -LiteralPath $dest -Force }
    } elseif ($replaceKind -eq 'dir') {
        $n = 1
        while (Test-Path -LiteralPath "$dest-backup-$n") { $n++ }
        if ($DryRun) { Write-Info "[dry-run] move $dest -> $dest-backup-$n" }
        else {
            Move-Item -LiteralPath $dest -Destination "$dest-backup-$n"
            Write-Info "previous install kept at $dest-backup-$n"
        }
    }

    if ($mode -eq 'link') {
        Write-Step "Linking $dest -> $srcFull"
        if ($DryRun) {
            Write-Info "[dry-run] New-Item -ItemType SymbolicLink -Path $dest -Target $srcFull"
        } else {
            $linked = $false
            try {
                New-Item -ItemType SymbolicLink -Path $dest -Target $srcFull -ErrorAction Stop | Out-Null
                $linked = $true
            } catch {
                Write-Info 'symlink not permitted (needs Developer Mode or an elevated prompt) — copying instead'
            }
            if (-not $linked) {
                Copy-Item -LiteralPath $src -Destination $dest -Recurse
                $mode = 'copy'
            }
        }
    } else {
        Write-Step "Copying the skill to $dest"
        if ($DryRun) { Write-Info "[dry-run] copy $src -> $dest" }
        else { Copy-Item -LiteralPath $src -Destination $dest -Recurse }
    }
}

# --- Verify -----------------------------------------------------------------

if ($DryRun) {
    if ($tempRoot -and (Test-Path -LiteralPath $tempRoot)) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
    Write-Host ''
    Write-Host 'Dry run complete. Nothing was changed.'
    exit 0
}

Write-Step 'Verifying the install'
$required = @(
    'SKILL.md',
    'references\question-anatomy.md',
    'references\judge-protocol.md',
    'scripts\extract_source.py',
    'scripts\check_mechanics.py',
    'scripts\render_output.py'
)
$missing = @()
foreach ($f in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $dest $f) -PathType Leaf)) { $missing += $f }
}
if ($missing.Count -gt 0) { Die ("install is incomplete, missing: " + ($missing -join ', ')) }

$smoke = Invoke-Native $python ($pythonArgs + @((Join-Path $dest 'scripts\render_output.py'), '--help'))
if ($smoke.ExitCode -ne 0) { Die "$dest\scripts\render_output.py failed to run under $python" }

if ($tempRoot -and (Test-Path -LiteralPath $tempRoot)) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }

Write-Host ''
Write-Host "Installed: $dest"
Write-Host ''
Write-Host "Open Claude Code and type /$SkillName, or just ask for practice questions"
Write-Host 'from a file. The skill will ask for anything else it needs.'
