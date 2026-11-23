// The Withered King - a cursed king who drags his greatsword, kneels to call his dead army at half health, rises
// with a howl, and dies kneeling beside his planted sword with his crown on its hilt.
//
// Needs EntityJS + GeckoLib + KubeJS. Spawn with the spawn egg or: /summon kubejs:withered_king
// Assets:  kubejs/assets/kubejs/{geo,animations,textures}/entity/withered_king*
// Data:    withered_king_data.js (generated from the Blender bake: event times, blade/palm/foot paths, dash motion)
// Config:  kubejs/config/withered_king.json (written with the defaults below on first start; edit and restart)
// AI goals: server_scripts/bosses/withered_king_goals.js (EntityJS only takes goal events from server scripts)
//
// Everything that decides gameplay runs on the server (this file's tick). Clients only play the animations the
// server triggers, plus two looping states (kneeling, dying) that clients read from the entity's synced pose, so a
// player who arrives late still sees the right one.

const $WkAttributes = Java.loadClass('net.minecraft.world.entity.ai.attributes.Attributes')
const $WkAABB = Java.loadClass('net.minecraft.world.phys.AABB')
const $WkBossEvent = Java.loadClass('net.minecraft.server.level.ServerBossEvent')
const $WkBarColor = Java.loadClass('net.minecraft.world.BossEvent$BossBarColor')
const $WkBarOverlay = Java.loadClass('net.minecraft.world.BossEvent$BossBarOverlay')
const $WkVec3 = Java.loadClass('net.minecraft.world.phys.Vec3')
const $WkPose = Java.loadClass('net.minecraft.world.entity.Pose')
const $WkUUID = Java.loadClass('java.util.UUID')

const WK = 'withered_king'
const WK_TRANS = 4            // animation controller blend (ticks): what players see lags a trigger by this much
const WK_TRIGGERS = { sweep: 'PLAY_ONCE', dash: 'PLAY_ONCE', phase_transition: 'PLAY_ONCE', phase_two_roar: 'PLAY_ONCE',
  hand_shockwave: 'PLAY_ONCE', ground_stomp: 'PLAY_ONCE', death: 'HOLD_ON_LAST_FRAME' }
const WK_TEX = n => `kubejs:textures/entity/${n}.png`

// ------------------------------------------------------------------ configuration
const WK_DEFAULTS = {
  boss: { health: 900, armor: 14, armorToughness: 6, attackDamage: 14, followRange: 48, bossBarRange: 56, debug: false },
  combat: { approachDistance: 4.5, recoveryGapTicks: 12, specialGapTicks: 140 },
  sweep: { damage: 18, knockback: 1.1, maxRange: 6.2, cooldownTicks: 50, bladeRadius: 0.35 },
  dash: { damage: 20, minRange: 7, maxRange: 15, cooldownTicks: 260, chancePerTick: 0.06, launch: 1.4 },
  shockwave: { damage: 6, range: 9, coneDegrees: 40, pushBlocks: 6.5, cooldownTicks: 220, triggerRange: 7 },
  stomp: { damage: 16, radius: 12, ringBlocksPerTick: 0.6, jumpClearance: 1.1, verticalRange: 4, knockback: 0.7,
    cooldownTicks: 340, triggerRange: 6, fragments: true, fragmentSpacing: 2.0, maxFragmentsPerTick: 22 },
  phase: { threshold: 0.5, ringRadius: 6, leashDistance: 22, timeoutSeconds: 180,
    minions: [{ id: 'minecraft:wither_skeleton', count: 3 }, { id: 'minecraft:skeleton', count: 3 }] },
  roar: { darknessRadius: 32, darknessSeconds: 5 },
  death: { xp: 600, dissolveTicks: 50, monument: false, stopMusic: true },
  walk: { dragEffects: true }
}
function wkMerge(def, src) {
  if (src == null) return def
  let out = {}
  for (let k in def) {
    let d = def[k], v = null
    try { v = src[k] } catch (err) { v = null }
    if (v == null || v === undefined) { out[k] = d; continue }
    if (Array.isArray(d)) {
      let arr = []
      try {
        let n = v.length !== undefined ? v.length : v.size()
        for (let i = 0; i < n; i++) {
          let it = v[i] !== undefined ? v[i] : v.get(i)
          arr.push({ id: String(it.id !== undefined ? it.id : it.get('id')), count: Number(it.count !== undefined ? it.count : it.get('count')) })
        }
      } catch (err) { arr = d }
      out[k] = arr.length ? arr : d
    } else if (typeof d == 'object') out[k] = wkMerge(d, v)
    else if (typeof d == 'boolean') out[k] = String(v) == 'true'
    else if (typeof d == 'number') { let n = Number(v); out[k] = isFinite(n) ? n : d }
    else out[k] = String(v)
  }
  return out
}
const WK_CFG_PATH = 'kubejs/config/withered_king.json'
let wkFile = null
try { wkFile = JsonIO.read(WK_CFG_PATH) } catch (err) { wkFile = null }
if (wkFile == null) { try { JsonIO.write(WK_CFG_PATH, WK_DEFAULTS) } catch (err) { console.warn(`[Withered King] could not write ${WK_CFG_PATH}: ${err}`) } }
global.WK_CFG = wkMerge(WK_DEFAULTS, wkFile)
const WKC = global.WK_CFG

// ------------------------------------------------------------------ the entity
StartupEvents.registry('entity_type', event => {
  event.create(WK, 'entityjs:mob')
    .sized(3.0, 8.6)
    .modelSize(2.0, 2.0)
    .clientTrackingRange(16)
    .updateInterval(1)
    .fireImmune(true)
    .isPushable(false)
    .canBreatheUnderwater(true)
    .isPersistenceRequired(true)
    .removeWhenFarAway(ctx => false)
    .mobCategory('monster')
    .eggItem(egg => egg.backgroundColor(0x1b2a2c).highlightColor(0x5ff0e0))
    .modelResource(e => `kubejs:geo/entity/${WK}.geo.json`)
    .animationResource(e => `kubejs:animations/entity/${WK}.animation.json`)
    .textureResource(e => wkAwakened(e) ? WK_TEX(`${WK}_awakened`) : WK_TEX(WK))
    .newGlowingGeoLayer(layer => layer.textureResource(e => wkAwakened(e) ? WK_TEX(`${WK}_awakened_glowmask`) : WK_TEX(`${WK}_glowmask`)))
    .attributes(a => {
      a.add($WkAttributes.MAX_HEALTH, WKC.boss.health)
      a.add($WkAttributes.ARMOR, WKC.boss.armor)
      a.add($WkAttributes.ARMOR_TOUGHNESS, WKC.boss.armorToughness)
      a.add($WkAttributes.KNOCKBACK_RESISTANCE, 1.0)
      a.add($WkAttributes.MOVEMENT_SPEED, 0.20)      // the walk cycle is animated for exactly this speed
      a.add($WkAttributes.FOLLOW_RANGE, WKC.boss.followRange)
      a.add($WkAttributes.ATTACK_DAMAGE, WKC.boss.attackDamage)
    })
    // one controller: looping states come from the predicate, every action is a triggered animation on the same
    // controller so an action fully replaces the loop while it plays
    .addAnimationController('base', WK_TRANS, ev => {
      try {
        Object.keys(WK_TRIGGERS).forEach(n => ev.addTriggerableAnimation(`${WK}_${n}`, n, WK_TRIGGERS[n]))
        let e = ev.entity, pose = String(e.getPose())
        if (pose == 'DIGGING' || e.isDeadOrDying()) ev.thenPlayAndHold(`${WK}_death`)
        else if (pose == 'SITTING') ev.thenLoop(`${WK}_kneeling`)
        else if (ev.isMoving()) ev.thenLoop(`${WK}_walk_drag`)
        else ev.thenLoop(`${WK}_idle`)
      } catch (err) {}
      return true
    })
    .isInvulnerableTo(ctx => {
      try { return global.wkInvulnerable(ctx.entity, ctx.damageSource) } catch (err) { return false }
    })
    .tick(e => {
      if (e.level.isClientSide()) return
      try { global.wkTick(e) } catch (err) { wkLogOnce('tick', err) }
    })
    // no vanilla tip-over: after the death animation the body dissolves (or stays as a monument, if enabled)
    .tickDeath(e => {
      if (e.level.isClientSide()) return
      try { global.wkTickDeath(e) } catch (err) { wkLogOnce('tickDeath', err); e.discard() }
    })
    .onRemovedFromWorld(e => { if (!e.level.isClientSide()) try { global.wkClearBar(e) } catch (err) {} })
    .setHurtSound(ctx => 'minecraft:entity.wither_skeleton.hurt')
    .setDeathSound('minecraft:block.bell.resonate')
    .setSoundVolume(2.0)

  // the optional monument: his last pose, kneeling beside the planted sword with the crown on its hilt
  event.create(`${WK}_remains`, 'entityjs:mob')
    .sized(3.0, 6.0)
    .modelSize(2.0, 2.0)
    .clientTrackingRange(16)
    .isPushable(false)
    .fireImmune(true)
    .isPersistenceRequired(true)
    .removeWhenFarAway(ctx => false)
    .mobCategory('misc')
    .modelResource(e => `kubejs:geo/entity/${WK}.geo.json`)
    .animationResource(e => `kubejs:animations/entity/${WK}.animation.json`)
    .textureResource(e => WK_TEX(`${WK}_awakened`))
    .newGlowingGeoLayer(layer => layer.textureResource(e => WK_TEX(`${WK}_awakened_glowmask`)))
    .attributes(a => { a.add($WkAttributes.MAX_HEALTH, 1); a.add($WkAttributes.KNOCKBACK_RESISTANCE, 1.0) })
    .addAnimationController('base', 0, ev => { try { ev.thenPlayAndHold(`${WK}_remains`) } catch (err) {} return true })
    // only a creative-mode player can break it
    .isInvulnerableTo(ctx => {
      try { let a = ctx.damageSource.getEntity(); return !(a && a.isPlayer() && a.isCreative()) } catch (err) { return true }
    })
    .tick(e => { try { e.setYBodyRot(e.getYRot()); e.setYHeadRot(e.getYRot()) } catch (err) {} })
})

