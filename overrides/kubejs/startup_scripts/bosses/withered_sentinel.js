// The Withered Sentinel: an ancient obsidian knight with a beating violet heart, guardian of the End portal.
// Model / animations / textures: kubejs/assets/kubejs/{geo,animations,textures}/entity/withered_sentinel*
// Built in Blender: dev/sentinel_knight (sk_build.py model + rig, sk_anims.py animations, sk_export.py GeckoLib export).
// Needs EntityJS (+ GeckoLib, KubeJS). Spawn with the egg or: /summon kubejs:withered_sentinel
//
// He waits kneeling on his sword (dormant, can't be hurt) until a player comes within 16 blocks, then AWAKENS.
// Moves (frame numbers = ticks of the Blender animations):
//   sweep         two-handed sweep, a 230-degree arc in front of him, ~6.5 blocks (hit on tick 24)
//   push          left palm thrust: a cube shockwave in a 9-block cone (tick 20)
//   summon        drives the sword into the stone, raises a hand and calls the dead; he can't be hurt until they fall
//   stomp         (phase 2) foot slam: everything within ~5 blocks, the ground heaves (tick 19)
//   dash          (phase 2) explosive lunge at a distant player (ticks 9-16), with a short purple blink
// The armour never glows: purple light comes from his heart; all other purple magic is temporary, spawned on events.

const $Attributes = Java.loadClass('net.minecraft.world.entity.ai.attributes.Attributes')
const $AABB = Java.loadClass('net.minecraft.world.phys.AABB')
const $BossEvent = Java.loadClass('net.minecraft.server.level.ServerBossEvent')
const $BarColor = Java.loadClass('net.minecraft.world.BossEvent$BossBarColor')
const $BarOverlay = Java.loadClass('net.minecraft.world.BossEvent$BossBarOverlay')
const $Vec3 = Java.loadClass('net.minecraft.world.phys.Vec3')

const WS = 'withered_sentinel'
const WS_ANIM = n => `animation.${WS}.${n}`
const WS_TEX = n => `kubejs:textures/entity/${n}.png`
const WS_ACTIONS = ['sweep', 'push', 'summon_start', 'summon_loop', 'summon_end', 'awaken', 'stomp', 'dash']
const WS_LOOPS = { summon_start: 'HOLD_ON_LAST_FRAME', summon_loop: 'LOOP' }
const WS_LEN = { sweep: 50, push: 40, summon_start: 40, summon_end: 30, awaken: 100, stomp: 40, dash: 32 }
const WS_SCALE = 1.4                      // model scale: 86 px model -> ~7.5 blocks tall
const WS_PX = WS_SCALE / 16               // one model pixel in blocks

