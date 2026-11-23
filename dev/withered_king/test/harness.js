// Node harness for withered_king.js: fakes just enough of KubeJS / EntityJS / Minecraft to run the server-side fight
// logic tick by tick on flat stone ground. It checks the state machine and the hit logic - not rendering, not the real
// game. Run: node test/harness.js
const fs = require('fs'), path = require('path'), assert = require('assert')
const ROOT = path.join(__dirname, '..', '..', '..', 'overrides', 'kubejs', 'startup_scripts', 'bosses')
let log = [], cmds = [], scheduled = []
const vec = (x, y, z) => ({ x, y, z })
class Tag { constructor() { this.m = new Map() }
  contains(k) { return this.m.has(k) } putString(k, v) { this.m.set(k, String(v)) } getString(k) { return this.m.has(k) ? this.m.get(k) : '' }
  putInt(k, v) { this.m.set(k, v | 0) } getInt(k) { return this.m.get(k) || 0 } putFloat(k, v) { this.m.set(k, +v) } getFloat(k) { return this.m.get(k) || 0 }
  putDouble(k, v) { this.m.set(k, +v) } getDouble(k) { return this.m.get(k) || 0 } putBoolean(k, v) { this.m.set(k, !!v) } getBoolean(k) { return !!this.m.get(k) } }