// ------------------------------------------------------------------ helpers
global.wkBars = global.wkBars || {}
global.wkLogged = global.wkLogged || {}
function wkLogOnce(where, err) {
  if (global.wkLogged[where]) return
  global.wkLogged[where] = true
  console.error(`[Withered King] ${where}: ${err}`)
}
function wkDebug(msg) { if (WKC.boss.debug) console.info(`[Withered King] ${msg}`) }
function wkD(e) { return e.persistentData }
function wkAwakened(e) { try { return e.getHealth() <= e.getMaxHealth() * WKC.phase.threshold + 0.01 } catch (err) { return false } }
function wkId(e) {
  let d = wkD(e)
  if (!d.contains('wk_id')) d.putString('wk_id', Math.floor(Math.random() * 0xfffffff).toString(16))
  return String(d.getString('wk_id'))
}
// Rhino in this pack can't read entity.x/.y/.z (the wrong getX overload wins), so positions go through position()
function wkNum(v) { try { if (typeof v == 'function') return NaN; let n = Number(v); return isFinite(n) ? n : NaN } catch (err) { return NaN } }
function wkVec(v) {
  let x = wkNum(v.x), y = wkNum(v.y), z = wkNum(v.z)
  if (isFinite(x) && isFinite(y) && isFinite(z)) return { x: x, y: y, z: z }
  try { x = wkNum(v.x()); y = wkNum(v.y()); z = wkNum(v.z()) } catch (err) {}
  if (isFinite(x) && isFinite(y) && isFinite(z)) return { x: x, y: y, z: z }
  return null
}
function wkP(o) {
  let r = null
  try { r = wkVec(o.position()) } catch (err) {}
  if (!r) try { let b = o.blockPosition(); r = { x: b.getX() + 0.5, y: b.getY(), z: b.getZ() + 0.5 } } catch (err) {}
  if (!r) { wkLogOnce('position', 'could not read a position'); r = { x: 0, y: 0, z: 0, bad: true } }
  return r
}
function wkDist(a, b) { let p = wkP(a), q = wkP(b); if (p.bad || q.bad) return 999; return Math.hypot(p.x - q.x, p.z - q.z) }
function wkYaw(e) { let y = wkNum(e.getYRot()); return isFinite(y) ? y : 0 }
function wkSetYaw(e, yaw) { if (!isFinite(yaw)) return; e.setYRot(yaw); e.setYHeadRot(yaw); e.setYBodyRot(yaw) }
function wkYawTo(e, t) { let p = wkP(e), q = wkP(t); return Math.atan2(q.z - p.z, q.x - p.x) * 180 / Math.PI - 90 }
function wkFwd(yaw) { let r = yaw * Math.PI / 180; return [-Math.sin(r), Math.cos(r)] }
// model pixels (x = his right, y = up, -z = in front of him; 8 px = 1 block) -> world, for a body at p facing yaw
function wkModel(p, yaw, m) {
  let r = yaw * Math.PI / 180, fx = -Math.sin(r), fz = Math.cos(r), rx = -Math.cos(r), rz = -Math.sin(r)
  let x = m[0] / 8, y = m[1] / 8, z = -m[2] / 8
  return { x: p.x + rx * x + fx * z, y: p.y + y, z: p.z + rz * x + fz * z }
}
function wkProbe(name, key, tick) {
  let a = global.WK_DATA[name][key]; let i = Math.max(0, Math.min(a.length - 1, tick)); return a[i]
}
function wkRun(e, c) { e.server.runCommandSilent(`execute in ${e.level.dimension} run ${c}`) }
function wkF(v) { return Number(v).toFixed(2) }
function wkSound(e, s, vol, pitch, at) { let p = at || wkP(e); wkRun(e, `playsound ${s} hostile @a ${wkF(p.x)} ${wkF(p.y)} ${wkF(p.z)} ${vol} ${pitch}`) }
function wkParticle(e, spec, at, dx, dy, dz, speed, count) {
  wkRun(e, `particle ${spec} ${wkF(at.x)} ${wkF(at.y)} ${wkF(at.z)} ${dx} ${dy} ${dz} ${speed} ${count} force`)
}
function wkNear(e, r, up) {
  let p = wkP(e)
  return e.level.getEntities(e, new $WkAABB(p.x - r, p.y - 4, p.z - r, p.x + r, p.y + (up || 10), p.z + r))
}
function wkTargetable(e, x) {
  if (!x || !x.isLiving() || !x.isAlive() || wkIsMinion(e, x)) return false
  if (x.isPlayer() && (x.isCreative() || x.isSpectator())) return false
  if (String(x.type).indexOf(WK) >= 0) return false
  return true
}
function wkIsMinion(e, x) { try { return x.getTags().contains('wkm_' + wkId(e)) } catch (err) { return false } }
// solid ground at block column (x, z) near height y: returns the y of the top face, or NaN
function wkSurface(level, x, z, y0, up, down) {
  let bx = Math.floor(x), bz = Math.floor(z), top = Math.floor(y0) + (up || 3)
  for (let y = top; y >= Math.floor(y0) - (down || 5); y--) {
    let b = level.getBlock(bx, y, bz), a = level.getBlock(bx, y + 1, bz)
    try {
      if (!b.blockState.isAir() && b.blockState.isSolidRender(level, b.pos) && !a.blockState.isSolidRender(level, a.pos)) return y + 1
    } catch (err) {}
  }
  return NaN
}
function wkBlockId(level, x, y, z) { try { return String(level.getBlock(Math.floor(x), Math.floor(y), Math.floor(z)).id) } catch (err) { return 'minecraft:air' } }
function wkIsStony(id) { return /stone|deepslate|cobble|brick|ore|andesite|diorite|granite|tuff|basalt|blackstone|obsidian|calcite|iron|copper/.test(id) }
function wkKnock(x, vx, vy, vz) { x.setDeltaMovement(new $WkVec3(vx, vy, vz)); x.hurtMarked = true }
function wkHurt(e, x, dmg) { try { x.attack(e.damageSources().mobAttack(e), dmg) } catch (err) { wkLogOnce('hurt', err) } }

