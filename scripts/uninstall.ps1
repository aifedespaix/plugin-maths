<#
.SYNOPSIS
  Desinstalle l'extension "Maths facile pour Writer" (fr.aifedespaix.plugin-maths).
.PARAMETER UserOnly
  Retire uniquement l'installation de l'utilisateur courant (pas besoin d'administrateur).
.PARAMETER CloseLibreOffice
  Ferme LibreOffice s'il est ouvert.
#>
[CmdletBinding()]
param(
    [switch]$UserOnly,
    [switch]$CloseLibreOffice,
    [switch]$Elevated
)
$ErrorActionPreference = 'Stop'
$ExtId = 'fr.aifedespaix.plugin-maths'

function Test-Admin {
    $p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

try {
    $unopkg = $null
    foreach ($d in @($env:ProgramFiles, ${env:ProgramFiles(x86)}) | Where-Object { $_ }) {
        foreach ($n in 'unopkg.com', 'unopkg.exe') {
            $c = Join-Path $d "LibreOffice\program\$n"
            if (-not $unopkg -and (Test-Path -LiteralPath $c)) { $unopkg = $c }
        }
    }
    if (-not $unopkg) { throw 'LibreOffice est introuvable (unopkg absent de Program Files).' }

    $running = Get-Process -Name soffice, soffice.bin -ErrorAction SilentlyContinue
    if ($running) {
        if ($CloseLibreOffice) { $running | Stop-Process -Force; Start-Sleep -Seconds 2 }
        else { throw 'LibreOffice est ouvert : fermez-le puis relancez (ou ajoutez -CloseLibreOffice).' }
    }

    if (-not $UserOnly -and -not (Test-Admin) -and -not $Elevated) {
        Write-Host 'Demande des droits administrateur...'
        $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", '-Elevated')
        if ($CloseLibreOffice) { $argList += '-CloseLibreOffice' }
        try {
            $proc = Start-Process -FilePath (Get-Process -Id $PID).Path -ArgumentList $argList -Verb RunAs -Wait -PassThru
            exit $proc.ExitCode
        } catch { Write-Warning 'Elevation refusee : seule l''installation utilisateur sera retiree.' }
    }

    $removed = $false
    if (-not $UserOnly -and (Test-Admin)) {
        & $unopkg remove --shared $ExtId
        if ($LASTEXITCODE -eq 0) { $removed = $true }
    }
    & $unopkg remove $ExtId
    if ($LASTEXITCODE -eq 0) { $removed = $true }

    if ($removed) { Write-Host 'Extension desinstallee.' -ForegroundColor Green }
    else { Write-Warning 'Aucune installation de l''extension n''a ete retiree (deja desinstallee ?).' }
    if ($Elevated) { Start-Sleep -Seconds 3 }
    exit 0
}
catch {
    Write-Host "Erreur : $($_.Exception.Message)" -ForegroundColor Red
    if ($Elevated) { Read-Host 'Appuyez sur Entree pour fermer' }
    exit 1
}