StartupEvents.registry('entity_type', event => {
  event.create(WS, 'entityjs:mob')
    .sized(3.0, 7.2)
    .modelSize(WS_SCALE, WS_SCALE)
    .clientTrackingRange(16)
    .updateInterval(1)
    .fireImmune(true)
    .isPushable(false)
    .canBreatheUnderwater(true)
    .isPersistenceRequired(true)
    .removeWhenFarAway(ctx => false)
    .mobCategory('monster')
    .eggItem(egg => egg.backgroundColor(0x0b0a10).highlightColor(0x9b3cff))
    .modelResource(e => `kubejs:geo/entity/${WS}.geo.json`)
    .animationResource(e => `kubejs:animations/entity/${WS}.animation.json`)
    .textureResource(e => WS_TEX(WS))
    .newGlowingGeoLayer(layer => layer.textureResource(e => WS_TEX(`${WS}_glowmask`)))
    .attributes(a => {
      a.add($Attributes.MAX_HEALTH, 700)
      a.add($Attributes.ARMOR, 16)
      a.add($Attributes.ARMOR_TOUGHNESS, 8)
      a.add($Attributes.KNOCKBACK_RESISTANCE, 1.0)
      a.add($Attributes.MOVEMENT_SPEED, 0.27)   // the walk cycle covers 0.9 px/tick at scale 1.4: feet stay planted
      a.add($Attributes.FOLLOW_RANGE, 48)
      a.add($Attributes.ATTACK_DAMAGE, 16)
    })
    // one controller: dormant / idle / combat stance / walk / death from the predicate, every attack as a trigger
    .addAnimationController('base', 6, ev => {
      try {
        WS_ACTIONS.forEach(n => ev.addTriggerableAnimation(WS_ANIM(n), n, WS_LOOPS[n] || 'PLAY_ONCE'))
        let e = ev.entity
        if (e.isDeadOrDying()) ev.thenPlayAndHold(WS_ANIM('death'))
        else if (!e.persistentData.getBoolean('ws_awake')) ev.thenLoop(WS_ANIM('dormant'))
        else if (ev.isMoving()) ev.thenLoop(WS_ANIM('walk'))
        else if (e.isAggressive()) ev.thenLoop(WS_ANIM('idle_combat'))
        else ev.thenLoop(WS_ANIM('idle'))
      } catch (err) {}
      return true
    })
    .isInvulnerableTo(ctx => {
      let d = ctx.entity.persistentData
      return d.getBoolean('ws_guarded') || !d.getBoolean('ws_awake')
    })
    .tick(e => {
      if (e.level.isClientSide()) return
      try { global.wsTick(e) } catch (err) { wsLogOnce('tick', err) }
    })
    .tickDeath(e => {
      if (e.level.isClientSide()) return
      try {
        let d = e.persistentData, n = d.getInt('ws_dying') + 1
        d.putInt('ws_dying', n)
        global.wsDeathFx(e, n)
        if (n >= 108) { e.level.broadcastEntityEvent(e, 60); e.discard() }
      } catch (err) { wsLogOnce('death', err); e.discard() }
    })
    .onDeath(ctx => { if (!ctx.entity.level.isClientSide()) try { global.wsOnDeath(ctx.entity) } catch (err) { wsLogOnce('onDeath', err) } })
    .onRemovedFromWorld(e => { if (!e.level.isClientSide()) try { global.wsClearBar(e) } catch (err) { wsLogOnce('removed', err) } })
    .setHurtSound(ctx => 'minecraft:entity.iron_golem.hurt')
    .setDeathSound('minecraft:entity.wither.death')
    .setSoundVolume(2.0)
})

// AI goals (target players, look around) live in server_scripts/bosses/withered_sentinel_goals.js.