function wkTrigger(e, n) {
  try { e.triggerAnimation('base', n) } catch (err) {
    try { e.triggerAnim('base', n) } catch (err2) { wkLogOnce('trigger', err2) }
  }
}
function wkStopTriggered(e) { Object.keys(WK_TRIGGERS).forEach(n => { try { e.stopTriggeredAnimation('base', n) } catch (err) {} }) }
function wkSetPose(e, name) { try { e.setPose($WkPose.valueOf(name)) } catch (err) { wkLogOnce('pose', err) } }

// action name -> animation, length (ticks incl. the blend)
const WK_ACT = { SWEEP: 'sweep', DASH: 'dash', TRANSITION: 'phase_transition', ROAR: 'phase_two_roar',
  SHOCKWAVE: 'hand_shockwave', STOMP: 'ground_stomp', DYING: 'death' }
function wkLen(act) { return Math.round(global.WK_DATA[WK_ACT[act]].len * 20) + WK_TRANS }
function wkStart(e, act) {
  let d = wkD(e)
  d.putString('wk_act', act); d.putInt('wk_t', 0); d.putFloat('wk_yaw', wkYaw(e))
  d.putString('wk_hit', '')
  e.getNavigation().stop()
  wkTrigger(e, WK_ACT[act])
  wkDebug(`${act} (${global.wkState(e)})`)
}
function wkEnd(e) {
  let d = wkD(e); let act = String(d.getString('wk_act'))
  d.putString('wk_act', ''); d.putInt('wk_t', 0); d.putInt('wk_gap', WKC.combat.recoveryGapTicks)
  if (act == 'SHOCKWAVE' || act == 'STOMP') { d.putString('wk_last_special', act); d.putInt('cd_special', WKC.combat.specialGapTicks) }
}
// a hit list for the current action, so each target is hit at most once
function wkWasHit(e, x) { return String(wkD(e).getString('wk_hit')).indexOf(String(x.getStringUuid())) >= 0 }
function wkMarkHit(e, x) { let d = wkD(e); d.putString('wk_hit', String(d.getString('wk_hit')) + ',' + String(x.getStringUuid())) }

// the state names from the design document, for debugging and for other scripts
global.wkState = e => {
  let d = wkD(e), act = String(d.getString('wk_act')), s = (d.getInt('wk_t') - WK_TRANS) / 20
  if (d.getBoolean('wk_dead')) return 'DEAD'
  if (act == 'SWEEP') return s < 0.8 ? 'SWEEP_WINDUP' : s < 1.25 ? 'SWEEP_ATTACK' : 'SWEEP_RECOVERY'
  if (act == 'DASH') return s < 0.9 ? 'DASH_WINDUP' : s < 1.5 ? 'DASH_ATTACK' : 'DASH_RECOVERY'
  if (act == 'TRANSITION') return 'PHASE_TRANSITION'
  if (act == 'KNEEL') return 'KNEELING_INVULNERABLE'
  if (act == 'ROAR') return s < 2.9 ? 'PHASE_TWO_RISE' : 'PHASE_TWO_ROAR'
  if (act == 'SHOCKWAVE') return s < 0.65 ? 'SHOCKWAVE_WINDUP' : s < 0.95 ? 'SHOCKWAVE_RELEASE' : 'SHOCKWAVE_RECOVERY'
  if (act == 'STOMP') return s < 1.15 ? 'STOMP_WINDUP' : s < 1.42 ? 'STOMP_IMPACT' : 'STOMP_RECOVERY'
  if (act == 'DYING') return 'DYING'
  if (d.getInt('wk_phase') >= 2) return 'PHASE_TWO_COMBAT'
  return e.getNavigation().isInProgress() ? 'WALKING' : 'IDLE'
}
const WK_PROTECTED = ['TRANSITION', 'KNEEL', 'ROAR', 'DYING']
function wkProtected(e) { let d = wkD(e); return d.getBoolean('wk_dead') || WK_PROTECTED.indexOf(String(d.getString('wk_act'))) >= 0 || d.getBoolean('wk_go_transition') || d.getBoolean('wk_go_death') }
function wkAlwaysAllowed(src) {
  try { let id = String(src.getMsgId()); return id == 'genericKill' || id == 'outOfWorld' } catch (err) { return false }
}
global.wkInvulnerable = (e, src) => {
  if (wkD(e).getBoolean('wk_finish')) return false
  if (src && wkAlwaysAllowed(src)) return false
  return wkProtected(e)
}

// ------------------------------------------------------------------ damage gates (50% transition, controlled death)
// Damage is cut so health stops exactly at the phase gate (the transition starts on his next tick) and so a lethal
// blow leaves him at 1 HP and starts the death sequence instead of the vanilla death.
ForgeEvents.onEvent('net.minecraftforge.event.entity.living.LivingAttackEvent', ev => {
  try {
    let e = ev.getEntity()
    if (String(e.type) != `kubejs:${WK}` || e.level.isClientSide()) return
    if (wkD(e).getBoolean('wk_finish') || wkAlwaysAllowed(ev.getSource())) return
    if (!wkProtected(e)) return
    ev.setCanceled(true)
    let d = wkD(e)
    if (e.tickCount - d.getInt('wk_clank') > 10 && !d.getBoolean('wk_dead') && String(d.getString('wk_act')) != 'DYING') {
      d.putInt('wk_clank', e.tickCount)
      wkSound(e, 'minecraft:block.respawn_anchor.deplete', 0.8, 1.6)
      let p = wkP(e); wkParticle(e, 'minecraft:enchanted_hit', { x: p.x, y: p.y + 3, z: p.z }, 1.2, 1.5, 1.2, 0.1, 12)
    }
  } catch (err) { wkLogOnce('attack event', err) }
})
ForgeEvents.onEvent('net.minecraftforge.event.entity.living.LivingDamageEvent', ev => {
  try {
    let e = ev.getEntity()
    if (String(e.type) != `kubejs:${WK}` || e.level.isClientSide()) return
    let d = wkD(e)
    if (d.getBoolean('wk_finish') || wkAlwaysAllowed(ev.getSource())) return
    if (wkProtected(e)) { ev.setCanceled(true); return }
    let hp = e.getHealth(), max = e.getMaxHealth(), amt = ev.getAmount()
    let gate = max * WKC.phase.threshold + 0.5
    if (d.getInt('wk_phase') < 2 && !d.getBoolean('wk_transition_done') && hp - amt <= gate) {
      ev.setAmount(Math.max(0, hp - gate))
      d.putBoolean('wk_go_transition', true)
      return
    }
    if (hp - amt < 1) {
      ev.setAmount(Math.max(0, hp - 1))
      d.putBoolean('wk_go_death', true)
      let killer = null
      try { let s = ev.getSource().getEntity(); if (s && s.isPlayer()) killer = s } catch (err) {}
      if (killer) d.putString('wk_killer', String(killer.getStringUuid()))
    }
  } catch (err) { wkLogOnce('damage event', err) }
})

// ------------------------------------------------------------------ boss bar
function wkBar(e) {
  let id = wkId(e), bar = global.wkBars[id]
  if (!bar) {
    bar = new $WkBossEvent(Text.of('The Withered King').darkAqua(), $WkBarColor.BLUE, $WkBarOverlay.NOTCHED_10)
    global.wkBars[id] = bar
  }
  bar.setProgress(Math.max(0, Math.min(1, e.getHealth() / e.getMaxHealth())))
  bar.setColor(wkD(e).getInt('wk_phase') >= 2 ? $WkBarColor.PURPLE : $WkBarColor.BLUE)
  e.server.players.forEach(p => {
    if (p.level == e.level && wkDist(p, e) < WKC.boss.bossBarRange) bar.addPlayer(p); else bar.removePlayer(p)
  })
}
global.wkClearBar = e => { let id = wkId(e); if (global.wkBars[id]) { global.wkBars[id].removeAllPlayers(); delete global.wkBars[id] } }

