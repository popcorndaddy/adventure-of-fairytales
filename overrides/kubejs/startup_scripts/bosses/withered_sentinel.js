// The Withered Sentinel: guardian of the End portal (test build).
// Model, textures and animations: kubejs/assets/kubejs/{geo,textures,animations}/entity/withered_sentinel*
// Needs EntityJS (+ GeckoLib, KubeJS). Spawn with the egg or: /summon kubejs:withered_sentinel
//
// Moves
//   sweep   - slow giant sword sweep in front of him (~4 blocks)
//   push    - left palm thrust: a shockwave that throws players back
//   summon  - kneels, drives the sword into the ground and calls the dead to fight for him.
//             He stays down and takes no damage until every summoned mob is dead.
//   phase 2 (50% HP): roars, his armour ignites, and he adds
//   stomp   - hits everything within ~3 blocks around him; the ground heaves up and settles
//   dash    - a rare lunge at a distant player

const $Attributes = Java.loadClass('net.minecraft.world.entity.ai.attributes.Attributes')
const $Player = Java.loadClass('net.minecraft.world.entity.player.Player')
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

// action lengths and hit frames in ticks (20 per second), matched to the animations
const WS_LEN = { sweep: 56, push: 40, summon_start: 44, summon_end: 36, awaken: 72, stomp: 40, dash: 32 }   // ticks, matching the animations

StartupEvents.registry('entity_type', event => {
  let b = event.create(WS, 'entityjs:mob')
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
    .modelResource(e => `kubejs:geo/entity/${WS}.geo.json`)
    .animationResource(e => `kubejs:animations/entity/${WS}.animation.json`)
    .textureResource(e => wsPhase2(e) ? WS_TEX(`${WS}_awakened`) : WS_TEX(WS))
    .newGlowingGeoLayer(layer => layer.textureResource(e => wsPhase2(e) ? WS_TEX(`${WS}_awakened_glowmask`) : WS_TEX(`${WS}_glowmask`)))
    .attributes(a => {
      a.add($Attributes.MAX_HEALTH, 600)
      a.add($Attributes.ARMOR, 14)
      a.add($Attributes.ARMOR_TOUGHNESS, 6)
      a.add($Attributes.KNOCKBACK_RESISTANCE, 1.0)
      a.add($Attributes.MOVEMENT_SPEED, 0.20)   // walk cycle is animated for this speed (feet stay planted)
      a.add($Attributes.FOLLOW_RANGE, 48)
      a.add($Attributes.ATTACK_DAMAGE, 14)
    })
    // one controller for everything: idle / combat stance / walk / death from the predicate, and every attack
    // as a triggerable animation on the same controller, so an attack fully takes over while it plays
    .addAnimationController('base', 6, ev => {
      // the predicate must return true/false; the then*() calls pick the animation
      try {
        WS_ACTIONS.forEach(n => ev.addTriggerableAnimation(WS_ANIM(n), n, WS_LOOPS[n] || 'PLAY_ONCE'))
        let e = ev.entity
        if (e.isDeadOrDying()) ev.thenPlayAndHold(WS_ANIM('death'))
        else if (ev.isMoving()) ev.thenLoop(WS_ANIM('walk'))
        else if (e.isAggressive()) ev.thenLoop(WS_ANIM('idle_combat'))
        else ev.thenLoop(WS_ANIM('idle'))
      } catch (err) {}
      return true
    })
    .isInvulnerableTo(ctx => {
      let d = ctx.entity.persistentData
      return d.getBoolean('ws_guarded')
    })
    .tick(e => {
      if (e.level.isClientSide()) return
      try { global.wsTick(e) } catch (err) { wsLogOnce('tick', err) }
    })
    // he plays his own 4-second death animation instead of tipping over, then crumbles away
    .tickDeath(e => {
      if (e.level.isClientSide()) return
      try {
        let d = e.persistentData, n = d.getInt('ws_dying') + 1
        d.putInt('ws_dying', n)
        if (n >= 90) { e.level.broadcastEntityEvent(e, 60); e.discard() }   // death animation is 3.8s, then a beat
      } catch (err) { wsLogOnce('death', err); e.discard() }
    })
    .onDeath(ctx => { if (!ctx.entity.level.isClientSide()) try { global.wsOnDeath(ctx.entity) } catch (err) { wsLogOnce('onDeath', err) } })
    .onRemovedFromWorld(e => { if (!e.level.isClientSide()) try { global.wsClearBar(e) } catch (err) { wsLogOnce('removed', err) } })
    .setHurtSound(ctx => 'minecraft:entity.skeleton.hurt')
    .setDeathSound('minecraft:entity.wither_skeleton.death')
    .setSoundVolume(2.0)
})