// ------------------------------------------------------------------ helpers
global.wsBars = global.wsBars || {}
function wsId(e) {
  let d = e.persistentData
  if (!d.contains('ws_id')) d.putString('ws_id', Math.floor(Math.random() * 0xfffffff).toString(16))
  return String(d.getString('ws_id'))
}
global.wsLogged = global.wsLogged || {}
function wsLogOnce(where, err) {
  if (global.wsLogged[where]) return
  global.wsLogged[where] = true
  console.error(`[Withered Sentinel] ${where}: ${err}`)
}
// Rhino in this pack can't read entity.x/.y/.z reliably, so positions go through position() and are checked.
function wsNum(v) { try { if (typeof v == 'function') return NaN; let n = Number(v); return isFinite(n) ? n : NaN } catch (err) { return NaN } }
function wsVec(v) {
  let x = wsNum(v.x), y = wsNum(v.y), z = wsNum(v.z)
  if (isFinite(x) && isFinite(y) && isFinite(z)) return { x: x, y: y, z: z }
  try { x = wsNum(v.x()); y = wsNum(v.y()); z = wsNum(v.z()) } catch (err) {}
  if (isFinite(x) && isFinite(y) && isFinite(z)) return { x: x, y: y, z: z }
  return null
}
function wsP(o) {
  let r = null
  try { r = wsVec(o.position()) } catch (err) {}
  if (!r) try { let x = wsNum(o.getX()), y = wsNum(o.getY()), z = wsNum(o.getZ()); if (isFinite(x) && isFinite(y) && isFinite(z)) r = { x: x, y: y, z: z } } catch (err) {}
  if (!r) try { let b = o.blockPosition(); r = { x: b.getX() + 0.5, y: b.getY(), z: b.getZ() + 0.5 } } catch (err) {}
  if (!r) { wsLogOnce('position', 'could not read a position'); r = { x: 0, y: 0, z: 0, bad: true } }
  return r
}
function wsDist(a, b) { let p = wsP(a), q = wsP(b); if (p.bad || q.bad) return 999; let dx = p.x - q.x, dz = p.z - q.z; return Math.sqrt(dx * dx + dz * dz) }
// yaw access differs between KubeJS / EntityJS builds (getYRot is not exposed on EntityJS mobs here), so every
// known accessor is tried; the one that works is remembered and logged once.
// (never store null in `global`: reading a null entry of that Java map crashes Rhino outside any try/catch)
global.wsYawGet = global.wsYawGet || ''
function wsYaw(e) {
  let tries = [['getYaw', x => x.getYaw()], ['yaw', x => x.yaw], ['getYRot', x => x.getYRot()], ['yRot', x => x.yRot],
               ['getYHeadRot', x => x.getYHeadRot()], ['nbt', x => x.nbt.getList('Rotation', 5).getFloat(0)]]
  if (global.wsYawGet) tries.sort((a, b) => (a[0] == global.wsYawGet ? -1 : b[0] == global.wsYawGet ? 1 : 0))
  for (let i = 0; i < tries.length; i++) {
    let v = NaN
    try { v = wsNum(tries[i][1](e)) } catch (err) {}
    if (isFinite(v)) { if (global.wsYawGet != tries[i][0]) { global.wsYawGet = tries[i][0]; console.info(`[Withered Sentinel] yaw read via ${tries[i][0]}`) } return v }
  }
  return 0
}
function wsSetYaw(e, yaw) {
  let done = false
  ;['setYaw', 'setYRot'].forEach(m => { if (!done) try { e[m](yaw); done = true } catch (err) {} })
  ;['setYHeadRot', 'setYBodyRot', 'setHeadYaw', 'setBodyYaw'].forEach(m => { try { e[m](yaw) } catch (err) {} })
  if (!done) try { e.server.runCommandSilent(`execute as ${e.getStringUuid()} at @s run tp @s ~ ~ ~ ${yaw.toFixed(2)} ~`) } catch (err) { wsLogOnce('setYaw', err) }
}
function wsFace(e, t) {
  let p = wsP(e), q = wsP(t)
  if (p.bad || q.bad) return
  let yaw = Math.atan2(q.z - p.z, q.x - p.x) * 180 / Math.PI - 90
  if (!isFinite(yaw)) return
  wsSetYaw(e, yaw)
}
function wsFwd(e) { let r = wsYaw(e) * Math.PI / 180; if (!isFinite(r)) r = 0; return [-Math.sin(r), Math.cos(r)] }
// a point in his own frame, in model pixels: left (+ = his left), up, fwd (+ = in front of him)
function wsLocal(e, left, up, fwd) {
  let p = wsP(e), f = wsFwd(e), lx = f[1], lz = -f[0]   // his left = forward rotated +90 degrees
  return { x: p.x + (f[0] * fwd + lx * left) * WS_PX, y: p.y + up * WS_PX, z: p.z + (f[1] * fwd + lz * left) * WS_PX }
}
function wsNear(e, r) {
  let p = wsP(e)
  return e.level.getEntities(e, new $AABB(p.x - r, p.y - 3, p.z - r, p.x + r, p.y + 10, p.z + r))
}
function wsCmd(e, c) { let p = wsP(e); e.server.runCommandSilent(`execute in ${e.level.dimension} positioned ${p.x} ${p.y} ${p.z} run ${c}`) }
function wsAt(e, q, c) { e.server.runCommandSilent(`execute in ${e.level.dimension} positioned ${q.x.toFixed(3)} ${q.y.toFixed(3)} ${q.z.toFixed(3)} run ${c}`) }
function wsIsMinion(e, x) { try { return x.getTags().contains('wsm_' + wsId(e)) } catch (err) { return false } }

// hit every living thing in range (not his minions); arc = cosine of the half-angle in front (-1 = all round)
function wsHit(e, range, arc, dmg, push, lift) {
  let f = wsFwd(e), hit = 0
  wsNear(e, range + 2).forEach(x => {
    if (!x.isLiving() || !x.isAlive() || wsIsMinion(e, x)) return
    if (x.isPlayer() && (x.isCreative() || x.isSpectator())) return
    let px = wsP(x), pe = wsP(e)
    if (px.bad || pe.bad) return
    let dx = px.x - pe.x, dz = px.z - pe.z, d = Math.sqrt(dx * dx + dz * dz)
    if (d > range + x.getBbWidth() / 2) return
    let nx = d > 0.01 ? dx / d : f[0], nz = d > 0.01 ? dz / d : f[1]
    if (arc > -1 && nx * f[0] + nz * f[1] < arc) return
    if (dmg > 0) x.attack(e.damageSources().mobAttack(e), dmg)
    x.setDeltaMovement(new $Vec3(nx * push, lift, nz * push))
    x.hurtMarked = true
    hit++
  })
  return hit
}