// ------------------------------------------------------------------ the fight
global.wkTick = e => {
  let d = wkD(e)
  if (!d.contains('wk_phase')) { d.putInt('wk_phase', 1); d.putInt('cd_sweep', 20); d.putInt('cd_dash', 120); d.putInt('cd_shock', 60); d.putInt('cd_stomp', 100) }
  if (e.tickCount % 5 == 0) wkBar(e)
  ;['cd_sweep', 'cd_dash', 'cd_shock', 'cd_stomp', 'cd_special', 'wk_gap'].forEach(k => { if (d.getInt(k) > 0) d.putInt(k, d.getInt(k) - 1) })

  // death outranks everything, the transition outranks combat
  if (d.getBoolean('wk_go_death') && String(d.getString('wk_act')) != 'DYING') {
    d.putBoolean('wk_go_death', false); wkStopTriggered(e); wkSetPose(e, 'DIGGING'); wkStart(e, 'DYING'); return wkDying(e, 0)
  }
  if (d.getBoolean('wk_go_transition') && WK_PROTECTED.indexOf(String(d.getString('wk_act'))) < 0) {
    d.putBoolean('wk_go_transition', false); d.putBoolean('wk_transition_done', true)
    wkStopTriggered(e); wkStart(e, 'TRANSITION'); return wkTransition(e, 0)
  }

  let target = e.getTarget()
  e.setAggressive(!!target)
  let act = String(d.getString('wk_act'))
  if (act != '') {
    let t = d.getInt('wk_t'); d.putInt('wk_t', t + 1)
    e.getNavigation().stop()
    if (act == 'SWEEP') wkSweep(e, t, target)
    else if (act == 'DASH') wkDash(e, t, target)
    else if (act == 'TRANSITION') wkTransition(e, t)
    else if (act == 'KNEEL') wkKneel(e, t)
    else if (act == 'ROAR') wkRoar(e, t)
    else if (act == 'SHOCKWAVE') wkShockwave(e, t, target)
    else if (act == 'STOMP') wkStomp(e, t, target)
    else if (act == 'DYING') wkDying(e, t)
    return
  }
  wkWalkEffects(e)
  if (!target || !target.isAlive()) { e.getNavigation().stop(); return }
  let dist = wkDist(e, target), p2 = d.getInt('wk_phase') >= 2, r = Math.random()
  if (d.getInt('wk_gap') == 0) {
    if (p2 && d.getInt('cd_special') == 0) {
      let close = 0; wkNear(e, WKC.stomp.triggerRange).forEach(x => { if (x.isPlayer() && wkTargetable(e, x)) close++ })
      let last = String(d.getString('wk_last_special'))
      if (close > 0 && d.getInt('cd_stomp') == 0 && last != 'STOMP' && r < 0.35) { d.putInt('cd_stomp', WKC.stomp.cooldownTicks); wkStart(e, 'STOMP'); return }
      if (dist <= WKC.shockwave.triggerRange && d.getInt('cd_shock') == 0 && last != 'SHOCKWAVE' && r < 0.3) { d.putInt('cd_shock', WKC.shockwave.cooldownTicks); wkStart(e, 'SHOCKWAVE'); return }
    }
    if (dist <= WKC.sweep.maxRange - 0.4 && d.getInt('cd_sweep') == 0) { d.putInt('cd_sweep', WKC.sweep.cooldownTicks); wkStart(e, 'SWEEP'); return }
    if (dist >= WKC.dash.minRange && dist <= WKC.dash.maxRange && d.getInt('cd_dash') == 0 && r < WKC.dash.chancePerTick && e.hasLineOfSight(target)) {
      d.putInt('cd_dash', WKC.dash.cooldownTicks); wkStart(e, 'DASH'); return
    }
  }
  if (dist > WKC.combat.approachDistance) {
    try { if (!e.getNavigation().moveTo(target, 1.0)) { let q = wkP(target); e.getNavigation().moveTo(q.x, q.y, q.z, 1.0) } } catch (err) { wkLogOnce('moveTo', err) }
  } else { e.getNavigation().stop(); wkSetYaw(e, wkYawTo(e, target)) }
}

// --- walking: the sword point gouges the ground behind him (visual only), heavy footsteps
function wkWalkEffects(e) {
  let d = wkD(e), moving = e.getNavigation().isInProgress()
  if (!moving) { d.putInt('wk_walk', 0); return }
  let w = d.getInt('wk_walk'); d.putInt('wk_walk', w + 1)
  if (!WKC.walk.dragEffects) return
  let k = (w - WK_TRANS + 480) % 48, p = wkP(e), yaw = wkYaw(e)
  if (w % 2 == 0) {
    let tip = wkModel(p, yaw, wkProbe('walk_drag', 'tip', k)), id = wkBlockId(e.level, tip.x, tip.y - 0.3, tip.z)
    if (id != 'minecraft:air') {
      wkParticle(e, `minecraft:block ${id}`, { x: tip.x, y: tip.y + 0.1, z: tip.z }, 0.15, 0.05, 0.15, 0.05, 3)
      if (wkIsStony(id) && w % 6 == 0) wkParticle(e, 'minecraft:electric_spark', { x: tip.x, y: tip.y + 0.15, z: tip.z }, 0.1, 0.05, 0.1, 0.08, 2)
    }
  }
  if (w % 16 == 4) wkSound(e, 'minecraft:block.grindstone.use', 0.45, 0.5, wkModel(p, yaw, wkProbe('walk_drag', 'tip', k)))
  if (k == 0 || k == 24) {
    let f = wkModel(p, yaw, wkProbe('walk_drag', k == 0 ? 'footR' : 'footL', k)), id = wkBlockId(e.level, f.x, p.y - 0.5, f.z)
    wkSound(e, 'minecraft:entity.iron_golem.step', 1.6, 0.55, f)
    if (id != 'minecraft:air') wkParticle(e, `minecraft:block ${id}`, { x: f.x, y: p.y + 0.1, z: f.z }, 0.5, 0.05, 0.5, 0.1, 10)
  }
}

// helper for timed events: true on the tick that shows animation time s
function wkAt(t, s) { return t == Math.round(s * 20) + WK_TRANS }
function wkAnimTick(t) { return Math.max(0, t - WK_TRANS) }

// --- 03 sweep: the blade's real path (from the bake) is swept through the world each tick of the swing
function wkSweep(e, t, target) {
  let d = wkD(e)
  if (t < Math.round(0.6 * 20) + WK_TRANS && target) { wkSetYaw(e, wkYawTo(e, target)); d.putFloat('wk_yaw', wkYaw(e)) }
  else wkSetYaw(e, d.getFloat('wk_yaw'))
  let p = wkP(e), yaw = d.getFloat('wk_yaw'), k = wkAnimTick(t)
  if (wkAt(t, 0.15)) wkSound(e, 'minecraft:item.armor.equip_netherite', 1.5, 0.5)
  if (t >= WK_TRANS + 6 && t <= WK_TRANS + 16 && t % 2 == 0) {                 // the point scraped back into the windup
    let tip = wkModel(p, yaw, wkProbe('sweep', 'tip', k)), id = wkBlockId(e.level, tip.x, tip.y - 0.3, tip.z)
    if (id != 'minecraft:air') wkParticle(e, `minecraft:block ${id}`, { x: tip.x, y: tip.y + 0.1, z: tip.z }, 0.2, 0.05, 0.2, 0.05, 4)
    if (t % 6 == 0) wkSound(e, 'minecraft:block.grindstone.use', 0.6, 0.6, tip)
  }
  if (wkAt(t, 0.9)) wkSound(e, 'minecraft:entity.player.attack.sweep', 2.0, 0.45)
  if (wkAt(t, 0.95)) wkSound(e, 'minecraft:entity.ravager.attack', 1.5, 0.5)
  // active frames: 0.85 s - 1.3 s of the animation
  if (k >= 17 && k <= 26) {
    let A = [], steps = 4
    for (let s = 0; s <= steps; s++) {
      let u = s / steps, ga = wkProbe('sweep', 'grip', k - 1), gb = wkProbe('sweep', 'grip', k), ta = wkProbe('sweep', 'tip', k - 1), tb = wkProbe('sweep', 'tip', k)
      let g = [ga[0] + (gb[0] - ga[0]) * u, ga[1] + (gb[1] - ga[1]) * u, ga[2] + (gb[2] - ga[2]) * u]
      let tp = [ta[0] + (tb[0] - ta[0]) * u, ta[1] + (tb[1] - ta[1]) * u, ta[2] + (tb[2] - ta[2]) * u]
      for (let j = 0; j <= 8; j++) { let v = j / 8; A.push(wkModel(p, yaw, [g[0] + (tp[0] - g[0]) * v, g[1] + (tp[1] - g[1]) * v, g[2] + (tp[2] - g[2]) * v])) }
    }
    let tip = wkModel(p, yaw, wkProbe('sweep', 'tip', k)), id = wkBlockId(e.level, tip.x, tip.y - 0.3, tip.z)
    if (id != 'minecraft:air') {
      wkParticle(e, `minecraft:block ${id}`, { x: tip.x, y: tip.y + 0.15, z: tip.z }, 0.4, 0.1, 0.4, 0.15, 8)
      if (wkIsStony(id)) wkParticle(e, 'minecraft:electric_spark', { x: tip.x, y: tip.y + 0.2, z: tip.z }, 0.3, 0.1, 0.3, 0.2, 5)
    }
    let br = WKC.sweep.bladeRadius
    wkNear(e, WKC.sweep.maxRange + 3).forEach(x => {
      if (!wkTargetable(e, x) || wkWasHit(e, x)) return
      let bb = x.getBoundingBox(), hit = false
      for (let i = 0; i < A.length && !hit; i++) {
        let q = A[i]
        if (q.x > bb.minX - br && q.x < bb.maxX + br && q.y > bb.minY - br && q.y < bb.maxY + br && q.z > bb.minZ - br && q.z < bb.maxZ + br) hit = true
      }
      if (!hit) return
      wkMarkHit(e, x); wkHurt(e, x, WKC.sweep.damage)
      // thrown along the blade's travel (sideways across his front) and a little away from him
      let q = wkP(x), dx = q.x - p.x, dz = q.z - p.z, n = Math.max(0.01, Math.hypot(dx, dz))
      let tb = wkModel(p, yaw, wkProbe('sweep', 'tip', k)), ta = wkModel(p, yaw, wkProbe('sweep', 'tip', k - 1))
      let sx = tb.x - ta.x, sz = tb.z - ta.z, sn = Math.max(0.01, Math.hypot(sx, sz))
      let kb = WKC.sweep.knockback
      wkKnock(x, (sx / sn * 0.6 + dx / n * 0.4) * kb, 0.35, (sz / sn * 0.6 + dz / n * 0.4) * kb)
      wkSound(e, 'minecraft:entity.player.attack.crit', 1.5, 0.6, q)
    })
  }
  if (t >= wkLen('SWEEP')) wkEnd(e)
}

