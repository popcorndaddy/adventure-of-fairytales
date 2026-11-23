# Export all actions -> import with the GeckoLib importer -> glow -> one 3-angle sheet per action (key frames as rows).
param([string]$Only = "", [switch]$NoBake)
$b = "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"
$D = $PSScriptRoot; $A = "$D\out_assets"; $P = "$D\preview"; $T = "$PSScriptRoot\tools"
New-Item -ItemType Directory -Force "$P\sheets" | Out-Null
if (-not $NoBake) { & $b -b "$D\sentinel_knight.blend" --python "$D\sk_anims.py" -- $Only 2>&1 | Select-String -Pattern "Traceback|Error|line \d|ANIMS_DONE" }
# animations only: the anim .blend still carries the geometry it was first baked with, so its geo/texture are not used
$X = "$env:TEMP\ws_animexp"
& $b -b "$D\sentinel_knight_anim.blend" --python "$D\sk_export.py" -- $X --anims 2>&1 | Select-String -Pattern "Traceback|Error|line \d|ANIMS_OK"
Copy-Item "$X\animations\entity\withered_sentinel.animation.json" "$A\animations\entity\" -Force
& $b -b --python "$T\geckolib_blender.py" -- import "$A\geo\entity\withered_sentinel.geo.json" "$A\animations\entity\withered_sentinel.animation.json" "$A\textures\entity\withered_sentinel.png" "$P\all.blend" 2>&1 | Select-String "Traceback|IMPORT_OK"
& $b -b "$P\all.blend" --python "$T\add_glow.py" -- "$A\textures\entity\withered_sentinel_glowmask.png" 6 2>&1 | Select-String "Traceback|GLOW_OK"
$KEYS = @{ idle = "0,30,62"; idle_combat = "0,20,40"; walk = "0,12,24,36"; sweep = "0,18,24,28,36,50"; push = "0,10,15,20,30"; stomp = "0,13,19,30";
           dash = "0,8,14,18,22"; summon_start = "0,16,30,40"; summon_loop = "0,30"; summon_end = "0,10,15,26"; awaken = "0,40,62,80,99"; death = "0,14,30,60,99" }
foreach ($k in $KEYS.Keys) {
    if ($Only -and -not ($Only.Split(",") -contains $k)) { continue }
    & $b -b "$P\all.blend" --python "$D\sk_review.py" -- "$P\sheets\$k.png" $k $KEYS[$k] "front34,side,back34" 2>&1 | Select-String "Traceback|REVIEW_OK"
}