// ------------------------------------------------------------------ purple voxel magic (temporary, event driven)
// dust particles render as small squares: the voxel cubes / blocky smoke. 'enchant' are rune glyphs.
const WS_DARK = 'minecraft:dust 0.32 0.04 0.55', WS_VIOLET = 'minecraft:dust 0.72 0.32 1.0', WS_PALE = 'minecraft:dust 0.9 0.7 1.0'
function fxDust(e, q, col, size, spread, n, speed) { wsAt(e, q, `particle ${col} ${size} ~ ~ ~ ${spread} ${spread} ${spread} ${speed || 0} ${n} force`) }
function fxCubes(e, q, spread, n) { fxDust(e, q, WS_DARK, 1.6, spread, Math.ceil(n * 0.6), 0.02); fxDust(e, q, WS_VIOLET, 1.1, spread, Math.ceil(n * 0.4), 0.02) }
function fxRunes(e, q, spread, n) { wsAt(e, q, `particle minecraft:enchant ~ ~ ~ ${spread} ${spread} ${spread} 0.6 ${n} force`) }
function fxShards(e, q, spread, n) {
  wsAt(e, q, `particle minecraft:block crying_obsidian ~ ~ ~ ${spread} 0.3 ${spread} 0.4 ${n} force`)
  wsAt(e, q, `particle minecraft:block obsidian ~ ~ ~ ${spread} 0.3 ${spread} 0.4 ${Math.ceil(n / 2)} force`)
}
function fxHeart(e, strength) {           // energy escaping between the ribs
  let q = wsLocal(e, 0, 58, 4)
  fxDust(e, q, WS_VIOLET, 0.9 + 0.5 * strength, 0.25, Math.ceil(2 * strength), 0.01)
  if (strength > 1) fxDust(e, q, WS_PALE, 0.7, 0.15, Math.ceil(strength), 0.02)
}
function fxRing(e, radius, col, size, n, up) {
  let p = wsP(e)
  for (let i = 0; i < n; i++) {
    let a = i / n * Math.PI * 2
    fxDust(e, { x: p.x + Math.cos(a) * radius, y: p.y + (up || 0.2), z: p.z + Math.sin(a) * radius }, col, size, 0.08, 1, 0)
  }
}
// sword trail: dust along the blade at a given azimuth (deg, + = his left) and height, in model px from his centre
function fxBlade(e, az, up, from, to) {
  let a = az * Math.PI / 180
  for (let s = from; s <= to; s += 6) {
    let q = wsLocal(e, Math.sin(a) * s, up, Math.cos(a) * s)
    fxDust(e, q, s % 12 == 0 ? WS_VIOLET : WS_DARK, 1.3, 0.05, 1, 0)
  }
}