// --- 04 dash: aimed in the windup, locked at 0.75 s; the body really travels the distance the feet were animated for
function wkDash(e, t, target) {
  let d = wkD(e), k = wkAnimTick(t)
  if (k < 15 && target) { wkSetYaw(e, wkYawTo(e, target)); d.putFloat('wk_yaw', wkYaw(e)) }
  else wkSetYaw(e, d.getFloat('wk_yaw'))
  let yaw = d.getFloat('wk_yaw'), f = wkFwd(yaw), p = wkP(e)
  if (wkAt(t, 0.1)) { wkSound(e, 'minecraft:entity.ravager.roar', 1.6, 0.6); wkSound(e, 'minecraft:item.armor.equip_netherite', 1.5, 0.5) }
  if (wkAt(t, 0.38)) wkSound(e, 'minecraft:entity.iron_golem.step', 2, 0.5)
  if (wkAt(t, 0.9)) { wkSound(e, 'minecraft:entity.ravager.step', 2, 0.6); wkParticle(e, 'minecraft:cloud', { x: p.x - f[0], y: p.y + 0.2, z: p.z - f[1] }, 0.6, 0.1, 0.6, 0.02, 12) }
  let move = global.WK_DATA.dash.move, step = k < move.length ? move[k] : 0
  if (step > 0 && !d.getBoolean('wk_dash_blocked')) {
    // stop at walls and at drops instead of sailing off a cliff
    let ahead = { x: p.x + f[0] * 2.0, z: p.z + f[1] * 2.0 }
    if (e.horizontalCollision || isNaN(wkSurface(e.level, ahead.x, ahead.z, p.y, 1, 3))) {
      d.putBoolean('wk_dash_blocked', true)
      wkSound(e, 'minecraft:entity.iron_golem.damage', 2, 0.5); wkParticle(e, 'minecraft:explosion', { x: p.x + f[0] * 1.8, y: p.y + 2, z: p.z + f[1] * 1.8 }, 0.5, 0.5, 0.5, 0, 2)
    } else {
      let vy = 0; try { let v = wkVec(e.getDeltaMovement()); if (v) vy = v.y } catch (err) {}
      e.setDeltaMovement(new $WkVec3(f[0] * step, vy, f[1] * step)); e.hurtMarked = true
      if (k % 2 == 0) wkParticle(e, 'minecraft:campfire_cosy_smoke', { x: p.x - f[0], y: p.y + 0.2, z: p.z - f[1] }, 0.6, 0.05, 0.6, 0.01, 3)
      // anyone in his path is struck and thrown ahead of him (so he never runs through them)
      wkNear(e, 5).forEach(x => {
        if (!wkTargetable(e, x) || wkWasHit(e, x)) return
        let q = wkP(x), dx = q.x - p.x, dz = q.z - p.z, along = dx * f[0] + dz * f[1], side = Math.abs(dx * f[1] - dz * f[0]), w = x.getBbWidth() / 2
        if (along < -0.5 || along > 2.6 + w || side > 1.6 + w || q.y > p.y + 5 || q.y + x.getBbHeight() < p.y - 0.5) return
        wkMarkHit(e, x); wkHurt(e, x, WKC.dash.damage)
        let L = Math.max(WKC.dash.launch, step * 1.3)
        wkKnock(x, f[0] * L, 0.45, f[1] * L)
        wkSound(e, 'minecraft:block.anvil.land', 1.2, 0.5, q); wkSound(e, 'minecraft:entity.player.attack.knockback', 1.5, 0.6, q)
        wkParticle(e, 'minecraft:crit', { x: q.x, y: q.y + 1, z: q.z }, 0.4, 0.5, 0.4, 0.3, 20)
      })
    }
  }
  ;(global.WK_DATA.dash.ev || []).forEach(ev => {
    if (ev[1] == 'footstep' && wkAt(t, ev[0])) { wkSound(e, 'minecraft:entity.iron_golem.step', 1.8, 0.6); wkParticle(e, 'minecraft:cloud', { x: p.x, y: p.y + 0.1, z: p.z }, 0.6, 0.05, 0.6, 0.02, 4) }
  })
  if (wkAt(t, 1.5)) { wkSound(e, 'minecraft:block.gravel.break', 2, 0.5); wkParticle(e, 'minecraft:campfire_cosy_smoke', { x: p.x + f[0] * 1.2, y: p.y + 0.2, z: p.z + f[1] * 1.2 }, 0.8, 0.1, 0.8, 0.01, 10) }
  if (t >= wkLen('DASH')) { d.putBoolean('wk_dash_blocked', false); wkEnd(e) }
}

