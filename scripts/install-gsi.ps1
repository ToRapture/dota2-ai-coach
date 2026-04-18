#Requires -Version 5.1
<#
.SYNOPSIS
  Copy the GSI cfg into Dota 2's gamestate_integration folder.
.DESCRIPTION
  Tries to auto-detect Steam library containing Dota 2. If detection fails, pass
  -DotaRoot pointing to the folder containing "game\dota".
.PARAMETER DotaRoot
  Optional. Path to "...\Steam\steamapps\common\dota 2 beta". Auto-detected when omitted.
#>
[CmdletBinding()]
param(
    [string]$DotaRoot
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$CfgSource = Join-Path $ProjectRoot 'gsi\gamestate_integration_coach.cfg'

if (-not (Test-Path $CfgSource)) {
    throw "GSI cfg source not found: $CfgSource"
}

function Find-DotaRoot {
    $candidates = @(
        'C:\Program Files (x86)\Steam\steamapps\common\dota 2 beta',
        'D:\Steam\steamapps\common\dota 2 beta',
        'D:\SteamLibrary\steamapps\common\dota 2 beta',
        'E:\SteamLibrary\steamapps\common\dota 2 beta'
    )

    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }

    $libFile = 'C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf'
    if (Test-Path $libFile) {
        $content = Get-Content $libFile -Raw
        foreach ($m in [regex]::Matches($content, '"path"\s*"([^"]+)"')) {
            $path = $m.Groups[1].Value -replace '\\\\', '\'
            $try = Join-Path $path 'steamapps\common\dota 2 beta'
            if (Test-Path $try) { return $try }
        }
    }
    return $null
}

if (-not $DotaRoot) {
    $DotaRoot = Find-DotaRoot
    if (-not $DotaRoot) {
        throw "Cannot locate Dota 2 install. Re-run with -DotaRoot 'path\to\dota 2 beta'."
    }
}

$GsiDir = Join-Path $DotaRoot 'game\dota\cfg\gamestate_integration'
if (-not (Test-Path $GsiDir)) {
    New-Item -ItemType Directory -Path $GsiDir -Force | Out-Null
}

$Destination = Join-Path $GsiDir 'gamestate_integration_coach.cfg'
Copy-Item -Path $CfgSource -Destination $Destination -Force
Write-Host "Installed GSI config:" -ForegroundColor Green
Write-Host "  $Destination"

Write-Host ""
Write-Host "NEXT: in Steam, right-click Dota 2 -> Properties -> Launch Options," -ForegroundColor Yellow
Write-Host "      add:  -gamestateintegration"
