# Export all actions -> import with the GeckoLib importer -> glow -> one 3-angle sheet per action (key frames as rows).
param([string]$Only = "", [switch]$NoBake)
$b = "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"
$D = $PSScriptRoot; $A = "$D\out_assets"; $P = "$D\preview"; $T = "$PSScriptRoot\tools"
New-Item -ItemType Directory -Force "$P\sheets" | Out-Null
if (-not $NoBake) { & $b -b "$D\sentinel_knight.blend" --python "$D\sk_anims.py" -- $Only 2>&1 | Select-String -Pattern "Traceback|Error|line \d|ANIMS_DONE" }
& $b -b "$D\sentinel_knight_anim.blend" --python "$D\sk_export.py" -- $A --anims 2>&1 | Select-String -Pattern "Traceback|Error|line \d|ANIMS_OK|GEO_OK"
& $b -b --python "$T\geckolib_blender.py" -- import "$A\geo\entity\withered_sentinel.geo.json" "$A\animations\entity\withered_sentinel.animation.json" "$A\textures\entity\withered_sentinel.png" "$P\all.blend" 2>&1 | Select-String "Traceback|IMPORT_OK"
& $b -b "$P\all.blend" --python "$T\add_glow.py" -- "$A\textures\entity\withered_sentinel_glowmask.png" 6 2>&1 | Select-String "Traceback|GLOW_OK"
$KEYS = @{ idle = "0,30,62"; idle_combat = "0,20,40"; walk = "0,12,24,36"; sweep = "0,16,24,32"; push = "0,14,20,32"; stomp = "0,13,19,30";
           dash = "0,7,12,19"; summon_start = "0,16,30,40"; summon_loop = "0,30"; summon_end = "0,10,15,26"; awaken = "0,40,62,80,99"; death = "0,14,30,60,99" }
foreach ($k in $KEYS.Keys) {
    if ($Only -and -not ($Only.Split(",") -contains $k)) { continue }
    & $b -b "$P\all.blend" --python "$D\sk_review.py" -- "$P\sheets\$k.png" $k $KEYS[$k] "front34,side,back34" 2>&1 | Select-String "Traceback|REVIEW_OK"
}
