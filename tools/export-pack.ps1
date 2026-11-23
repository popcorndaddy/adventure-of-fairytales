# Exports the Adventures of Fairytale CurseForge instance as an importable CurseForge pack zip,
# mirroring the folders of previous exports and bundling the Gatekeeper mod jar in overrides/mods.
#   powershell -ExecutionPolicy Bypass -File tools\export-pack.ps1 -Version 1.1.0
param(
    [string]$Instance = "C:\Users\richa\curseforge\minecraft\Instances\Adventures of Fairytale",
    [string]$Version = "1.2.1",
    [string]$ModJar = "$PSScriptRoot\..\gatekeeper-mod\build\libs\aof_gatekeeper-1.1.1.jar",
    [string]$Out = "$PSScriptRoot\..\Adventures-of-Fairytale-$Version.zip"
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem

$manifest = Get-Content (Join-Path $Instance "manifest.json") -Raw | ConvertFrom-Json
$manifest.name = "Adventures of Fairytale"
$manifest.version = $Version
$manifest.author = "popcorndaddy"

$Out = [System.IO.Path]::GetFullPath($Out)
if (Test-Path $Out) { Remove-Item $Out }
$zip = [System.IO.Compression.ZipFile]::Open($Out, "Create")
function Add-Text($name, $text) {
    $e = $zip.CreateEntry($name, "Optimal")
    $w = New-Object System.IO.StreamWriter($e.Open(), (New-Object System.Text.UTF8Encoding($false)))
    $w.Write($text); $w.Dispose()
}
function Add-File($path, $name) {
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $path, $name, "Optimal") | Out-Null
}

Add-Text "manifest.json" ($manifest | ConvertTo-Json -Depth 10)
$modlist = Get-Content (Join-Path $Instance "modlist.html") -Raw
$modlist = $modlist -replace "</ul>", "<li>AOF: The Gatekeeper (bundled, by popcorndaddy)</li>`n</ul>"
Add-Text "modlist.html" $modlist

$count = 0
foreach ($item in @("config", "fancymenu_data", "kubejs", "patchouli_books", "resourcepacks", "shaderpacks", "options.txt", "patchouli_data.json")) {
    $src = Join-Path $Instance $item
    if (-not (Test-Path $src)) { continue }
    if ((Get-Item $src).PSIsContainer) {
        foreach ($f in Get-ChildItem $src -Recurse -File) {
            $rel = $f.FullName.Substring($Instance.Length + 1).Replace('\', '/')
            Add-File $f.FullName "overrides/$rel"; $count++
        }
    } else {
        Add-File $src "overrides/$item"; $count++
    }
}
Add-File ([System.IO.Path]::GetFullPath($ModJar)) "overrides/mods/$([System.IO.Path]::GetFileName($ModJar))"; $count++
$zip.Dispose()
"EXPORTED $Out  ($count override files, $($manifest.files.Count) CurseForge mods, $([math]::Round((Get-Item $Out).Length / 1MB, 1)) MB)"
