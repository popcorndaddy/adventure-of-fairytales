# Build -> export -> re-import with the independent GeckoLib importer -> glow -> review render.
# The review shows exactly what GeckoLib will draw.  Usage: .\sk_cycle.ps1 -Tag v2 [-Anims] [-Action rest] [-Frames 0] [-Views ...]
param([string]$Tag = "v", [switch]$Anims, [string]$Action = "rest", [string]$Frames = "0", [string]$Views = "front34,side,back34,front_close", [switch]$NoBuild)
$b = "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"
$D = $PSScriptRoot; $A = "$D\out_assets"; $P = "$D\preview"; $T = "$PSScriptRoot\tools"
New-Item -ItemType Directory -Force $P | Out-Null
if (-not $NoBuild) { & $b -b --python "$D\sk_build.py" -- "$D\sentinel_knight.blend" 2>&1 | Select-String -Pattern "Traceback|Error|line \d|BUILD_OK" }
if ($Anims) { & $b -b "$D\sentinel_knight_anim.blend" --python "$D\sk_export.py" -- $A --anims 2>&1 | Select-String -Pattern "Traceback|Error|line \d|ATLAS|GEO_OK|ANIM|EXPORT_OK"; $anim = "$A\animations\entity\withered_sentinel.animation.json" }
else { & $b -b "$D\sentinel_knight.blend" --python "$D\sk_export.py" -- $A 2>&1 | Select-String -Pattern "Traceback|Error|line \d|ATLAS|GEO_OK|EXPORT_OK"
       '{"format_version":"1.8.0","animations":{"animation.withered_sentinel.rest":{"animation_length":0.05,"bones":{}}}}' | Set-Content "$P\rest.animation.json" -Encoding ascii; $anim = "$P\rest.animation.json" }
& $b -b --python "$T\geckolib_blender.py" -- import "$A\geo\entity\withered_sentinel.geo.json" $anim "$A\textures\entity\withered_sentinel.png" "$P\$Tag.blend" 2>&1 | Select-String "Traceback|IMPORT_OK"
& $b -b "$P\$Tag.blend" --python "$T\add_glow.py" -- "$A\textures\entity\withered_sentinel_glowmask.png" 6 2>&1 | Select-String "Traceback|GLOW_OK"
& $b -b "$P\$Tag.blend" --python "$D\sk_review.py" -- "$P\$Tag.png" $Action $Frames $Views 2>&1 | Select-String "Traceback|REVIEW_OK"
