"""Final Withered Sentinel animations: authored and solved in Blender (bl/anims.py), baked, then skirt/cape-solved and
key-reduced by qc/post.py.  Values are Blockbench additive rotations/positions with linear keys."""
import json, os
_D = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qc', 'anims_final.json')))
ORDER = ['idle', 'idle_combat', 'walk', 'sweep', 'summon_start', 'summon_loop', 'summon_end', 'push', 'awaken', 'stomp', 'dash', 'death']
ANIMS = [dict(_D[n], bones={b: {ch: [(t, tuple(v)) for t, v in keys] for ch, keys in chs.items()} for b, chs in _D[n]['bones'].items()}) for n in ORDER if n in _D]
