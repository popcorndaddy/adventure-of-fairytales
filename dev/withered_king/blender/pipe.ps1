param([string]$only = "", [string]$render = "none", [string]$step = "2", [string]$yaws = "30", [string]$res = "300", [switch]$rig)
$d = 'C:\Users\Colten\Documents\Blockbench\Withered Sentinel\withered_king_blender'
$r = Join-Path $d 'run.ps1'
$q = 'C:\Users\Colten\curseforge\minecraft\Instances\Adventures of Fairytale (1)\_fix_tmp\wkq'
Get-ChildItem 'C:\Users\Colten\curseforge\minecraft\Instances\Adventures of Fairytale (1)\_fix_tmp\wk\*.py' | % { (Get-FileHash $_.FullName -Algorithm MD5).Hash.ToLower().Substring(0,8) + ' ' + $_.Name }
if ($rig) { powershell -ExecutionPolicy Bypass -File $r -script build_rig.py }
if ($only -ne "") { powershell -ExecutionPolicy Bypass -File $r -script anims.py -blend withered_king_anim.blend -args2 $only }
else { powershell -ExecutionPolicy Bypass -File $r -script anims.py -blend withered_king_rig.blend }
powershell -ExecutionPolicy Bypass -File $r -script bake.py -blend withered_king_anim.blend
New-Item -ItemType Directory -Force $q | Out-Null
Remove-Item (Join-Path $q '*') -Force -ErrorAction SilentlyContinue
if ($render -ne "none") {
  Remove-Item (Join-Path $d 'renders\*') -Force -ErrorAction SilentlyContinue
  powershell -ExecutionPolicy Bypass -File $r -script render_qc.py -blend withered_king_anim.blend -args2 "$render $step $yaws $res 10"
  Copy-Item (Join-Path $d 'renders\SHEET_*.png') $q -Force -ErrorAction SilentlyContinue
}
Copy-Item (Join-Path $d 'king_baked.json') $q -Force
