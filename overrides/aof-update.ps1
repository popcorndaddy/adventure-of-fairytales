<#
  Adventures of Fairytale - pack updater.

  Pulls the latest pack files (scripts, configs, assets, books, menus) from the GitHub repo and copies them into
  this CurseForge instance, so everyone on the team runs the same pack. Your own settings are never touched
  (options.txt, servers, worlds, screenshots, logs). Mods can't be downloaded from here: CurseForge only lets its own
  app do that, so the updater lists any mod the pack needs that your instance is missing.

  Usage (from the instance folder, or double-click "Update Pack.bat"):
    powershell -ExecutionPolicy Bypass -File aof-update.ps1                 # update now
    powershell -ExecutionPolicy Bypass -File aof-update.ps1 -Schedule       # also update automatically at every Windows sign-in
    powershell -ExecutionPolicy Bypass -File aof-update.ps1 -Unschedule     # stop the automatic updates
    -Instance <folder>   instance folder (default: the folder this script is in)
    -Branch <name>       branch to follow (default: main, or unpack-pack while main doesn't hold the unpacked pack yet)
    -DryRun              show what would change without copying anything
    -Force               download and compare even if GitHub has no new commit since the last update
#>
param([string]$Instance = $PSScriptRoot, [string]$Branch = "", [string]$Repo = "popcorndaddy/adventure-of-fairytales",
      [switch]$Schedule, [switch]$Unschedule, [switch]$DryRun, [switch]$Quiet, [switch]$Force, [string]$ZipPath = "")
$ErrorActionPreference = 'Stop'
$TaskName = 'Adventures of Fairytale pack updater'
$Keep = @('options.txt', 'optionsof.txt', 'optionsshaders.txt', 'servers.dat')        # never overwritten
$Stamp = Join-Path $Instance '.aof-update-files.txt'                                   # files this updater installed
$ShaFile = Join-Path $Instance '.aof-update-commit.txt'                                 # commit last installed
$Log = Join-Path $Instance 'logs\aof-update.log'
function Say($m) { if (-not $Quiet) { Write-Host $m }; try { New-Item -ItemType Directory -Force (Split-Path $Log) | Out-Null; Add-Content $Log "$(Get-Date -Format s)  $m" } catch {} }

if ($Unschedule) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue; Say "Automatic updates turned off."; exit 0 }
if (-not (Test-Path (Join-Path $Instance 'mods'))) { Write-Host "'$Instance' doesn't look like a Minecraft instance (no mods folder). Pass -Instance <folder>."; exit 1 }
if ($Schedule) {
  $arg = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Instance `"$Instance`" -Quiet"
  $act = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arg
  $trg = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
  Register-ScheduledTask -TaskName $TaskName -Action $act -Trigger $trg -Description "Keeps '$Instance' in sync with github.com/$Repo" -Force | Out-Null
  Say "Automatic updates on: the pack updates every time you sign in to Windows (task '$TaskName')."
}