let uid = 0
const GROUND = 64
const level = {
  ents: [], dimension: 'minecraft:overworld', isClientSide: () => false,
  get players() { const a = this.ents.filter(e => e.isPlayer()); a.forEach = Array.prototype.forEach; return a },
  getEntities(except, box) { const r = this.ents.filter(e => e !== except && !e.removed && e.p.x >= box.a && e.p.x <= box.d && e.p.y >= box.b - 2 && e.p.y <= box.e && e.p.z >= box.c && e.p.z <= box.f); return r },
  getBlock(x, y, z) { const solid = y < GROUND; return { id: solid ? 'minecraft:stone' : 'minecraft:air', pos: { x, y, z },
    blockState: { isAir: () => !solid, isSolidRender: () => solid, getFluidState: () => ({ isEmpty: () => true }) } } },
  getEntity(u) { return this.ents.find(e => e.uuid == String(u) && !e.removed) || null },
  getPlayerByUUID(u) { return this.ents.find(e => e.isPlayer() && e.uuid == String(u)) || null },
  getNearestPlayer(from, r) { let best = null, bd = r; this.ents.filter(e => e.isPlayer()).forEach(p => { const d = Math.hypot(p.p.x - from.p.x, p.p.z - from.p.z); if (d < bd) { bd = d; best = p } }); return best },
  broadcastEntityEvent() {}
}
class Ent {
  constructor(type, x, y, z, opts = {}) { Object.assign(this, { type, p: vec(x, y, z), uuid: 'u' + (++uid), hp: opts.hp || 20, maxHp: opts.hp || 20, tags: new Set(opts.tags || []),
    removed: false, w: opts.w || 0.6, h: opts.h || 1.8, player: !!opts.player, hits: [], vel: null, persistentData: new Tag(), tickCount: 0, yaw: 0, pose: 'STANDING', target: null, triggers: [] }) ; level.ents.push(this) }
  position() { return this.p } blockPosition() { return { getX: () => Math.floor(this.p.x), getY: () => Math.floor(this.p.y), getZ: () => Math.floor(this.p.z) } }
  isPlayer() { return this.player } isLiving() { return true } isAlive() { return !this.removed && this.hp > 0 } isCreative() { return false } isSpectator() { return false }
  getStringUuid() { return this.uuid } getTags() { const t = this.tags; return { contains: k => t.has(k) } } removeTag(k) { this.tags.delete(k) }
  getBbWidth() { return this.w } getBbHeight() { return this.h }
  getBoundingBox() { return { minX: this.p.x - this.w / 2, maxX: this.p.x + this.w / 2, minY: this.p.y, maxY: this.p.y + this.h, minZ: this.p.z - this.w / 2, maxZ: this.p.z + this.w / 2 } }
  attack(src, dmg) { this.hits.push({ dmg, tick: T }); this.hp -= dmg; return true }
  setDeltaMovement(v) { this.vel = v } getDeltaMovement() { return this.vel || vec(0, 0, 0) }
  setTarget(t) { this.target = t } getTarget() { return this.target } discard() { this.removed = true } teleportTo(x, y, z) { this.p = vec(x, y, z) }
  isInWall() { return false } isInLava() { return false }
}
const server = { runCommandSilent(c) { cmds.push({ T, c }); const m = c.match(/summon (minecraft:\w+) (\S+) (\S+) (\S+) \{Tags:\["([^"]+)","wk_minion","wk_new"\]/); if (m) new Ent(m[1], +m[2], +m[3], +m[4], { tags: [m[5], 'wk_minion', 'wk_new'], hp: 20 }) },
  scheduleInTicks(n, f) { scheduled.push({ at: T + n, f }) }, get players() { return level.players } }
// ---- KubeJS / EntityJS / Java fakes
const builders = {}, forge = {}
function builder(name) { const cb = {}; const p = new Proxy({}, { get: (_, k) => (...a) => { cb[k] = a; return p } }); builders[name] = cb; return p }
global.StartupEvents = { registry: (t, f) => f({ create: n => builder(n) }) }
global.ForgeEvents = { onEvent: (n, f) => { forge[n.split('.').pop()] = f } }
global.JsonIO = { read: () => null, write: () => {} }
global.Text = { of: s => ({ darkAqua() { return this } }) }
global.Java = { loadClass: n => ({
  'net.minecraft.world.entity.ai.attributes.Attributes': {},
  'net.minecraft.world.phys.AABB': function (a, b, c, d, e, f) { Object.assign(this, { a, b, c, d, e, f }) },
  'net.minecraft.server.level.ServerBossEvent': function () { this.setProgress = () => {}; this.setColor = () => {}; this.addPlayer = () => {}; this.removePlayer = () => {}; this.removeAllPlayers = () => {} },
  'net.minecraft.world.BossEvent$BossBarColor': { BLUE: 'BLUE', PURPLE: 'PURPLE' }, 'net.minecraft.world.BossEvent$BossBarOverlay': { NOTCHED_10: 'N10' },
  'net.minecraft.world.phys.Vec3': function (x, y, z) { Object.assign(this, { x, y, z }) },
  'net.minecraft.world.entity.Pose': { valueOf: s => s }, 'java.util.UUID': { fromString: s => s } }[n]) }
let src = fs.readFileSync(path.join(ROOT, 'withered_king.js'), 'utf8').replace(/^(const|let) /gm, 'var ')
eval(fs.readFileSync(path.join(ROOT, 'withered_king_data.js'), 'utf8'))
eval(src)
const B = builders['withered_king']
const tickCb = B.tick[0], invCb = B.isInvulnerableTo[0], deathCb = B.tickDeath[0]
// ---- the boss
let T = 0
function makeBoss() {
  const b = new Ent('kubejs:withered_king', 0.5, GROUND, 0.5, { w: 3, h: 8.6, hp: WKC.boss.health })
  Object.assign(b, { level, server, getHealth() { return this.hp }, setHealth(v) { this.hp = v }, getMaxHealth() { return this.maxHp },
    getYRot() { return this.yaw }, setYRot(v) { this.yaw = v }, setYHeadRot() {}, setYBodyRot() {}, setAggressive() {}, hasLineOfSight: () => true, horizontalCollision: false,
    nav: { going: false, stop() { this.going = false }, moveTo() { this.going = true; return true }, isInProgress() { return this.going } },
    getNavigation() { return this.nav }, setPose(p) { this.pose = p }, getPose() { return this.pose },
    triggerAnimation(c, n) { this.triggers.push({ T, n }) }, stopTriggeredAnimation() {}, damageSources: () => ({ mobAttack: () => 'mob' }),
    killed: false, kill() { this.killed = true; this.hp = 0 }, setLastHurtByPlayer(p) { this.lastPlayer = p }, isDeadOrDying() { return this.hp <= 0 } })
  return b
}
function step(b, n = 1) {
  for (let i = 0; i < n; i++) {
    T++; b.tickCount++
    if (b.killed) deathCb(b); else tickCb(b)
    if (b.vel) { b.p = vec(b.p.x + b.vel.x, b.p.y, b.p.z + b.vel.z); b.vel = null }       // travel()
    level.ents.forEach(e => { if (e !== b && e.vel) { e.p = vec(e.p.x + e.vel.x * 3, e.p.y, e.p.z + e.vel.z * 3); e.vel = null } })
    scheduled.filter(s => s.at <= T).forEach(s => s.f()); scheduled = scheduled.filter(s => s.at > T)
  }
}
function hurt(b, amount, attacker) {       // LivingAttackEvent then LivingDamageEvent, as Forge fires them
  let canceled = false
  const src = { getMsgId: () => 'player', getEntity: () => attacker }
  forge.LivingAttackEvent({ getEntity: () => b, getSource: () => src, setCanceled: v => { canceled = v } })
  if (canceled || invCb({ entity: b, damageSource: src })) return 0
  let amt = amount
  forge.LivingDamageEvent({ getEntity: () => b, getSource: () => src, getAmount: () => amt, setAmount: v => { amt = v }, setCanceled: v => { canceled = v } })
  if (canceled) return 0
  b.hp -= amt; return amt
}
const state = b => global.wkState(b)
let pass = 0; const ok = (c, m) => { assert.ok(c, m); pass++; console.log('  ok -', m) }

console.log('1. phase one: sweep hits along the blade, frontal only, once')
const boss = makeBoss()
const front = new Ent('player', 0.5, GROUND, 4.5, { player: true, hp: 1000 }), back = new Ent('player', 0.5, GROUND, -4.5, { player: true, hp: 1000 })
boss.target = front
step(boss, 25)
ok(boss.triggers.some(t => t.n == 'sweep'), 'he starts a sweep at a player 4 blocks in front')
const sw = boss.triggers.find(t => t.n == 'sweep').T
step(boss, 70)
ok(front.hits.length == 1, `front player hit exactly once (hits ${front.hits.length})`)
const hitAnim = (front.hits[0].tick - sw - WK_TRANS) / 20
ok(hitAnim >= 0.85 && hitAnim <= 1.3, `hit lands inside the swing frames (anim time ${hitAnim.toFixed(2)} s)`)
ok(back.hits.length == 0, 'player behind him is not hit')
back.removed = true
const r9 = Math.random; Math.random = () => 0.0; step(boss, 400); Math.random = r9
ok(!boss.triggers.some(t => t.n == 'ground_stomp' || t.n == 'hand_shockwave'), 'no phase-two specials during phase one (400 ticks at close range)')

console.log('2. phase gate at 50%, protected kneel, minions, roar')
front.p = vec(0.5, GROUND, 30); boss.target = null; step(boss, 5)
hurt(boss, boss.hp - boss.maxHp * 0.55, front)
const dealt = hurt(boss, 500, front)
ok(Math.abs(boss.hp - (boss.maxHp * 0.5 + 0.5)) < 1e-6, `a 500 hit stops at the gate (hp ${boss.hp.toFixed(1)} / ${boss.maxHp})`)
step(boss, 1)
ok(state(boss) == 'PHASE_TRANSITION', `transition starts (${state(boss)})`)
ok(hurt(boss, 50, front) == 0, 'no damage during the transition')
step(boss, wkLen('TRANSITION') + 2)
ok(state(boss) == 'KNEELING_INVULNERABLE' && boss.pose == 'SITTING', `kneeling, pose ${boss.pose}`)
step(boss, 30)
const minions = level.ents.filter(e => e.tags.has('wk_minion'))
ok(minions.length == 6, `six minions summoned (${minions.length})`)
ok(minions.every(m => Math.hypot(m.p.x - boss.p.x, m.p.z - boss.p.z) > 3), 'minions spawn in a ring, not on top of him')
const stranger = new Ent('minecraft:zombie', 3, GROUND, 3, { hp: 20 })
ok(hurt(boss, 50, front) == 0, 'no damage while kneeling')
minions.forEach(m => { m.hp = 0; m.removed = true })
step(boss, 20)
ok(state(boss).startsWith('PHASE_TWO_RISE') || state(boss).startsWith('PHASE_TWO_ROAR'), `an unrelated zombie doesn't hold him down; he rises (${state(boss)})`)
ok(hurt(boss, 50, front) == 0, 'no damage while rising')
step(boss, wkLen('ROAR') + 3)
ok(state(boss) == 'PHASE_TWO_COMBAT', `phase two after the roar (${state(boss)})`)
ok(hurt(boss, 10, front) > 0, 'damageable again')
ok(cmds.some(c => /darkness/.test(c.c)), 'the howl darkens nearby players')
stranger.removed = true

console.log('3. ground stomp ring')
boss.persistentData.putInt('cd_special', 0); boss.persistentData.putInt('cd_stomp', 0); boss.persistentData.putInt('wk_gap', 0)
const bx = boss.p.x, bz = boss.p.z
const near = new Ent('player', bx, GROUND, bz + 5, { player: true, hp: 1000 }), mid = new Ent('player', bx + 8, GROUND, bz, { player: true, hp: 1000 })
const jumper = new Ent('player', bx - 6.5, GROUND + 2, bz, { player: true, hp: 1000 }), far = new Ent('player', bx, GROUND, bz + 15.5, { player: true, hp: 1000 })
boss.target = near; front.removed = true
const r0 = Math.random; Math.random = () => 0.01
let guard = 0; while (!boss.triggers.some(t => t.n == 'ground_stomp') && guard++ < 200) step(boss, 1)
Math.random = r0
ok(boss.triggers.some(t => t.n == 'ground_stomp'), 'stomp chosen in phase two with a player close')
const st = T
step(boss, wkLen('STOMP') + 2)
const imp = st + Math.round(1.38 * 20) + WK_TRANS
ok(near.hits.length == 1 && mid.hits.length == 1, `players at ~5 and ~8 blocks hit once each (${near.hits.length}, ${mid.hits.length})`)
ok(mid.hits[0].tick > near.hits[0].tick, `the farther player is hit later (+${mid.hits[0].tick - near.hits[0].tick} ticks)`)
ok(jumper.hits.length == 0, 'a player 2 blocks up (jumping) is not hit')
ok(far.hits.length == 0, 'a player 15 blocks away is outside the 12-block ring')
ok(cmds.some(c => /block_display/.test(c.c)) && !cmds.some(c => /setblock|fill /.test(c.c)), 'fragments are display entities; no world blocks change')
;[near, mid, jumper, far].forEach(e => e.removed = true)

console.log('3b. hand shockwave')
const victim = new Ent('player', boss.p.x, GROUND, boss.p.z + 6, { player: true, hp: 1000 }), side = new Ent('player', boss.p.x + 6, GROUND, boss.p.z, { player: true, hp: 1000 })
boss.target = victim; const ds = boss.persistentData; ['cd_special', 'cd_shock', 'wk_gap'].forEach(k => ds.putInt(k, 0)); ds.putInt('cd_stomp', 999); ds.putString('wk_last_special', 'STOMP')
let caught = null; const vv = victim.setDeltaMovement.bind(victim); victim.setDeltaMovement = v => { caught = v; vv(v) }
const r2 = Math.random; Math.random = () => 0.01
const ns = boss.triggers.length; guard = 0; while (!boss.triggers.slice(ns).some(t => t.n == 'hand_shockwave') && guard++ < 200) step(boss, 1)
Math.random = r2; step(boss, wkLen('SHOCKWAVE') + 2)
ok(victim.hits.length == 1 && caught && Math.abs(Math.hypot(caught.x, caught.z) - WKC.shockwave.pushBlocks / 8.1) < 1e-6, `player in the cone is hit and launched (h ${caught && Math.hypot(caught.x, caught.z).toFixed(2)} b/t, vy ${caught && caught.y})`)
ok(side.hits.length == 0, 'player 90 degrees to his side is outside the cone')
;[victim, side].forEach(e => e.removed = true)

console.log('4. dash travels the animated distance in a locked direction')
const runner = new Ent('player', boss.p.x, GROUND, boss.p.z + 11, { player: true, hp: 1000 }); boss.target = runner
const d0 = boss.persistentData; ['cd_dash', 'cd_sweep', 'cd_special', 'wk_gap'].forEach(k => d0.putInt(k, 0)); d0.putInt('cd_shock', 999); d0.putInt('cd_stomp', 999)
const r1 = Math.random; Math.random = () => 0.0
const nd = boss.triggers.length; guard = 0; while (!boss.triggers.slice(nd).some(t => t.n == 'dash') && guard++ < 200) step(boss, 1)
Math.random = r1
ok(boss.triggers.slice(nd).some(t => t.n == 'dash'), 'dash chosen against a player 11 blocks away')
const start = { ...boss.p }; step(boss, 21)
const aim = Math.atan2(runner.p.z - start.z, runner.p.x - start.x); runner.p = vec(runner.p.x + 8, GROUND, runner.p.z)          // the player sidesteps after the aim locks
step(boss, wkLen('DASH'))
const moved = Math.hypot(boss.p.x - start.x, boss.p.z - start.z)
ok(Math.abs(moved - 7.82) < 0.3, `moved ${moved.toFixed(2)} blocks (animation authored for 7.82)`)
const went = Math.atan2(boss.p.z - start.z, boss.p.x - start.x), err = Math.abs(((went - aim) * 180 / Math.PI + 540) % 360 - 180)
ok(err < 5, `direction stayed locked on the aim, not the sidestep (off by ${err.toFixed(1)} deg)`)

console.log('5. the death sequence')
runner.p = vec(0.5, GROUND, boss.p.z + 5); boss.target = runner
hurt(boss, 99999, runner)
ok(boss.hp == 1, `a lethal blow leaves him at 1 HP (${boss.hp})`)
step(boss, 1)
ok(state(boss) == 'DYING' && boss.pose == 'DIGGING', `dying (${state(boss)}, pose ${boss.pose})`)
ok(hurt(boss, 999, runner) == 0, 'no damage while dying')
step(boss, wkLen('DYING') - 2)
ok(!boss.killed, 'still alive just before the last frame')
step(boss, 3)
ok(boss.killed && boss.lastPlayer === runner, 'killed at the end, credited to the player who struck the blow (loot + xp)')
ok(cmds.filter(c => /experience_orb/.test(c.c)).length == 6, 'experience orbs dropped')
step(boss, WKC.death.dissolveTicks + 2)
ok(boss.removed, 'body dissolves and is removed')
console.log(`\n${pass} checks passed`)