// --- 05 phase transition -> 06 kneeling (protected) while his summoned dead live
function wkTransition(e, t) {
  let d = wkD(e); wkSetYaw(e, d.getFloat('wk_yaw'))
  let p = wkP(e), yaw = d.getFloat('wk_yaw'), k = wkAnimTick(t)
  if (t == 0) { wkSound(e, 'minecraft:entity.wither_skeleton.hurt', 2, 0.4); wkSound(e, 'minecraft:entity.iron_golem.damage', 1.5, 0.5) }
  if (wkAt(t, 2.35)) {
    let tip = wkModel(p, yaw, wkProbe('phase_transition', 'tip', k)), id = wkBlockId(e.level, tip.x, tip.y - 0.3, tip.z)
    wkSound(e, 'minecraft:block.anvil.land', 1.5, 0.45, tip); wkSound(e, 'minecraft:entity.generic.explode', 1.0, 0.5, tip)
    if (id != 'minecraft:air') wkParticle(e, `minecraft:block ${id}`, { x: tip.x, y: tip.y + 0.2, z: tip.z }, 0.5, 0.2, 0.5, 0.2, 30)
  }
  if (wkAt(t, 3.6)) wkSound(e, 'minecraft:entity.iron_golem.step', 2, 0.4)
  if (t >= wkLen('TRANSITION')) {
    wkSetPose(e, 'SITTING')
    d.putString('wk_act', 'KNEEL'); d.putInt('wk_t', 0); d.putInt('wk_kneel_s', 0)
    wkDebug('KNEEL')
  }
}
function wkMinionSpots(e, n) {
  let p = wkP(e), spots = [], players = []
  e.level.players.forEach(x => { if (x.isAlive()) players.push(x) })
  for (let i = 0; i < n * 6 && spots.length < n; i++) {
    let a = (i / n) * Math.PI * 2 + Math.floor(i / n) * 0.37, rr = WKC.phase.ringRadius + [0, -1.5, 1.5, -2.5, 2.5, 0.8][Math.floor(i / n) % 6]
    let x = p.x + Math.cos(a) * rr, z = p.z + Math.sin(a) * rr, y = wkSurface(e.level, x, z, p.y, 3, 4)
    if (isNaN(y)) continue
    let clear = true
    for (let h = 0; h < 3; h++) { let b = e.level.getBlock(Math.floor(x), y + h, Math.floor(z)); try { if (b.blockState.isSolidRender(e.level, b.pos) || !b.blockState.getFluidState().isEmpty()) clear = false } catch (err) { clear = false } }
    if (!clear) continue
    if (players.some(pl => { let q = wkP(pl); return Math.hypot(q.x - x, q.z - z) < 1.8 && Math.abs(q.y - y) < 3 })) continue
    if (spots.some(s => Math.hypot(s.x - x, s.z - z) < 1.6)) continue
    spots.push({ x: Math.floor(x) + 0.5, y: y, z: Math.floor(z) + 0.5 })
  }
  return spots
}
function wkSummon(e) {
  let list = [], tag = 'wkm_' + wkId(e)
  WKC.phase.minions.forEach(m => { for (let i = 0; i < m.count; i++) list.push(m.id) })
  let spots = wkMinionSpots(e, list.length), p = wkP(e)
  if (spots.length < list.length) wkDebug(`only ${spots.length} safe spots for ${list.length} minions`)
  list.forEach((id, i) => {
    let s = spots.length ? spots[i % spots.length] : { x: p.x + 2, y: p.y, z: p.z }
    wkRun(e, `summon ${id} ${wkF(s.x)} ${s.y} ${wkF(s.z)} {Tags:["${tag}","wk_minion","wk_new"],PersistenceRequired:1b}`)
    wkParticle(e, 'minecraft:soul', { x: s.x, y: s.y + 0.5, z: s.z }, 0.4, 0.8, 0.4, 0.03, 30)
    wkParticle(e, 'minecraft:sculk_soul', { x: s.x, y: s.y + 0.2, z: s.z }, 0.3, 0.2, 0.3, 0.05, 10)
  })
  wkSound(e, 'minecraft:entity.evoker.prepare_summon', 2, 0.5); wkSound(e, 'minecraft:entity.wither.ambient', 1.2, 0.5)
}
function wkTrackNew(e) {
  let d = wkD(e), ids = String(d.getString('wk_minions')), tag = 'wkm_' + wkId(e)
  wkNear(e, WKC.phase.ringRadius + 8).forEach(x => {
    try {
      if (!x.getTags().contains('wk_new') || !x.getTags().contains(tag)) return
      x.removeTag('wk_new'); ids += (ids ? ',' : '') + String(x.getStringUuid())
      let pl = e.level.getNearestPlayer(x, 32); if (pl && !pl.isCreative() && !pl.isSpectator()) x.setTarget(pl)
    } catch (err) { wkLogOnce('track', err) }
  })
  d.putString('wk_minions', ids)
}
function wkMinions(e) {
  let ids = String(wkD(e).getString('wk_minions')), out = []
  if (!ids) return out
  ids.split(',').forEach(s => { try { let m = e.level.getEntity($WkUUID.fromString(s)); if (m && m.isAlive()) out.push(m) } catch (err) {} })
  return out
}
function wkKneel(e, t) {
  let d = wkD(e); wkSetYaw(e, d.getFloat('wk_yaw')); wkSetPose(e, 'SITTING')
  let p = wkP(e)
  // the aura: a slow dark ring at his feet and motes rising off him; it marks that he can't be hurt
  if (t % 6 == 0) {
    for (let i = 0; i < 10; i++) { let a = (i / 10) * Math.PI * 2 + t * 0.05; wkParticle(e, 'minecraft:reverse_portal', { x: p.x + Math.cos(a) * 2.4, y: p.y + 0.2, z: p.z + Math.sin(a) * 2.4 }, 0, 0.3, 0, 0.02, 1) }
    wkParticle(e, 'minecraft:soul', { x: p.x, y: p.y + 2.5, z: p.z }, 1.2, 1.5, 1.2, 0.01, t < 24 ? 1 + Math.floor(t / 6) : 4)
  }
  if (t < 24 && t % 8 == 0) wkSound(e, 'minecraft:entity.warden.heartbeat', 0.6 + t / 24, 0.5)
  if (t == 24) wkSummon(e)
  if (t == 25 || t == 27) wkTrackNew(e)
  if (t > 30 && t % 10 == 0) {
    let alive = wkMinions(e)
    if (t % 40 == 0) wkSound(e, 'minecraft:ambient.soul_sand_valley.mood', 0.8, 0.6)
    // anything that wanders off or gets stuck is called back to the ring, so the fight can't soft-lock
    alive.forEach(m => {
      let q = wkP(m), far = Math.hypot(q.x - p.x, q.z - p.z) > WKC.phase.leashDistance || Math.abs(q.y - p.y) > 8
      let stuck = false; try { stuck = m.isInWall() || m.isInLava() } catch (err) {}
      if (far || stuck) {
        let s = wkMinionSpots(e, 1)[0]
        if (s) { m.teleportTo(s.x, s.y, s.z); wkParticle(e, 'minecraft:soul', { x: s.x, y: s.y + 1, z: s.z }, 0.3, 0.8, 0.3, 0.02, 15) }
      }
    })
    let seconds = t / 20
    if (alive.length > 0 && seconds > WKC.phase.timeoutSeconds) {
      alive.forEach(m => { let q = wkP(m); wkParticle(e, 'minecraft:soul', { x: q.x, y: q.y + 1, z: q.z }, 0.3, 0.8, 0.3, 0.02, 20); m.discard() })
      wkDebug('minions timed out'); alive = []
    }
    if (alive.length == 0 && t > 40) {
      d.putString('wk_minions', '')
      wkSetPose(e, 'STANDING'); wkStart(e, 'ROAR')
    }
  }
}

// --- 07 rising and howl: still protected until it ends
function wkRoar(e, t) {
  let d = wkD(e); wkSetYaw(e, d.getFloat('wk_yaw'))
  let p = wkP(e), yaw = d.getFloat('wk_yaw'), k = wkAnimTick(t)
  if (wkAt(t, 0.1)) { wkSound(e, 'minecraft:entity.warden.emerge', 1.5, 0.6); wkParticle(e, 'minecraft:campfire_cosy_smoke', { x: p.x, y: p.y + 0.2, z: p.z }, 1.5, 0.1, 1.5, 0.01, 12) }
  if (wkAt(t, 2.6)) {
    let tip = wkModel(p, yaw, wkProbe('phase_two_roar', 'tip', Math.round(2.45 * 20))), id = wkBlockId(e.level, tip.x, tip.y - 0.3, tip.z)
    wkSound(e, 'minecraft:block.stone.break', 2, 0.5, tip); wkSound(e, 'minecraft:item.trident.return', 1.2, 0.5, tip)
    if (id != 'minecraft:air') wkParticle(e, `minecraft:block ${id}`, { x: tip.x, y: tip.y + 0.3, z: tip.z }, 0.4, 0.3, 0.4, 0.2, 30)
  }
  if (wkAt(t, 3.05)) {
    wkSound(e, 'minecraft:entity.warden.roar', 3, 0.5); wkSound(e, 'minecraft:entity.lightning_bolt.thunder', 1.4, 0.6)
    wkSound(e, 'minecraft:block.anvil.land', 0.7, 0.5); wkSound(e, 'minecraft:block.respawn_anchor.deplete', 1.5, 0.5)
    for (let i = 0; i < 24; i++) { let a = (i / 24) * Math.PI * 2; wkParticle(e, 'minecraft:sculk_soul', { x: p.x + Math.cos(a) * 1.5, y: p.y + 4, z: p.z + Math.sin(a) * 1.5 }, 0.2, 0.6, 0.2, 0.25, 2) }
    wkParticle(e, 'minecraft:large_smoke', { x: p.x, y: p.y + 4, z: p.z }, 2, 2, 2, 0.08, 60)
    wkParticle(e, 'minecraft:campfire_cosy_smoke', { x: p.x, y: p.y + 0.3, z: p.z }, 3, 0.1, 3, 0.02, 30)
    wkRun(e, `effect give @a[x=${wkF(p.x)},y=${wkF(p.y)},z=${wkF(p.z)},distance=..${WKC.roar.darknessRadius}] minecraft:darkness ${WKC.roar.darknessSeconds} 0 true`)
    wkNear(e, 5).forEach(x => {                 // the burst shoves people back, without damage
      if (!wkTargetable(e, x)) return
      let q = wkP(x), dx = q.x - p.x, dz = q.z - p.z, n = Math.max(0.01, Math.hypot(dx, dz)); wkKnock(x, dx / n * 0.9, 0.35, dz / n * 0.9)
    })
    // his armour ignites: the awakened texture shows from here on (it keys off health being at the gate)
    e.setHealth(Math.min(e.getHealth(), e.getMaxHealth() * WKC.phase.threshold))
  }
  if (t >= wkLen('ROAR')) {
    d.putInt('wk_phase', 2); d.putInt('cd_special', 40); d.putInt('cd_sweep', 10)
    wkEnd(e); wkDebug('PHASE_TWO_COMBAT')
  }
}