# ---- download the branch
$tmp = Join-Path $env:TEMP ("aof-update-" + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $tmp | Out-Null
try {
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  $branches = if ($Branch) { @($Branch) } else { @('main', 'unpack-pack') }
  $root = $null; $sha = ''
  foreach ($b in $branches) {
    $zip = Join-Path $tmp "$b.zip"
    if ($ZipPath) { Copy-Item $ZipPath $zip }
    else {
      # a tiny API call first: skip the download when nothing was pushed since the last update
      try { $sha = (Invoke-RestMethod -UseBasicParsing "https://api.github.com/repos/$Repo/commits/$b" -Headers @{ 'User-Agent' = 'aof-update' }).sha } catch { $sha = '' }
      if ($sha -and -not $Force -and -not $DryRun -and (Test-Path $ShaFile) -and ((Get-Content $ShaFile -Raw).Trim() -eq "$b $sha")) {
        Say "Adventures of Fairytale is up to date ($b @ $($sha.Substring(0, 7)))."; exit 0
      }
      try { Invoke-WebRequest -UseBasicParsing "https://codeload.github.com/$Repo/zip/refs/heads/$b" -OutFile $zip } catch { continue }
    }
    $dir = Join-Path $tmp $b; Expand-Archive $zip $dir -Force
    $r = Get-ChildItem $dir -Directory | Select-Object -First 1
    if ($r -and (Test-Path (Join-Path $r.FullName 'overrides'))) { $root = $r.FullName; $Branch = $b; break }
  }
  if (-not $root) { Say "Couldn't find the pack files on GitHub ($Repo, branches: $($branches -join ', ')). Nothing changed."; exit 1 }
  $ov = Join-Path $root 'overrides'

  # ---- copy changed files
  $old = @{}; if (Test-Path $Stamp) { Get-Content $Stamp | % { $p = $_.Split("`t"); if ($p.Count -eq 2) { $old[$p[0]] = $p[1] } } }
  $new = @{}; $added = 0; $changed = 0; $removed = 0
  Get-ChildItem $ov -Recurse -File | % {
    $rel = $_.FullName.Substring($ov.Length + 1)
    if ($Keep -contains $rel) { return }
    $h = (Get-FileHash $_.FullName -Algorithm SHA1).Hash; $new[$rel] = $h
    $dst = Join-Path $Instance $rel
    if (Test-Path $dst) {
      if ((Get-FileHash $dst -Algorithm SHA1).Hash -eq $h) { return }
      $changed++; Say "  updated  $rel"
    } else { $added++; Say "  added    $rel" }
    if (-not $DryRun) { New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null; Copy-Item $_.FullName $dst -Force }
  }
  # our own mods (overrides/mods): an older version left in mods/ would load twice and crash the game, so move it aside
  $packMods = Join-Path $ov 'mods'
  if (Test-Path $packMods) {
    $aside = Join-Path $Instance 'mods-replaced'
    Get-ChildItem $packMods -Filter *.jar | % {
      $keep = $_.Name
      if ($keep -match '^(.+?)-\d[^-]*\.jar$') {
        $id = $Matches[1]
        Get-ChildItem (Join-Path $Instance 'mods') -Filter "$id-*.jar" | ? { $_.Name -ne $keep -and $_.Name -match ('^' + [regex]::Escape($id) + '-\d[^-]*\.jar$') } | % {
          $removed++; Say "  replaced mods\$($_.Name) (moved to mods-replaced)"
          if (-not $DryRun) { New-Item -ItemType Directory -Force $aside | Out-Null; Move-Item $_.FullName (Join-Path $aside $_.Name) -Force }
        }
      }
    }
  }
  # files the updater put here earlier that the pack no longer has - removed only if you haven't edited them since
  foreach ($rel in $old.Keys) {
    if ($new.ContainsKey($rel)) { continue }
    $dst = Join-Path $Instance $rel
    if ((Test-Path $dst) -and (Get-FileHash $dst -Algorithm SHA1).Hash -eq $old[$rel]) {
      $removed++; Say "  removed  $rel"; if (-not $DryRun) { Remove-Item $dst -Force }
    }
  }
  if (-not $DryRun) { $new.GetEnumerator() | % { "$($_.Key)`t$($_.Value)" } | Set-Content $Stamp; if ($sha) { "$Branch $sha" | Set-Content $ShaFile } }

  # ---- mods the pack lists that this instance doesn't have
  $missing = @()
  $mi = Join-Path $Instance 'minecraftinstance.json'
  if (Test-Path $mi) {
    $have = @{}; (Get-Content $mi -Raw | ConvertFrom-Json).installedAddons | % { $have[[string]$_.addonID] = $true }
    $man = Get-Content (Join-Path $root 'manifest.json') -Raw | ConvertFrom-Json
    foreach ($f in $man.files) { if (-not $have[[string]$f.projectID]) { $missing += $f.projectID } }
  }
  $verb = if ($DryRun) { 'would change' } else { 'changed' }
  Say "Adventures of Fairytale ($Branch): $added added, $changed updated, $removed removed - $verb."
  if ($missing.Count) {
    Say "The pack also needs $($missing.Count) mod(s) this instance doesn't have (CurseForge project IDs: $($missing -join ', '))."
    Say "  Install them in the CurseForge app (search the mod, or re-import the pack zip). Then run this again."
  }
  if (($added + $changed + $removed) -gt 0 -and -not $DryRun) { Say "Restart Minecraft (or run /reload for data-only changes) to use the new files." }
} finally { Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue }
