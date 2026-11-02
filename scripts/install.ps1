<#
.SYNOPSIS
  Installe l'extension "Maths facile pour Writer" (plugin-maths.oxt) dans LibreOffice, sans interface.
.DESCRIPTION
  - Cherche unopkg.com dans Program Files / Program Files (x86) \LibreOffice\program.
  - Verifie que LibreOffice est ferme (sinon avertit, ou le ferme avec -CloseLibreOffice).
  - Installation pour tous les utilisateurs (unopkg add --shared -f), ce qui demande les droits
    administrateur : le script se relance seul en administrateur.
    En cas d'echec ou avec -UserOnly, installation pour l'utilisateur courant (unopkg add -f).
.PARAMETER Oxt
  Chemin du fichier .oxt. Par defaut : dist\plugin-maths.oxt s'il existe, sinon la derniere release
  GitHub est telechargee.
.PARAMETER UserOnly
  Installe uniquement pour l'utilisateur courant (pas besoin d'administrateur).
.PARAMETER CloseLibreOffice
  Ferme LibreOffice s'il est ouvert (les documents non enregistres seront perdus).
#>
[CmdletBinding()]
param(
    [string]$Oxt = '',
    [switch]$UserOnly,
    [switch]$CloseLibreOffice,
    [switch]$Elevated
)
$ErrorActionPreference = 'Stop'
$ExtId = 'fr.aifedespaix.plugin-maths'
$Repo  = 'aifedespaix/plugin-maths'

function Test-Admin {
    $p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Find-Unopkg {
    $dirs = @($env:ProgramFiles, ${env:ProgramFiles(x86)}) | Where-Object { $_ }
    foreach ($d in $dirs) {
        foreach ($n in 'unopkg.com', 'unopkg.exe') {
            $c = Join-Path $d "LibreOffice\program\$n"
            if (Test-Path -LiteralPath $c) { return $c }
        }
    }
    return $null
}

function Resolve-Oxt([string]$path) {
    if ($path) {
        if (-not (Test-Path -LiteralPath $path)) { throw "Fichier introuvable : $path" }
        return (Resolve-Path -LiteralPath $path).Path
    }
    $root = Split-Path -Parent $PSScriptRoot
    $local = Join-Path $root 'dist\plugin-maths.oxt'
    if (Test-Path -LiteralPath $local) { return $local }
    Write-Host 'Telechargement de la derniere version depuis GitHub...'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $rel = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -Headers @{ 'User-Agent' = 'plugin-maths-install' }
    $asset = $rel.assets | Where-Object { $_.name -eq 'plugin-maths.oxt' } | Select-Object -First 1
    if (-not $asset) { throw 'plugin-maths.oxt est absent de la derniere release GitHub.' }
    $dest = Join-Path ([IO.Path]::GetTempPath()) 'plugin-maths.oxt'
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $dest -UseBasicParsing
    Write-Host "Version $($rel.tag_name) telechargee."
    return $dest
}

try {
    $unopkg = Find-Unopkg
    if (-not $unopkg) { throw 'LibreOffice est introuvable (unopkg absent de Program Files). Installez LibreOffice 7.4 ou plus recent.' }

    $oxtPath = Resolve-Oxt $Oxt

    $running = Get-Process -Name soffice, soffice.bin -ErrorAction SilentlyContinue
    if ($running) {
        if ($CloseLibreOffice) {
            Write-Host 'Fermeture de LibreOffice...'
            $running | Stop-Process -Force
            Start-Sleep -Seconds 2
        } else {
            Write-Warning 'LibreOffice est ouvert. Enregistrez votre travail et fermez-le, puis relancez ce script (ou ajoutez -CloseLibreOffice).'
            throw 'Installation annulee : LibreOffice est ouvert.'
        }
    }

    $shared = -not $UserOnly
    if ($shared -and -not (Test-Admin)) {
        if ($Elevated) {
            Write-Warning 'Droits administrateur indisponibles : installation pour l''utilisateur courant.'
            $shared = $false
        } else {
            Write-Host 'Demande des droits administrateur...'
            $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", '-Oxt', "`"$oxtPath`"", '-Elevated')
            if ($CloseLibreOffice) { $argList += '-CloseLibreOffice' }
            try {
                $proc = Start-Process -FilePath (Get-Process -Id $PID).Path -ArgumentList $argList -Verb RunAs -Wait -PassThru
                exit $proc.ExitCode
            } catch {
                Write-Warning 'Elevation refusee : installation pour l''utilisateur courant.'
                $shared = $false
            }
        }
    }

    $done = $false
    if ($shared) {
        Write-Host 'Installation pour tous les utilisateurs...'
        & $unopkg add --shared -f $oxtPath
        if ($LASTEXITCODE -eq 0) { $done = $true; $mode = 'tous les utilisateurs' }
        else { Write-Warning "Echec de l'installation partagee (code $LASTEXITCODE) : essai pour l'utilisateur courant." }
    }
    if (-not $done) {
        Write-Host "Installation pour l'utilisateur courant..."
        & $unopkg add -f $oxtPath
        if ($LASTEXITCODE -ne 0) { throw "unopkg a echoue (code $LASTEXITCODE)." }
        $mode = 'l''utilisateur courant'
    }

    Write-Host ''
    Write-Host "Extension installee pour $mode." -ForegroundColor Green
    Write-Host 'Ouvrez LibreOffice Writer, puis la barre laterale (Ctrl+F5) et cliquez sur "Maths".'
    if ($Elevated) { Start-Sleep -Seconds 3 }
    exit 0
}
catch {
    Write-Host ''
    Write-Host "Erreur : $($_.Exception.Message)" -ForegroundColor Red
    if ($Elevated) { Read-Host 'Appuyez sur Entree pour fermer' }
    exit 1
}
