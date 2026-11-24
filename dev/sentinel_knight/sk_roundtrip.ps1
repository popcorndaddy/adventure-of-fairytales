# Proves the GeckoLib export: compares every bone's world pose in the Blender source vs the re-imported model.
$b = "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"; $D = $PSScriptRoot; $s = "$D\preview\rt"
New-Item -ItemType Directory -Force $s | Out-Null
$acts = @{ idle = "0,37,80"; idle_combat = "0,20"; walk = "0,13,30"; sweep = "0,18,24,34"; push = "0,20,30"; stomp = "0,14,19";
           dash = "0,11,18"; summon_start = "0,30,40"; summon_loop = "0,30"; summon_end = "0,15"; awaken = "0,50,80,99"; death = "0,25,60,99"; dormant = "0,20" }
foreach ($a in $acts.Keys) {
  & $b -b "$D\sentinel_knight_anim.blend" --python "$D\sk_dump.py" -- "$s\src_$a.json" $a $acts[$a] 2>&1 | Out-Null
  & $b -b "$D\preview\all.blend" --python "$D\sk_dump.py" -- "$s\imp_$a.json" $a $acts[$a] 2>&1 | Out-Null
}
node -e "
const fs=require('fs'); const dir=process.argv[1]; let worst=0, wb='';
for (const f of fs.readdirSync(dir).filter(x=>x.startsWith('src_'))) { const a=JSON.parse(fs.readFileSync(dir+'/'+f)), b=JSON.parse(fs.readFileSync(dir+'/'+f.replace('src_','imp_')));
  let w=0, wk=''; for (const fr of Object.keys(a)) for (const k of Object.keys(a[fr])) { if(!b[fr][k]) continue; const dh=Math.hypot(...a[fr][k].h.map((x,i)=>x-b[fr][k].h[i]))*16; let dr=0; for (const c of ['rx','ry','rz']) for (let i=0;i<3;i++) dr=Math.max(dr,Math.abs(a[fr][k][c][i]-b[fr][k][c][i])); if (dh+dr*10>w){w=dh+dr*10; wk=k+'@'+fr+' head '+dh.toFixed(3)+'px rot '+dr.toFixed(4)} }
  console.log('RT', f.slice(4,-5).padEnd(13), 'worst', wk); if (w>worst){worst=w; wb=f} }
console.log('RT_DONE worst', worst.toFixed(3), wb)" $s
