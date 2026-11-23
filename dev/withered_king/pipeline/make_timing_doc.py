"""Writes TIMING.md: every animation's stages, animation events and the server effects keyed to them."""
import json, sys
B = json.load(open(sys.argv[1])); TR = 4
STAGES = {
 'withered_king_idle': [('loop', 0, 6.0)],
 'withered_king_walk_drag': [('loop (one stride each foot)', 0, 2.4)],
 'withered_king_sweep': [('anticipation', 0, 0.8), ('swing', 0.8, 1.25), ('follow-through', 1.25, 1.9), ('recovery', 1.9, 2.85)],
 'withered_king_dash': [('preparation', 0, 0.9), ('dash', 0.9, 1.5), ('brake / recovery', 1.5, 2.5)],
 'withered_king_phase_transition': [('faltering', 0, 1.25), ('planting the sword', 1.25, 2.55), ('kneeling', 2.55, 4.5)],
 'withered_king_kneeling': [('loop (summoning, protected)', 0, 3.0)],
 'withered_king_phase_two_roar': [('awakening', 0, 1.0), ('rising', 1.0, 2.9), ('roar / howl', 2.9, 5.2)],
 'withered_king_hand_shockwave': [('anticipation', 0, 0.65), ('release', 0.65, 0.95), ('recovery', 0.95, 2.2)],
 'withered_king_ground_stomp': [('anticipation', 0, 1.15), ('stomp', 1.15, 1.42), ('recovery', 1.42, 2.7)],
 'withered_king_death': [('mortal injury', 0, 1.3), ('collapse to one knee', 1.3, 3.1), ('planting the sword', 3.1, 4.4), ('removing the crown', 4.4, 6.3),
                         ('crown onto the sword', 6.3, 8.4), ('final breath and death', 8.4, 10.0), ('hold', 10.0, 10.5)]}
SERVER = {
 'withered_king_sweep': [(0.0, 'faces the target until 0.6 s, then the swing direction is locked'), (0.3, 'scrape particles + grind sound at the blade point (0.3-0.8 s)'),
   (0.85, 'damage window opens: the baked blade (grip to tip) is swept through the world every tick; each target hit once'), (0.9, 'sweep whoosh'), (1.3, 'damage window closes')],
 'withered_king_dash': [(0.0, 'faces the target'), (0.75, 'direction locked (no homing after this)'), (0.9, 'entity starts moving: per-tick distance table from the animation (7.8 blocks total)'),
   (0.9, 'players in his path: damage + thrown ahead of him; stops at walls and ledges'), (1.5, 'movement ends, brake dust')],
 'withered_king_phase_transition': [(0.0, 'protected from here (no damage, no knockback, no turning)'), (2.35, 'sword impact sound + debris at the blade point'), (4.5, 'pose -> kneeling loop')],
 'withered_king_kneeling': [(0.0, 'aura (ring + motes); heartbeat rises'), (1.2, 'minions summoned in a safe ring and tracked by UUID'), (1.5, 'every 0.5 s: alive check, stray/stuck minions pulled back; timeout after 180 s'), (0.0, 'last minion dead -> roar')],
 'withered_king_phase_two_roar': [(0.1, 'rumble'), (2.6, 'sword wrenched out: debris'), (3.05, 'howl: roar + thunder + metallic ring, dark burst, dust, darkness on players within 32, gentle shove'), (5.2, 'damageable again; phase two')],
 'withered_king_hand_shockwave': [(0.0, 'faces the target until 0.55 s'), (0.2, 'palm charge'), (0.82, 'cone (40 deg, 9 blocks) from the palm: damage + throw ~6.5 blocks by real velocity')],
 'withered_king_ground_stomp': [(0.0, 'faces the target until 0.7 s'), (1.38, 'impact at the left foot; ring expands 0.6 blocks/tick to 12 blocks (1 s); fragments + debris follow the ring; players hit when it reaches them (once, not if 1.1+ blocks in the air)')],
 'withered_king_death': [(0.0, 'protected, AI stopped, minions removed'), (4.05, 'sword impact'), (5.3, 'crown lifted'), (7.55, 'crown set on the guard: chain + resonance'), (9.1, 'last breath'),
   (10.0, 'bell + beacon fade, dust settles, combat music stopped'), (10.5, 'loot table + XP (credited to the killer), then the body dissolves (or becomes the monument if enabled)')]}
out = ['# The Withered King - timing and events', '',
       'Times are animation seconds. The server triggers an animation and the client blends into it over 4 ticks, so every',
       f'server effect is scheduled at `round(t x 20) + {TR}` ticks after the trigger. Event names come straight from the Blender actions',
       '(they are stored on each action and exported with the bake).', '']
for name in STAGES:
    a = B[name]
    out += [f'## `{name}` ({a["length"]} s, {"loop" if a["loop"] == "loop" else "hold last frame" if a["loop"] == "hold" else "play once"})', '',
            '| Stage | From | To |', '|---|---|---|'] + [f'| {s} | {t0:.2f} | {t1:.2f} |' for s, t0, t1 in STAGES[name]] + ['']
    if a['events']:
        out += ['Animation events: ' + ', '.join(f'`{e["kind"]}`{"(" + e["side"] + ")" if "side" in e else ""} {e["t"]:.2f}' for e in a['events']), '']
    if name in SERVER:
        out += ['| Server tick | Anim s | What happens |', '|---|---|---|'] + [f'| {round(t * 20) + TR} | {t:.2f} | {w} |' for t, w in SERVER[name]] + ['']
open(sys.argv[2], 'w').write('\n'.join(out) + '\n')
print('wrote', sys.argv[2])