// his AI goals (targeting players, looking around) are in server_scripts/bosses/withered_sentinel_goals.js;
// EntityJS only accepts goal events from server scripts

// ------------------------------------------------------------------ server-side fight logic
global.wsBars = global.wsBars || {}

function wsPhase2(e) { try { return e.getHealth() <= e.getMaxHealth() * 0.5 } catch (err) { return false } }

// a short id saved on the boss, used to tag his summons and find his boss bar
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
// Rhino in this pack can't read entity.x/.y/.z (getX has two overloads and the wrong one wins),
// so positions are read through position() and checked before use.
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
function wsFace(e, t) {
  let p = wsP(e), q = wsP(t)
  if (p.bad || q.bad) return
  let yaw = Math.atan2(q.z - p.z, q.x - p.x) * 180 / Math.PI - 90
  if (!isFinite(yaw)) return
  e.setYRot(yaw); e.setYHeadRot(yaw); e.setYBodyRot(yaw)
}
function wsFwd(e) { let r = wsNum(e.getYRot()) * Math.PI / 180; if (!isFinite(r)) r = 0; return [-Math.sin(r), Math.cos(r)] }
function wsNear(e, r) {
  let p = wsP(e)
  let box = new $AABB(p.x - r, p.y - 3, p.z - r, p.x + r, p.y + 10, p.z + r)
  return e.level.getEntities(e, box)
}
function wsCmd(e, c) { let p = wsP(e); e.server.runCommandSilent(`execute in ${e.level.dimension} positioned ${p.x} ${p.y} ${p.z} run ${c}`) }
function wsIsMinion(e, x) { try { return x.getTags().contains('wsm_' + wsId(e)) } catch (err) { return false } }

// hit every living thing (not his own minions) in range; arc = cosine of half-angle in front (-1 = all round)
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
    x.attack(e.damageSources().mobAttack(e), dmg)
    x.setDeltaMovement(new $Vec3(nx * push, lift, nz * push))
    x.hurtMarked = true
    hit++
  })
  return hit
}

global.wsSeen = global.wsSeen || {}
function wsNote(key, msg) { if (global.wsSeen[key]) return; global.wsSeen[key] = true; console.info(`[Withered Sentinel] ${msg}`) }
function wsTrigger(e, action) {
  try { e.triggerAnimation('base', action) } catch (err) {
    try { e.triggerAnim('base', action) } catch (err2) { wsLogOnce('trigger', err2) }
  }
}
function wsWalkTo(e, target) {
  try { if (e.getNavigation().moveTo(target, 1.0)) return } catch (err) { wsLogOnce('moveTo entity', err) }
  try { let q = wsP(target); if (!q.bad) e.getNavigation().moveTo(q.x, q.y, q.z, 1.0) } catch (err) { wsLogOnce('moveTo position', err) }
}
function wsStart(e, action) {
  wsNote('act_' + action, `first ${action}`)
  let d = e.persistentData
  d.putString('ws_act', action); d.putInt('ws_t', 0)
  e.getNavigation().stop()
  wsTrigger(e, action)
}

function wsStopAll(e) { WS_ACTIONS.forEach(n => { try { e.stopTriggeredAnimation('base', n) } catch (err) {} }) }

function wsBar(e) {
  let id = wsId(e), bar = global.wsBars[id]
  if (!bar) {
    bar = new $BossEvent(Text.of('The Withered Sentinel').darkAqua(), $BarColor.BLUE, $BarOverlay.NOTCHED_10)
    global.wsBars[id] = bar
  }
  bar.setProgress(Math.max(0, Math.min(1, e.getHealth() / e.getMaxHealth())))
  if (e.persistentData.getBoolean('ws_p2')) bar.setColor($BarColor.PURPLE)
  e.server.players.forEach(p => {
    let near = p.level == e.level && wsDist(p, e) < 48
    if (near) bar.addPlayer(p); else bar.removePlayer(p)
  })
}
global.wsClearBar = e => { let id = wsId(e); if (global.wsBars[id]) { global.wsBars[id].removeAllPlayers(); delete global.wsBars[id] } }

global.wsOnDeath = e => {
  wsStopAll(e)
  wsCmd(e, `kill @e[tag=wsm_${wsId(e)}]`)
  wsCmd(e, `playsound minecraft:entity.wither.death hostile @a ~ ~ ~ 3 0.6`)
}

