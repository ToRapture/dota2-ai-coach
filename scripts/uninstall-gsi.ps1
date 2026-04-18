#Requires -Version 5.1
<#
.SYNOPSIS
  Remove gamestate_integration_coach.cfg from Dota 2.
#>
[CmdletBinding()]
param(
    [string]$DotaRoot
)

$ErrorActionPreference = 'Stop'

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

if (-not $DotaRoot) { $DotaRoot = Find-DotaRoot }
if (-not $DotaRoot) {
    Write-Warning "Dota 2 install not found; nothing to remove."
    return
}

$Target = Join-Path $DotaRoot 'game\dota\cfg\gamestate_integration\gamestate_integration_coach.cfg'
if (Test-Path $Target) {
    Remove-Item $Target -Force
    Write-Host "Removed: $Target" -ForegroundColor Green
} else {
    Write-Host "Already absent: $Target"
}
