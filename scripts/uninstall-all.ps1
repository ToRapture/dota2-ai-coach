#Requires -Version 5.1
<#
.SYNOPSIS
  Full uninstall: GSI cfg, venv, whisper model cache.
.DESCRIPTION
  Does NOT edit your Claude Code / OpenCode config. Remove the "dota2-coach"
  entry from those configs manually; the README has the exact snippet.
.PARAMETER ProjectRoot
  Path to the project. Defaults to the parent directory of this script.
#>
[CmdletBinding()]
param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$DotaRoot
)

$ErrorActionPreference = 'Continue'
Write-Host "Uninstall start" -ForegroundColor Cyan

# 1. GSI cfg
& (Join-Path $PSScriptRoot 'uninstall-gsi.ps1') @(if ($DotaRoot) { '-DotaRoot', $DotaRoot } else { @() })

# 2. venv
$venv = Join-Path $ProjectRoot '.venv'
if (Test-Path $venv) {
    Write-Host "Removing venv: $venv"
    Remove-Item -Recurse -Force $venv
}

# 3. uv cache for this project (optional — only removes env uv created)
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Push-Location $ProjectRoot
    try { uv cache prune } catch {}
    Pop-Location
}

# 4. Whisper / HuggingFace models downloaded by faster-whisper
$hfCache = Join-Path $env:USERPROFILE '.cache\huggingface\hub'
if (Test-Path $hfCache) {
    Get-ChildItem $hfCache -Directory |
        Where-Object { $_.Name -like '*faster-whisper*' -or $_.Name -like '*Systran*' -or $_.Name -like '*silero*' } |
        ForEach-Object {
            Write-Host "Removing cached model: $($_.FullName)"
            Remove-Item -Recurse -Force $_.FullName
        }
}

# 5. Torch hub cache (silero-vad fallback)
$torchHub = Join-Path $env:USERPROFILE '.cache\torch\hub'
if (Test-Path $torchHub) {
    Get-ChildItem $torchHub -Directory -Filter '*silero_vad*' | ForEach-Object {
        Write-Host "Removing: $($_.FullName)"
        Remove-Item -Recurse -Force $_.FullName
    }
}

Write-Host ""
Write-Host "Done. Remaining manual step:" -ForegroundColor Yellow
Write-Host "  Remove 'dota2-coach' from your Claude Code / OpenCode MCP config."
Write-Host "  Remove '-gamestateintegration' from Dota 2 launch options."
Write-Host "  To wipe the source tree itself: Remove-Item -Recurse -Force '$ProjectRoot'"