// ------------------------------------------------------------------ boss bar, death
function wsBar(e) {
  let id = wsId(e), bar = global.wsBars[id]
  if (!bar) {
    bar = new $BossEvent(Text.of('The Withered Sentinel').darkPurple(), $BarColor.PURPLE, $BarOverlay.NOTCHED_10)
    global.wsBars[id] = bar
  }
  bar.setProgress(Math.max(0, Math.min(1, e.getHealth() / e.getMaxHealth())))
  e.server.players.forEach(p => {
    let near = e.persistentData.getBoolean('ws_awake') && p.level == e.level && wsDist(p, e) < 48
    if (near) bar.addPlayer(p); else bar.removePlayer(p)
  })
}
global.wsClearBar = e => { let id = wsId(e); if (global.wsBars[id]) { global.wsBars[id].removeAllPlayers(); delete global.wsBars[id] } }
function wsTrigger(e, action) {
  try { e.triggerAnimation('base', action) } catch (err) {
    try { e.triggerAnim('base', action) } catch (err2) { wsLogOnce('trigger', err2) }
  }
}
function wsStopAll(e) { WS_ACTIONS.forEach(n => { try { e.stopTriggeredAnimation('base', n) } catch (err) {} }) }
function wsStart(e, action) {
  let d = e.persistentData
  d.putString('ws_act', action); d.putInt('ws_t', 0)
  e.getNavigation().stop()
  wsTrigger(e, action)
}
global.wsOnDeath = e => {
  wsStopAll(e)
  wsCmd(e, `kill @e[tag=wsm_${wsId(e)}]`)
}
// death: recoil, the sword clatters down (t30), violent heartbeats, a final eruption at t77, then the light dies
global.wsDeathFx = (e, n) => {
  if (n == 30) { wsAt(e, wsLocal(e, -14, 1, 16), 'playsound minecraft:block.anvil.land hostile @a ~ ~ ~ 2 0.5'); fxShards(e, wsLocal(e, -14, 1, 18), 0.8, 10) }
  if (n >= 34 && n <= 74 && n % 4 == 0) { fxHeart(e, 2.2); if (n % 8 == 0) wsCmd(e, 'playsound minecraft:entity.warden.heartbeat hostile @a ~ ~ ~ 3 0.7') }
  if (n == 77) {
    let q = wsLocal(e, 0, 40, 12)
    fxDust(e, q, WS_VIOLET, 2.5, 1.4, 70, 0.15); fxDust(e, q, WS_DARK, 3.0, 1.8, 60, 0.12); fxDust(e, q, WS_PALE, 1.4, 0.8, 30, 0.2)
    fxShards(e, q, 1.5, 40); fxRunes(e, q, 2.0, 80)
    wsCmd(e, 'playsound minecraft:entity.generic.explode hostile @a ~ ~ ~ 3 0.6')
    wsCmd(e, 'playsound minecraft:block.respawn_anchor.deplete hostile @a ~ ~ ~ 3 0.5')
  }
  if (n > 80 && n < 100 && n % 3 == 0) fxDust(e, wsLocal(e, 0, 30, 10), WS_DARK, 2.0, 1.2, 4, 0.03)   // smoke drifting away
}

// the ground heaves in a ring around him and settles again (block displays)
function wsQuake(e) {
  let tag = `wsq_${wsId(e)}_${e.tickCount}`, pe = wsP(e), cx = Math.floor(pe.x), cz = Math.floor(pe.z), y = Math.floor(pe.y) - 1
  for (let dx = -6; dx <= 6; dx++) for (let dz = -6; dz <= 6; dz++) {
    let r = Math.sqrt(dx * dx + dz * dz)
    if (r < 1.5 || r > 5.4) continue
    let block = e.level.getBlock(cx + dx, y, cz + dz)
    if (!block || block.id == 'minecraft:air' || !block.blockState.isSolidRender(e.level, block.pos)) continue
    e.server.runCommandSilent(`execute in ${e.level.dimension} run summon block_display ${cx + dx} ${y} ${cz + dz} {block_state:{Name:"${block.id}"},Tags:["${tag}"],interpolation_duration:3}`)
  }
  let sel = `@e[type=block_display,tag=${tag}]`
  let tf = h => `{transformation:{translation:[0f,${h}f,0f],left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],scale:[1f,1f,1f]},start_interpolation:0}`
  e.server.scheduleInTicks(1, () => e.server.runCommandSilent(`execute as ${sel} run data merge entity @s ${tf(0.55)}`))
  e.server.scheduleInTicks(7, () => e.server.runCommandSilent(`execute as ${sel} run data merge entity @s {interpolation_duration:5,start_interpolation:0,transformation:{translation:[0f,0f,0f],left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],scale:[1f,1f,1f]}}`))
  e.server.scheduleInTicks(14, () => e.server.runCommandSilent(`kill ${sel}`))
}
function wsMinionsAlive(e) { let n = 0; wsNear(e, 64).forEach(x => { if (x.isAlive() && wsIsMinion(e, x)) n++ }); return n }

