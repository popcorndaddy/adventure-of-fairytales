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
$ProgressPreference = 'SilentlyContinue'                                              # the progress bar makes Invoke-WebRequest crawl in Windows PowerShell
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

# git's id for a file's content ("blob <size>\0" + bytes, SHA-1): matches the ids in GitHub's file list
function BlobSha([string]$path) {
  $bytes = [IO.File]::ReadAllBytes($path)
  $hdr = [Text.Encoding]::ASCII.GetBytes("blob $($bytes.Length)`0")
  $h = [Security.Cryptography.SHA1]::Create()
  [void]$h.TransformBlock($hdr, 0, $hdr.Length, $null, 0); [void]$h.TransformFinalBlock($bytes, 0, $bytes.Length)
  -join ($h.Hash | % { $_.ToString('x2') })
}
function FileSha1([string]$path) { (Get-FileHash $path -Algorithm SHA1).Hash }

# ---- find the pack files: GitHub's file list for the branch (only changed files get downloaded), or a local zip
$tmp = Join-Path $env:TEMP ("aof-update-" + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $tmp | Out-Null
try {
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  $hdrs = @{ 'User-Agent' = 'aof-update' }
  $entries = @(); $manifest = $null; $sha = ''; $apiErr = ''
  if ($ZipPath) {
    $dir = Join-Path $tmp 'zip'; Expand-Archive $ZipPath $dir -Force
    $r = Get-ChildItem $dir -Directory | ? { Test-Path (Join-Path $_.FullName 'overrides') } | Select-Object -First 1
    if (-not $r) { Say "That zip has no overrides folder. Nothing changed."; exit 1 }
    $ov = Join-Path $r.FullName 'overrides'; $manifest = Join-Path $r.FullName 'manifest.json'
    if (-not $Branch) { $Branch = 'zip' }
    Get-ChildItem $ov -Recurse -File | % { $entries += [pscustomobject]@{ Rel = $_.FullName.Substring($ov.Length + 1); Sha = (BlobSha $_.FullName); Src = $_.FullName; Url = $null } }
  } else {
    $branches = if ($Branch) { @($Branch) } else { @('main', 'unpack-pack') }
    foreach ($b in $branches) {
      try { $c = Invoke-RestMethod -UseBasicParsing "https://api.github.com/repos/$Repo/commits/$b" -Headers $hdrs }
      catch { if ("$_" -match 'rate limit') { $apiErr = "GitHub only answers 60 update checks an hour per network; try again in a while." }; continue }
      if (-not $Force -and -not $DryRun -and (Test-Path $ShaFile) -and ((Get-Content $ShaFile -Raw).Trim() -eq "$b $($c.sha)")) {
        Say "Adventures of Fairytale is up to date ($b @ $($c.sha.Substring(0, 7)))."; exit 0
      }
      try { $tree = Invoke-RestMethod -UseBasicParsing "https://api.github.com/repos/$Repo/git/trees/$($c.sha)?recursive=1" -Headers $hdrs }
      catch { if ("$_" -match 'rate limit') { $apiErr = "GitHub only answers 60 update checks an hour per network; try again in a while." }; continue }
      $files = @($tree.tree | ? { $_.type -eq 'blob' -and $_.path.StartsWith('overrides/') })
      if (-not $files.Count) { continue }                                    # this branch doesn't hold the unpacked pack
      if ($tree.truncated) { Say "GitHub's file list for '$b' was cut short; some files may be missed this time." }
      $sha = $c.sha; $Branch = $b
      foreach ($f in $files) {
        $url = "https://raw.githubusercontent.com/$Repo/$sha/" + (($f.path -split '/' | % { [Uri]::EscapeDataString($_) }) -join '/')
        $entries += [pscustomobject]@{ Rel = $f.path.Substring(10).Replace('/', '\'); Sha = $f.sha; Src = $null; Url = $url }
      }
      $manifest = Join-Path $tmp 'manifest.json'
      try { Invoke-WebRequest -UseBasicParsing "https://raw.githubusercontent.com/$Repo/$sha/manifest.json" -OutFile $manifest } catch { $manifest = $null }
      break
    }
    if (-not $entries.Count) {
      if ($apiErr) { Say "$apiErr Nothing changed."; exit 1 }
      Say "Couldn't find the pack files on GitHub ($Repo, branches: $($branches -join ', ')). Nothing changed."; exit 1
    }
  }

  # ---- copy changed files
  $old = @{}; if (Test-Path $Stamp) { Get-Content $Stamp | % { $p = $_.Split("`t"); if ($p.Count -eq 2) { $old[$p[0]] = $p[1] } } }
  $new = @{}; $added = 0; $changed = 0; $removed = 0; $failed = 0
  foreach ($e in $entries) {
    $rel = $e.Rel
    if ($Keep -contains $rel) { continue }
    $new[$rel] = $e.Sha
    $dst = Join-Path $Instance $rel
    if (Test-Path $dst) {
      if ((BlobSha $dst) -eq $e.Sha) { continue }
      $what = 'updated '
    } else { $what = 'added   ' }
    if ($DryRun) { if ($what -eq 'added   ') { $added++ } else { $changed++ }; Say "  $what $rel"; continue }
    $part = Join-Path $tmp ([guid]::NewGuid().ToString('N'))
    try {
      if ($e.Url) { Invoke-WebRequest -UseBasicParsing $e.Url -OutFile $part } else { Copy-Item $e.Src $part }
      if ((BlobSha $part) -ne $e.Sha) { throw "the download didn't match GitHub's copy" }
      New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null; Move-Item $part $dst -Force
      if ($what -eq 'added   ') { $added++ } else { $changed++ }; Say "  $what $rel"
    } catch { $failed++; $new.Remove($rel); Say "  FAILED   $rel ($($_.Exception.Message))" }
  }
  # our own mods (overrides/mods): an older version left in mods/ would load twice and crash the game, so move it aside
  $aside = Join-Path $Instance 'mods-replaced'
  foreach ($e in ($entries | ? { $_.Rel -match '^mods\\[^\\]+\.jar$' })) {
    $keep = Split-Path $e.Rel -Leaf
    if ($keep -match '^(.+?)-\d[^-]*\.jar$') {
      $id = $Matches[1]
      Get-ChildItem (Join-Path $Instance 'mods') -Filter "$id-*.jar" | ? { $_.Name -ne $keep -and $_.Name -match ('^' + [regex]::Escape($id) + '-\d[^-]*\.jar$') } | % {
        $removed++; Say "  replaced mods\$($_.Name) (moved to mods-replaced)"
        if (-not $DryRun) { New-Item -ItemType Directory -Force $aside | Out-Null; Move-Item $_.FullName (Join-Path $aside $_.Name) -Force }
      }
    }
  }
  # files the updater put here earlier that the pack no longer has - removed only if you haven't edited them since
  foreach ($rel in $old.Keys) {
    if ($new.ContainsKey($rel)) { continue }
    $dst = Join-Path $Instance $rel
    if ((Test-Path $dst) -and ((BlobSha $dst) -eq $old[$rel] -or (FileSha1 $dst) -eq $old[$rel])) {
      $removed++; Say "  removed  $rel"; if (-not $DryRun) { Remove-Item $dst -Force }
    }
  }
  if (-not $DryRun) {
    # keep entries for files that failed this time so they are retried and never treated as removed
    foreach ($k in $old.Keys) { if (-not $new.ContainsKey($k) -and ($entries | ? { $_.Rel -eq $k })) { $new[$k] = $old[$k] } }
    $new.GetEnumerator() | % { "$($_.Key)`t$($_.Value)" } | Set-Content $Stamp
    if ($sha -and -not $failed) { "$Branch $sha" | Set-Content $ShaFile }
  }

  # ---- mods the pack lists that this instance doesn't have
  $missing = @()
  $mi = Join-Path $Instance 'minecraftinstance.json'
  if ((Test-Path $mi) -and $manifest -and (Test-Path $manifest)) {
    $have = @{}; (Get-Content $mi -Raw | ConvertFrom-Json).installedAddons | % { $have[[string]$_.addonID] = $true }
    $man = Get-Content $manifest -Raw | ConvertFrom-Json
    # CurseForge mods the pack ships itself in overrides/mods (open licence), so a locked CurseForge profile still gets them
    $bundled = @{ '967617' = 'entityjs-forge-*.jar' }
    foreach ($f in $man.files) {
      $id = [string]$f.projectID
      if ($have[$id]) { continue }
      if ($bundled.ContainsKey($id) -and (Get-ChildItem (Join-Path $Instance 'mods') -Filter $bundled[$id] -ErrorAction SilentlyContinue)) { continue }
      $missing += $f.projectID
    }
  }
  $verb = if ($DryRun) { 'would change' } else { 'changed' }
  Say "Adventures of Fairytale ($Branch): $added added, $changed updated, $removed removed - $verb."
  if ($failed) { Say "$failed file(s) couldn't be downloaded; run the updater again to retry them." }
  if ($missing.Count) {
    Say "The pack also needs $($missing.Count) mod(s) this instance doesn't have (CurseForge project IDs: $($missing -join ', '))."
    Say "  Install them in the CurseForge app (search the mod, or re-import the pack zip). Then run this again."
  }
  if (($added + $changed + $removed) -gt 0 -and -not $DryRun) { Say "Restart Minecraft (or run /reload for data-only changes) to use the new files." }
} finally { Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue }
