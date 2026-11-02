<#
.SYNOPSIS
  Construit dist/plugin-maths.oxt a partir du dossier extension/.
.PARAMETER Version
  Version optionnelle (ex. 0.2.0). Estampillee dans une copie de staging de
  extension/description.xml et update.xml ; les sources ne sont jamais modifiees.
.PARAMETER OutDir
  Dossier de sortie (defaut: dist).
#>
[CmdletBinding()]
param(
    [string]$Version = '',
    [string]$OutDir = 'dist'
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$root = $PSScriptRoot
if (-not $root) { $root = (Get-Location).Path }
$srcDir = Join-Path $root 'extension'
if (-not (Test-Path -LiteralPath $srcDir)) { throw "Dossier introuvable: $srcDir" }
if ($Version) {
    $Version = $Version.TrimStart('v')
    if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Version invalide '$Version' (attendu: X.Y.Z)" }
}
if (-not [System.IO.Path]::IsPathRooted($OutDir)) { $OutDir = Join-Path $root $OutDir }
$null = New-Item -ItemType Directory -Force -Path $OutDir
$OutDir = (Resolve-Path -LiteralPath $OutDir).Path

$staging = Join-Path ([System.IO.Path]::GetTempPath()) ("plugin-maths-" + [guid]::NewGuid().ToString('N'))
$stageExt = Join-Path $staging 'extension'
$oxt = Join-Path $OutDir 'plugin-maths.oxt'

try {
    Write-Host "==> Staging: $stageExt"
    $null = New-Item -ItemType Directory -Force -Path $stageExt

    $excludeDirs  = @('.git', '.vs', '__pycache__')
    $excludeFiles = @('.gitignore', '.gitattributes', 'Thumbs.db')
    $excludeExt   = @('.pyc', '.oxt')

    function Copy-Filtered([string]$from, [string]$to) {
        foreach ($item in Get-ChildItem -LiteralPath $from -Force) {
            if ($item.PSIsContainer) {
                if ($excludeDirs -contains $item.Name) { continue }
                $dest = Join-Path $to $item.Name
                $null = New-Item -ItemType Directory -Force -Path $dest
                Copy-Filtered $item.FullName $dest
            } else {
                if ($excludeFiles -contains $item.Name) { continue }
                if ($item.Name -like '.git*') { continue }
                if ($excludeExt -contains $item.Extension.ToLowerInvariant()) { continue }
                Copy-Item -LiteralPath $item.FullName -Destination (Join-Path $to $item.Name)
            }
        }
    }
    Copy-Filtered $srcDir $stageExt

    if ($Version) {
        Write-Host "==> Version: $Version"
        $enc = New-Object System.Text.UTF8Encoding($false)
        $desc = Join-Path $stageExt 'description.xml'
        $txt = [System.IO.File]::ReadAllText($desc)
        $new = [regex]::Replace($txt, '(<version\s+value=")[^"]*(")', "`${1}$Version`${2}")
        if ($new -eq $txt -and $txt -notmatch [regex]::Escape("value=`"$Version`"")) { throw 'Balise <version value=...> introuvable dans description.xml' }
        [System.IO.File]::WriteAllText($desc, $new, $enc)

        $upd = Join-Path $root 'update.xml'
        if (Test-Path -LiteralPath $upd) {
            $u = [System.IO.File]::ReadAllText($upd)
            $u = [regex]::Replace($u, '(<version\s+value=")[^"]*(")', "`${1}$Version`${2}")
            $url = "https://github.com/aifedespaix/plugin-maths/releases/download/v$Version/plugin-maths.oxt"
            $u = [regex]::Replace($u, '(<update-download>\s*<src\s+xlink:href=")[^"]*(")', "`${1}$url`${2}")
            $notes = "https://github.com/aifedespaix/plugin-maths/releases/tag/v$Version"
            $u = [regex]::Replace($u, '(<release-notes>\s*<src\s+lang="fr"\s+xlink:href=")[^"]*(")', "`${1}$notes`${2}")
            [System.IO.File]::WriteAllText((Join-Path $staging 'update.xml'), $u, $enc)
            Copy-Item -LiteralPath (Join-Path $staging 'update.xml') -Destination (Join-Path $OutDir 'update.xml') -Force
        }
    }

    if (-not (Test-Path -LiteralPath (Join-Path $stageExt 'META-INF/manifest.xml'))) {
        throw 'META-INF/manifest.xml manquant dans extension/'
    }

    if (Test-Path -LiteralPath $oxt) { Remove-Item -LiteralPath $oxt -Force }
    Write-Host "==> Archive: $oxt"
    $zip = [System.IO.Compression.ZipFile]::Open($oxt, [System.IO.Compression.ZipArchiveMode]::Create)
    try {
        $files = Get-ChildItem -LiteralPath $stageExt -Recurse -File -Force | Sort-Object FullName
        $prefix = $stageExt.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
        foreach ($f in $files) {
            # Entrees ZIP: separateurs '/' obligatoires (sinon oxt invalide)
            $name = $f.FullName.Substring($prefix.Length).Replace('\', '/')
            $entry = $zip.CreateEntry($name, [System.IO.Compression.CompressionLevel]::Optimal)
            $in = [System.IO.File]::OpenRead($f.FullName)
            try {
                $out = $entry.Open()
                try { $in.CopyTo($out) } finally { $out.Dispose() }
            } finally { $in.Dispose() }
            Write-Host "    + $name"
        }
    } finally { $zip.Dispose() }

    $size = [math]::Round((Get-Item -LiteralPath $oxt).Length / 1KB, 1)
    Write-Host "==> OK: $oxt ($size Ko)" -ForegroundColor Green
}
finally {
    if (Test-Path -LiteralPath $staging) { Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue }
}