// ------------------------------------------------------------------ the fight
global.wsTick = e => {
  let d = e.persistentData
  if (!d.contains('ws_init')) {
    d.putBoolean('ws_init', true)
    d.putInt('cd_sweep', 20); d.putInt('cd_push', 120); d.putInt('cd_summon', 300); d.putInt('cd_stomp', 60); d.putInt('cd_dash', 160)
  }
  if (e.tickCount % 5 == 0) wsBar(e)
  ;['cd_sweep', 'cd_push', 'cd_summon', 'cd_stomp', 'cd_dash'].forEach(k => { if (d.getInt(k) > 0) d.putInt(k, d.getInt(k) - 1) })
  let target = e.getTarget()
  let act = d.getString('ws_act'), t = d.getInt('ws_t')
  let p2 = e.getHealth() <= e.getMaxHealth() * 0.5

  // ---- dormant: kneeling on his sword until a player comes close (or hits him)
  if (!d.getBoolean('ws_awake') && act != 'awaken') {
    e.getNavigation().stop(); e.setAggressive(false)
    if (e.tickCount % 40 == 0) fxHeart(e, 0.4)
    let wake = false
    e.server.players.forEach(p => { if (!p.isCreative() && !p.isSpectator() && p.level == e.level && wsDist(p, e) < 16) wake = true })
    if (wake || target) { d.putBoolean('ws_guarded', true); wsStart(e, 'awaken') }
    return
  }
  e.setAggressive(!!target)

  // ---- ambient magic: faint runes near the shoulders, pixels rising from his boots, the heart breathing light
  if (act == '' && e.tickCount % 23 == 0) fxRunes(e, wsLocal(e, (Math.random() < 0.5 ? -1 : 1) * 16, 62, 0), 0.4, 3)
  if (act == '' && e.tickCount % 31 == 0) fxDust(e, wsLocal(e, (Math.random() - 0.5) * 16, 2, -2), WS_DARK, 1.2, 0.35, 3, 0.01)
  if (e.tickCount % (target ? 12 : 30) == 0) fxHeart(e, target ? 1.0 : 0.5)

  if (act != '') {
    d.putInt('ws_t', t + 1)
    if (act == 'awaken') {
      // dormant -> fingers tighten (20) -> rises, draws the sword (40-64) -> guard -> heart flare (80)
      if (t == 2) wsCmd(e, 'playsound minecraft:block.respawn_anchor.charge hostile @a ~ ~ ~ 3 0.5')
      if (t >= 20 && t < 78 && t % 3 == 0) {                           // runes and cubes stream into his heart
        let a = t * 0.4, q = wsLocal(e, Math.cos(a) * 30, 30 + (t % 30), Math.sin(a) * 30)
        fxRunes(e, q, 0.3, 4); fxDust(e, q, WS_DARK, 1.4, 0.2, 2, 0)
      }
      if (t == 40) wsCmd(e, 'playsound minecraft:entity.warden.emerge hostile @a ~ ~ ~ 3 0.7')
      if (t == 52) { wsAt(e, wsLocal(e, -2, 1, 22), 'playsound minecraft:block.stone.break hostile @a ~ ~ ~ 3 0.4'); fxShards(e, wsLocal(e, -2, 1, 22), 0.6, 18) }
      if (t == 80) {
        let q = wsLocal(e, 0, 58, 4)
        fxDust(e, q, WS_VIOLET, 2.2, 1.0, 60, 0.18); fxDust(e, q, WS_PALE, 1.2, 0.6, 30, 0.25); fxRunes(e, q, 2.5, 60)
        fxRing(e, 3.5, WS_DARK, 2.0, 36, 0.3)
        wsCmd(e, 'playsound minecraft:entity.warden.roar hostile @a ~ ~ ~ 4 0.6')
        wsHit(e, 6, -1, 0, 1.6, 0.4)
      }
      if (t >= WS_LEN.awaken) { d.putBoolean('ws_awake', true); d.putBoolean('ws_guarded', false) }
    } else if (act == 'sweep') {
      if (t < 18 && target) wsFace(e, target)
      if (t >= 8 && t <= 18 && t % 3 == 0) fxHeart(e, 1.6)
      if (t == 20) wsCmd(e, 'playsound minecraft:entity.player.attack.sweep hostile @a ~ ~ ~ 3 0.4')
      // trail along the blade's real path: azimuth from the animation (+ = his left)
      let AZ = { 20: -95, 21: -70, 22: -44, 23: -18, 24: 8, 25: 30, 26: 50, 27: 70, 28: 86 }
      if (AZ[t] !== undefined) fxBlade(e, AZ[t], 44, 20, 80)
      if (t == 24) {
        wsHit(e, 6.5, -0.42, 17, 1.7, 0.35)
        let f = wsFwd(e)
        wsCmd(e, `particle minecraft:sweep_attack ~${f[0] * 3} ~3 ~${f[1] * 3} 2 0.4 2 0 10 force`)
        fxCubes(e, wsLocal(e, 0, 40, 50), 1.5, 24)
      }
    } else if (act == 'push') {
      if (t < 16 && target) wsFace(e, target)
      if (t >= 4 && t <= 16 && t % 2 == 0) fxDust(e, wsLocal(e, 9, 52, 4), WS_VIOLET, 1.0, 0.15, 3, 0.02)   // gathering in the claw
      if (t == 20) {
        // a blocky shockwave: expanding square bursts and shards down a cone
        for (let i = 1; i <= 6; i++) {
          let q = wsLocal(e, 0, 44, 30 + i * 18)
          e.server.scheduleInTicks(i, () => { fxCubes(e, q, 0.3 + i * 0.25, 10 + i * 3); fxShards(e, q, 0.3 + i * 0.2, 4) })
        }
        wsCmd(e, 'playsound minecraft:entity.warden.sonic_boom hostile @a ~ ~ ~ 3 0.7')
        wsHit(e, 9, 0.5, 7, 2.6, 0.55)
      }
    } else if (act == 'stomp') {
      if (t >= 8 && t <= 16 && t % 2 == 0) fxHeart(e, 1.8)
      if (t == 19) {
        wsCmd(e, 'playsound minecraft:entity.generic.explode hostile @a ~ ~ ~ 3 0.6')
        let q = wsLocal(e, -7, 1, 2)
        fxShards(e, q, 1.2, 40); fxRing(e, 2.5, WS_DARK, 2.2, 28, 0.2); fxRing(e, 4.5, WS_VIOLET, 1.6, 40, 0.2)
        e.server.scheduleInTicks(3, () => fxRing(e, 5.5, WS_DARK, 1.8, 44, 0.2))
        wsQuake(e)
        wsHit(e, 5, -1, 15, 1.0, 0.9)
      }
    } else if (act == 'dash') {
      if (t < 8 && target) wsFace(e, target)
      if (t == 8) {                                                      // a short purple blink at the start
        fxDust(e, wsLocal(e, 0, 30, 0), WS_DARK, 2.0, 0.8, 30, 0.1); wsCmd(e, 'particle minecraft:reverse_portal ~ ~2 ~ 0.8 1.6 0.8 0.3 60 force')
        wsCmd(e, 'playsound minecraft:entity.enderman.teleport hostile @a ~ ~ ~ 2 0.5')
        wsCmd(e, 'playsound minecraft:entity.ravager.roar hostile @a ~ ~ ~ 3 0.7')
      }
      if (t >= 9 && t <= 16) {
        let f = wsFwd(e)
        let vy = 0; try { let v = wsVec(e.getDeltaMovement()); if (v) vy = v.y } catch (err) {}
        e.setDeltaMovement(new $Vec3(f[0] * 1.3, vy, f[1] * 1.3)); e.hurtMarked = true
        fxDust(e, wsLocal(e, 0, 6, -10), WS_DARK, 1.8, 0.4, 4, 0.01)    // voxel trail behind him
        if (!d.getBoolean('ws_dash_hit') && wsHit(e, 3.5, 0.2, 18, 1.4, 0.4) > 0) d.putBoolean('ws_dash_hit', true)
      }
      if (t == 17) {                                                     // brakes on planted feet, purple burst
        let f = wsFwd(e), vy = 0; try { let v = wsVec(e.getDeltaMovement()); if (v) vy = v.y } catch (err) {}
        e.setDeltaMovement(new $Vec3(f[0] * 0.1, vy, f[1] * 0.1)); e.hurtMarked = true
        fxCubes(e, wsLocal(e, 0, 20, 10), 1.0, 30); fxShards(e, wsLocal(e, 0, 1, 12), 1.0, 14)
        wsCmd(e, 'playsound minecraft:entity.iron_golem.damage hostile @a ~ ~ ~ 3 0.5')
      }
    } else if (act == 'summon_start') {
      if (t == 2) wsCmd(e, 'playsound minecraft:entity.evoker.prepare_summon hostile @a ~ ~ ~ 3 0.6')
      if (t == 20) { wsAt(e, wsLocal(e, -12, 1, 22), 'playsound minecraft:entity.generic.explode hostile @a ~ ~ ~ 2 0.5'); fxShards(e, wsLocal(e, -12, 1, 22), 0.8, 24) }
      if (t >= 22) {                                                      // runes and cubes orbit the raised hand
        let h = wsLocal(e, 18, 74, 16), a = t * 0.5
        fxRunes(e, { x: h.x + Math.cos(a) * 1.0, y: h.y, z: h.z + Math.sin(a) * 1.0 }, 0.1, 3)
        fxDust(e, { x: h.x + Math.cos(a + 3) * 0.8, y: h.y + 0.2, z: h.z + Math.sin(a + 3) * 0.8 }, WS_VIOLET, 1.0, 0.05, 1, 0)
      }
      if (t == 30) {
        let tag = 'wsm_' + wsId(e), mobs = ['minecraft:wither_skeleton', 'minecraft:wither_skeleton', 'minecraft:skeleton']
        if (p2) mobs.push('minecraft:wither_skeleton')
        let pe = wsP(e)
        mobs.forEach((m, i) => {
          let a = (i / mobs.length) * Math.PI * 2, x = pe.x + Math.cos(a) * 6, z = pe.z + Math.sin(a) * 6
          e.server.runCommandSilent(`execute in ${e.level.dimension} run summon ${m} ${x} ${pe.y} ${z} {Tags:["${tag}","ws_minion"],PersistenceRequired:1b}`)
          fxCubes(e, { x: x, y: pe.y + 1, z: z }, 0.5, 20); fxRunes(e, { x: x, y: pe.y + 1, z: z }, 0.6, 20)
        })
        d.putBoolean('ws_guarded', true)
      }
      if (t >= WS_LEN.summon_start) { d.putString('ws_act', 'summon_hold'); d.putInt('ws_t', 0); wsTrigger(e, 'summon_loop') }
    } else if (act == 'summon_hold') {
      let h = wsLocal(e, 18, 74, 16), a = t * 0.35
      for (let k = 0; k < 2; k++) fxRunes(e, { x: h.x + Math.cos(a + k * Math.PI) * 1.2, y: h.y + Math.sin(a * 0.7) * 0.4, z: h.z + Math.sin(a + k * Math.PI) * 1.2 }, 0.05, 2)
      if (t % 4 == 0) fxDust(e, { x: h.x + Math.cos(-a) * 0.9, y: h.y, z: h.z + Math.sin(-a) * 0.9 }, WS_DARK, 1.3, 0.05, 2, 0)
      if (t % 10 == 0 && wsMinionsAlive(e) == 0) { d.putBoolean('ws_guarded', false); wsStart(e, 'summon_end'); d.putInt('cd_summon', 900) }
    } else if (act == 'summon_end') {
      if (t == 13) {                                                      // the gathered energy is flung away
        let h = wsLocal(e, 22, 50, 18)
        fxDust(e, h, WS_VIOLET, 1.8, 0.8, 40, 0.25); fxRunes(e, h, 1.5, 40)
        wsCmd(e, 'playsound minecraft:entity.illusioner.cast_spell hostile @a ~ ~ ~ 3 0.6')
      }
    }
    let len = WS_LEN[act]
    if (len && t >= len && act != 'summon_start') { d.putString('ws_act', ''); d.putBoolean('ws_dash_hit', false) }
    return
  }

  // ---- choosing the next move
  if (!target || !target.isAlive()) { e.getNavigation().stop(); return }
  let dist = wsDist(e, target), r = Math.random()
  if (d.getInt('cd_summon') == 0 && e.getHealth() < e.getMaxHealth() * 0.8 && dist < 24) { wsStart(e, 'summon_start'); return }
  if (p2 && d.getInt('cd_stomp') == 0 && dist < 5.5) { wsStart(e, 'stomp'); d.putInt('cd_stomp', 160); return }
  if (p2 && d.getInt('cd_dash') == 0 && dist > 8 && dist < 20 && r < 0.05) { wsStart(e, 'dash'); d.putInt('cd_dash', 300); return }
  if (d.getInt('cd_push') == 0 && dist < 7 && r < 0.35) { wsStart(e, 'push'); d.putInt('cd_push', 200); return }
  if (d.getInt('cd_sweep') == 0 && dist < 6.2) { wsStart(e, 'sweep'); d.putInt('cd_sweep', 50); return }
  if (dist > 5.0) e.getNavigation().moveTo(target, 1.0)
  else { e.getNavigation().stop(); wsFace(e, target) }
}