// --- 08 hand shockwave: a cone from his palm; players are thrown ~6-7 blocks by real velocity
function wkShockwave(e, t, target) {
  let d = wkD(e), k = wkAnimTick(t)
  if (k < 11 && target) { wkSetYaw(e, wkYawTo(e, target)); d.putFloat('wk_yaw', wkYaw(e)) }
  else wkSetYaw(e, d.getFloat('wk_yaw'))
  let p = wkP(e), yaw = d.getFloat('wk_yaw'), f = wkFwd(yaw)
  if (wkAt(t, 0.2)) wkSound(e, 'minecraft:block.beacon.power_select', 1.5, 0.5)
  if (k >= 4 && k <= 13 && t % 2 == 0) { let pm = wkModel(p, yaw, wkProbe('hand_shockwave', 'palm', k)); wkParticle(e, 'minecraft:reverse_portal', pm, 0.3, 0.3, 0.3, 0.05, 6) }
  if (wkAt(t, 0.82)) {
    let pm = wkModel(p, yaw, wkProbe('hand_shockwave', 'palm', 16))
    wkSound(e, 'minecraft:entity.warden.sonic_boom', 2.5, 0.6, pm); wkSound(e, 'minecraft:entity.generic.explode', 1.5, 0.5, pm)
    for (let i = 1; i <= 4; i++) for (let s = -1; s <= 1; s++) {
      let a = yaw + s * WKC.shockwave.coneDegrees * 0.5, ff = wkFwd(a)
      wkParticle(e, 'minecraft:sonic_boom', { x: pm.x + ff[0] * i * 1.6, y: pm.y - i * 0.35, z: pm.z + ff[1] * i * 1.6 }, 0, 0, 0, 0, 1)
    }
    wkParticle(e, 'minecraft:cloud', { x: p.x + f[0] * 4, y: p.y + 0.3, z: p.z + f[1] * 4 }, 2.5, 0.1, 2.5, 0.05, 30)
    let cosA = Math.cos(WKC.shockwave.coneDegrees * Math.PI / 180)
    // speed for a given flight distance: ~8.1 x horizontal speed on level ground with vy 0.4 (drag + landing slide)
    let h = WKC.shockwave.pushBlocks / 8.1
    wkNear(e, WKC.shockwave.range + 2).forEach(x => {
      if (!wkTargetable(e, x)) return
      let q = wkP(x), dx = q.x - pm.x, dz = q.z - pm.z, n = Math.hypot(dx, dz)
      if (n > WKC.shockwave.range || n < 0.01 || q.y > pm.y + 4 || q.y + x.getBbHeight() < p.y - 2) return
      if ((dx * f[0] + dz * f[1]) / n < cosA) return
      wkHurt(e, x, WKC.shockwave.damage); wkKnock(x, dx / n * h, 0.4, dz / n * h)
    })
  }
  if (t >= wkLen('SHOCKWAVE')) wkEnd(e)
}

// --- 09 ground stomp: a 12-block ring that rolls out over the terrain; you're hit when it reaches you, once
function wkStomp(e, t, target) {
  let d = wkD(e), k = wkAnimTick(t)
  if (k < 14 && target) { wkSetYaw(e, wkYawTo(e, target)); d.putFloat('wk_yaw', wkYaw(e)) }
  else wkSetYaw(e, d.getFloat('wk_yaw'))
  let p = wkP(e), yaw = d.getFloat('wk_yaw')
  if (wkAt(t, 0.4)) wkSound(e, 'minecraft:entity.ravager.roar', 1.2, 0.5)
  if (wkAt(t, 0.9)) wkSound(e, 'minecraft:item.armor.equip_netherite', 1.5, 0.4)
  let impact = Math.round(1.38 * 20) + WK_TRANS
  if (t == impact) {
    let c = wkModel(p, yaw, wkProbe('ground_stomp', 'footL', Math.round(1.38 * 20)))
    d.putDouble('wk_rx', c.x); d.putDouble('wk_ry', p.y); d.putDouble('wk_rz', c.z)
    wkSound(e, 'minecraft:entity.generic.explode', 3, 0.4, c); wkSound(e, 'minecraft:entity.lightning_bolt.thunder', 1.6, 0.5, c)
    wkSound(e, 'minecraft:entity.warden.sonic_boom', 1.2, 0.4, c)
    wkParticle(e, 'minecraft:explosion', { x: c.x, y: p.y + 0.3, z: c.z }, 1.2, 0.2, 1.2, 0, 6)
    wkParticle(e, 'minecraft:campfire_cosy_smoke', { x: c.x, y: p.y + 0.2, z: c.z }, 1.5, 0.1, 1.5, 0.02, 20)
  }
  if (t >= impact) {
    let n = t - impact, r1 = n * WKC.stomp.ringBlocksPerTick, r0 = Math.max(0, r1 - WKC.stomp.ringBlocksPerTick)
    if (r0 < WKC.stomp.radius) {
      let c = { x: d.getDouble('wk_rx'), y: d.getDouble('wk_ry'), z: d.getDouble('wk_rz') }
      wkStompRing(e, c, Math.min(r1, WKC.stomp.radius), n)
      wkNear(e, WKC.stomp.radius + 3, 8).forEach(x => {
        if (!wkTargetable(e, x) || wkWasHit(e, x)) return
        let q = wkP(x), dist = Math.hypot(q.x - c.x, q.z - c.z), w = x.getBbWidth() / 2
        if (dist - w > r1 || dist + w < r0 || dist - w > WKC.stomp.radius) return
        let gy = wkSurface(e.level, q.x, q.z, q.y, 1, 3)
        if (isNaN(gy) || Math.abs(gy - c.y) > WKC.stomp.verticalRange) return
        if (q.y - gy > WKC.stomp.jumpClearance) return               // jumped over it
        wkMarkHit(e, x); wkHurt(e, x, WKC.stomp.damage)
        let dx = q.x - c.x, dz = q.z - c.z, nn = Math.max(0.01, dist)
        wkKnock(x, dx / nn * WKC.stomp.knockback, 0.55, dz / nn * WKC.stomp.knockback)
      })
    }
  }
  if (t >= wkLen('STOMP')) wkEnd(e)
}
// block-shaped fragments rise 0.2-0.6, tilt, hang and settle back; they are display entities, the world is untouched
function wkStompRing(e, c, r, n) {
  if (r < 0.5) return
  let lvl = e.level, circ = 2 * Math.PI * r, count = Math.min(WKC.stomp.maxFragmentsPerTick, Math.max(3, Math.floor(circ / WKC.stomp.fragmentSpacing)))
  let tag = `wkf_${wkId(e)}_${e.tickCount}`, off = Math.random() * Math.PI * 2, groups = 4
  for (let i = 0; i < count; i++) {
    let a = off + (i / count) * Math.PI * 2, x = c.x + Math.cos(a) * r, z = c.z + Math.sin(a) * r
    let gy = wkSurface(lvl, x, z, c.y, 3, 4)
    if (isNaN(gy) || Math.abs(gy - c.y) > WKC.stomp.verticalRange) continue
    let id = wkBlockId(lvl, x, gy - 1, z)
    if (id == 'minecraft:air') continue
    if (i % 3 == 0) wkParticle(e, `minecraft:block ${id}`, { x: x, y: gy + 0.2, z: z }, 0.4, 0.2, 0.4, 0.15, 6)
    if (i % 5 == 0) wkParticle(e, 'minecraft:campfire_cosy_smoke', { x: x, y: gy + 0.1, z: z }, 0.3, 0.05, 0.3, 0.01, 1)
    if (!WKC.stomp.fragments) continue
    wkRun(e, `summon block_display ${Math.floor(x)} ${gy - 1} ${Math.floor(z)} {block_state:{Name:"${id}"},Tags:["${tag}","${tag}_${i % groups}","wk_fragment"],transformation:{translation:[0.01f,0.01f,0.01f],left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],scale:[0.98f,0.98f,0.98f]}}`)
  }
  if (n % 4 == 0) wkSound(e, 'minecraft:block.basalt.break', 1.6, 0.5, { x: c.x + r, y: c.y, z: c.z })
  if (!WKC.stomp.fragments) return
  let quat = (ax, az, ang) => { let s = Math.sin(ang / 2); return `[${(ax * s).toFixed(3)}f,0f,${(az * s).toFixed(3)}f,${Math.cos(ang / 2).toFixed(3)}f]` }
  for (let g = 0; g < groups; g++) {
    let lift = 0.2 + 0.4 * (g / (groups - 1)), ax = [1, 0, 0.7, -0.7][g], az = [0, 1, 0.7, 0.7][g], ang = (g % 2 ? -1 : 1) * (0.08 + 0.05 * g)
    let sel = `@e[type=block_display,tag=${tag}_${g}]`
    e.server.scheduleInTicks(1, () => wkRun(e, `execute as ${sel} run data merge entity @s {interpolation_duration:3,start_interpolation:0,transformation:{translation:[0.01f,${lift.toFixed(2)}f,0.01f],left_rotation:${quat(ax, az, ang)},right_rotation:[0f,0f,0f,1f],scale:[0.98f,0.98f,0.98f]}}`))
    e.server.scheduleInTicks(7, () => wkRun(e, `execute as ${sel} run data merge entity @s {interpolation_duration:6,start_interpolation:0,transformation:{translation:[0.01f,0.01f,0.01f],left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],scale:[0.98f,0.98f,0.98f]}}`))
  }
  e.server.scheduleInTicks(15, () => wkRun(e, `kill @e[type=block_display,tag=${tag}]`))
}