// the ground heaves in a ring around him and settles again
function wsQuake(e) {
  let tag = `wsq_${wsId(e)}_${e.tickCount}`, pe = wsP(e), cx = Math.floor(pe.x), cz = Math.floor(pe.z), y = Math.floor(pe.y) - 1
  for (let dx = -5; dx <= 5; dx++) for (let dz = -5; dz <= 5; dz++) {
    let r = Math.sqrt(dx * dx + dz * dz)
    if (r < 1.5 || r > 4.8) continue
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

function wsMinionsAlive(e) {
  let n = 0
  wsNear(e, 64).forEach(x => { if (x.isAlive() && wsIsMinion(e, x)) n++ })
  return n
}

global.wsTick = e => {
  let d = e.persistentData
  if (!d.contains('ws_home')) {
    d.putBoolean('ws_home', true)
    try { console.info(`[Withered Sentinel] awake at ${JSON.stringify(wsP(e))}`) } catch (err) {}
    d.putInt('cd_sweep', 20); d.putInt('cd_push', 120); d.putInt('cd_summon', 300); d.putInt('cd_stomp', 60); d.putInt('cd_dash', 160)
  }
  if (e.tickCount % 5 == 0) wsBar(e)
  ;['cd_sweep', 'cd_push', 'cd_summon', 'cd_stomp', 'cd_dash'].forEach(k => { if (d.getInt(k) > 0) d.putInt(k, d.getInt(k) - 1) })

  let target = e.getTarget()
  if (target) { try { wsNote('target_' + wsId(e), `locked on to ${target.getType()}`) } catch (err) {} }
  e.setAggressive(!!target)
  let act = d.getString('ws_act'), t = d.getInt('ws_t')
  let p2 = e.getHealth() <= e.getMaxHealth() * 0.5

  // ---------------------------------------------------------- running action
  if (act != '') {
    d.putInt('ws_t', t + 1)
    if (act == 'sweep') {
      if (t < 24 && target) wsFace(e, target)
      if (t == 23) wsCmd(e, 'playsound minecraft:entity.player.attack.sweep hostile @a ~ ~ ~ 3 0.4')
      if (t == 26) {
        let f = wsFwd(e)
        wsCmd(e, `particle minecraft:sweep_attack ~${f[0] * 3} ~2.5 ~${f[1] * 3} 2 0.4 2 0 12 force`)
        wsHit(e, 5.2, -0.2, 16, 1.6, 0.35)
      }
    } else if (act == 'push') {
      if (t < 18 && target) wsFace(e, target)
      if (t == 20) {
        let f = wsFwd(e)
        for (let i = 1; i <= 4; i++) wsCmd(e, `particle minecraft:sonic_boom ~${f[0] * i * 1.6} ~5 ~${f[1] * i * 1.6} 0 0 0 0 1 force`)
        wsCmd(e, 'playsound minecraft:entity.warden.sonic_boom hostile @a ~ ~ ~ 3 0.7')
        wsHit(e, 9, 0.5, 6, 2.6, 0.55)
      }
    } else if (act == 'summon_start') {
      if (t == 2) wsCmd(e, 'playsound minecraft:entity.evoker.prepare_summon hostile @a ~ ~ ~ 3 0.6')
      if (t == 36) {      // the blade hits the ground
        wsCmd(e, 'playsound minecraft:entity.generic.explode hostile @a ~ ~ ~ 2 0.5')
        wsCmd(e, 'particle minecraft:soul_fire_flame ~ ~0.5 ~ 3 0.2 3 0.05 120 force')
        let tag = 'wsm_' + wsId(e), mobs = ['minecraft:wither_skeleton', 'minecraft:wither_skeleton', 'minecraft:skeleton']
        if (p2) mobs.push('minecraft:wither_skeleton')
        let pe = wsP(e)
        mobs.forEach((m, i) => {
          let a = (i / mobs.length) * Math.PI * 2, x = pe.x + Math.cos(a) * 5, z = pe.z + Math.sin(a) * 5
          e.server.runCommandSilent(`execute in ${e.level.dimension} run summon ${m} ${x} ${pe.y} ${z} {Tags:["${tag}","ws_minion"],PersistenceRequired:1b}`)
          e.server.runCommandSilent(`execute in ${e.level.dimension} run particle minecraft:soul ${x} ${pe.y + 1} ${z} 0.4 0.8 0.4 0.02 30 force`)
        })
        d.putBoolean('ws_guarded', true)
      }
      if (t >= WS_LEN.summon_start) { d.putString('ws_act', 'summon_hold'); d.putInt('ws_t', 0); wsTrigger(e, 'summon_loop') }
    } else if (act == 'summon_hold') {
      if (t % 20 == 0) wsCmd(e, 'particle minecraft:soul ~ ~0.5 ~ 1.5 0.2 1.5 0.01 8 force')
      if (t % 10 == 0 && wsMinionsAlive(e) == 0) {
        d.putBoolean('ws_guarded', false)
        wsStart(e, 'summon_end')
        d.putInt('cd_summon', 900)
      }
    } else if (act == 'awaken') {
      if (t == 2) wsCmd(e, 'playsound minecraft:entity.wither_skeleton.death hostile @a ~ ~ ~ 3 0.4')
      if (t == 40) wsCmd(e, 'playsound minecraft:entity.warden.roar hostile @a ~ ~ ~ 4 0.6')
      if (t == 44) {      // rears up: the armour ignites
        wsCmd(e, 'playsound minecraft:entity.wither.spawn hostile @a ~ ~ ~ 3 0.8')
        wsCmd(e, 'particle minecraft:soul_fire_flame ~ ~4 ~ 1.5 3 1.5 0.08 200 force')
        wsHit(e, 6, -1, 0, 1.8, 0.4)
      }
      if (t >= WS_LEN.awaken) d.putBoolean('ws_guarded', false)
    } else if (act == 'stomp') {
      if (t == 19) {
        wsCmd(e, 'playsound minecraft:entity.generic.explode hostile @a ~ ~ ~ 3 0.6')
        wsCmd(e, 'particle minecraft:explosion ~ ~0.5 ~ 2.5 0.2 2.5 0 8 force')
        wsQuake(e)
        wsHit(e, 4.5, -1, 14, 0.9, 0.9)
      }
    } else if (act == 'dash') {
      if (t < 8 && target) wsFace(e, target)
      if (t == 8) wsCmd(e, 'playsound minecraft:entity.ravager.roar hostile @a ~ ~ ~ 3 0.7')
      if (t >= 9 && t <= 16) {
        let f = wsFwd(e)
        let vy = 0; try { let v = wsVec(e.getDeltaMovement()); if (v) vy = v.y } catch (err) {}
        if (t == 9) vy = 0.32      // he leaps: airborne for the lunge, lands with the animation (~t17)
        e.setDeltaMovement(new $Vec3(f[0] * 1.35, vy, f[1] * 1.35))
        e.hurtMarked = true
        if (!d.getBoolean('ws_dash_hit') && wsHit(e, 3.0, 0.2, 18, 1.4, 0.4) > 0) d.putBoolean('ws_dash_hit', true)
      }
      if (t == 17) {             // plants his feet on landing instead of skating on
        let f = wsFwd(e), vy = 0; try { let v = wsVec(e.getDeltaMovement()); if (v) vy = v.y } catch (err) {}
        e.setDeltaMovement(new $Vec3(f[0] * 0.12, vy, f[1] * 0.12)); e.hurtMarked = true
        wsCmd(e, 'playsound minecraft:entity.iron_golem.damage hostile @a ~ ~ ~ 3 0.5')
        wsCmd(e, 'particle minecraft:campfire_cosy_smoke ~ ~0.2 ~ 1.5 0.1 1.5 0.01 20 force')
      }
    }
    let len = WS_LEN[act]
    if (len && t >= len && act != 'summon_start') { d.putString('ws_act', ''); d.putBoolean('ws_dash_hit', false) }
    return
  }

  // ---------------------------------------------------------- choosing the next move
  if (p2 && !d.getBoolean('ws_p2')) {
    d.putBoolean('ws_p2', true); d.putBoolean('ws_guarded', true)
    wsStopAll(e); wsStart(e, 'awaken'); return
  }
  if (!target || !target.isAlive()) { e.getNavigation().stop(); return }
  let dist = wsDist(e, target)
  let r = Math.random()

  if (d.getInt('cd_summon') == 0 && e.getHealth() < e.getMaxHealth() * 0.8 && dist < 24) { wsStart(e, 'summon_start'); return }
  if (p2 && d.getInt('cd_stomp') == 0 && dist < 5) { wsStart(e, 'stomp'); d.putInt('cd_stomp', 160); return }
  if (p2 && d.getInt('cd_dash') == 0 && dist > 7 && dist < 18 && r < 0.04) { wsStart(e, 'dash'); d.putInt('cd_dash', 300); return }
  if (d.getInt('cd_push') == 0 && dist < 6 && r < 0.35) { wsStart(e, 'push'); d.putInt('cd_push', 200); return }
  if (d.getInt('cd_sweep') == 0 && dist < 5.6) { wsStart(e, 'sweep'); d.putInt('cd_sweep', 50); return }

  if (dist > 4.2) wsWalkTo(e, target)
  else { e.getNavigation().stop(); wsFace(e, target) }
}
