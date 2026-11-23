param([string]$script, [string]$blend = "", [string]$args2 = "")
$src = 'C:\Users\Colten\curseforge\minecraft\Instances\Adventures of Fairytale (1)\_fix_tmp\wk'
$dst = 'C:\Users\Colten\Documents\Blockbench\Withered Sentinel\withered_king_blender'
Get-ChildItem $src -File | Where-Object { $_.Extension -in '.py', '.json', '.png' } | ForEach-Object { Copy-Item $_.FullName (Join-Path $dst $_.Name) -Force }
$exe = 'C:\Program Files\Blender Foundation\Blender 5.3\blender.exe'
$a = @('-b')
if ($blend -ne "") { $a += (Join-Path $dst $blend) } else { $a += '--factory-startup' }
$a += @('--python-exit-code', '1', '--python', (Join-Path $dst $script))
if ($args2 -ne "") { $a += '--'; $a += $args2.Split(' ') }
$out = & $exe @a 2>&1
$out | Where-Object { $_ -match '^(QC|CROWN|POLE|SAVED|QC|OUT|ERR|WARN|Traceback|  File|\w+Error|Error|BAKE|ANIM|CHECK|REND|INFO)' } | ForEach-Object { $_ }
"EXIT $LASTEXITCODE"