// --- 10 death: The King's Last Rest. He stays alive (and untouchable) until the last frame, then drops his loot.
function wkDying(e, t) {
  let d = wkD(e); wkSetYaw(e, d.getFloat('wk_yaw')); wkSetPose(e, 'DIGGING')
  e.getNavigation().stop(); e.setTarget(null)
  let p = wkP(e), yaw = d.getFloat('wk_yaw'), k = wkAnimTick(t)
  if (t == 0) {
    wkSound(e, 'minecraft:entity.wither_skeleton.death', 2, 0.4); wkSound(e, 'minecraft:entity.iron_golem.damage', 2, 0.4)
    wkMinions(e).forEach(m => m.discard())
  }
  if (t % 10 == 0 && k < 180) wkParticle(e, 'minecraft:soul', { x: p.x, y: p.y + 3, z: p.z }, 1.0, 1.5, 1.0, 0.01, Math.max(1, 6 - Math.floor(k / 30)))
  if (wkAt(t, 2.6)) { wkSound(e, 'minecraft:entity.iron_golem.step', 2, 0.4); wkParticle(e, 'minecraft:campfire_cosy_smoke', { x: p.x, y: p.y + 0.2, z: p.z }, 1.2, 0.05, 1.2, 0.01, 10) }
  if (wkAt(t, 4.05)) {
    let tip = wkModel(p, yaw, wkProbe('death', 'tip', Math.round(4.05 * 20))), id = wkBlockId(e.level, tip.x, tip.y - 0.3, tip.z)
    wkSound(e, 'minecraft:block.anvil.land', 1.2, 0.45, tip)
    if (id != 'minecraft:air') wkParticle(e, `minecraft:block ${id}`, { x: tip.x, y: tip.y + 0.3, z: tip.z }, 0.4, 0.2, 0.4, 0.15, 25)
  }
  if (wkAt(t, 5.3)) wkSound(e, 'minecraft:block.chain.break', 1.0, 0.6)
  if (wkAt(t, 7.55)) { wkSound(e, 'minecraft:block.chain.place', 1.2, 0.5); wkSound(e, 'minecraft:block.amethyst_block.resonate', 1.2, 0.5) }
  if (wkAt(t, 9.1)) { wkSound(e, 'minecraft:entity.wither_skeleton.ambient', 1.5, 0.4); wkParticle(e, 'minecraft:poof', { x: p.x, y: p.y + 5, z: p.z }, 0.3, 0.2, 0.3, 0.02, 6) }
  if (wkAt(t, 10.0)) {
    wkSound(e, 'minecraft:block.bell.resonate', 1.5, 0.5); wkSound(e, 'minecraft:block.beacon.deactivate', 1.5, 0.5)
    wkParticle(e, 'minecraft:falling_dust minecraft:gravel', { x: p.x, y: p.y + 4, z: p.z }, 2, 2, 2, 0, 40)
    if (WKC.death.stopMusic) wkRun(e, `stopsound @a[x=${wkF(p.x)},y=${wkF(p.y)},z=${wkF(p.z)},distance=..64] music`)
  }
  if (t >= wkLen('DYING')) wkFinish(e)
}
function wkFinish(e) {
  let d = wkD(e)
  if (d.getBoolean('wk_dead')) return
  d.putBoolean('wk_dead', true); d.putBoolean('wk_finish', true)
  let killer = null
  try { let s = String(d.getString('wk_killer')); if (s) killer = e.level.getPlayerByUUID($WkUUID.fromString(s)) } catch (err) {}
  if (!killer) try { killer = e.level.getNearestPlayer(e, 48) } catch (err) {}
  try { if (killer) e.setLastHurtByPlayer(killer) } catch (err) { wkLogOnce('lastHurtByPlayer', err) }
  let p = wkP(e), orbs = 6, each = Math.max(1, Math.floor(WKC.death.xp / orbs))
  for (let i = 0; i < orbs; i++) wkRun(e, `summon experience_orb ${wkF(p.x + (Math.random() - 0.5) * 2)} ${wkF(p.y + 0.5)} ${wkF(p.z + (Math.random() - 0.5) * 2)} {Value:${each}}`)
  global.wkClearBar(e)
  wkDebug('DEAD')
  e.kill()                       // vanilla death now: drops the loot table (kubejs:entities/withered_king)
}
global.wkTickDeath = e => {
  let d = wkD(e), n = d.getInt('wk_dissolve') + 1
  d.putInt('wk_dissolve', n)
  let p = wkP(e)
  if (n == 1 && WKC.death.monument) {
    wkRun(e, `summon kubejs:${WK}_remains ${wkF(p.x)} ${wkF(p.y)} ${wkF(p.z)} {NoAI:1b,PersistenceRequired:1b,Rotation:[${wkF(d.getFloat('wk_yaw'))}f,0f]}`)
    e.discard(); return
  }
  if (n % 3 == 0) {
    wkParticle(e, 'minecraft:soul', { x: p.x, y: p.y + 2.5, z: p.z }, 1.0, 1.5, 1.0, 0.02, 4)
    wkParticle(e, 'minecraft:ash', { x: p.x, y: p.y + 3, z: p.z }, 1.2, 2, 1.2, 0.02, 20)
    wkParticle(e, 'minecraft:large_smoke', { x: p.x, y: p.y + 1.5, z: p.z }, 1.0, 1.0, 1.0, 0.01, 2)
  }
  if (n == 2) wkSound(e, 'minecraft:block.sand.break', 1.5, 0.4)
  if (n >= WKC.death.dissolveTicks) { e.level.broadcastEntityEvent(e, 60); e.discard() }
}
