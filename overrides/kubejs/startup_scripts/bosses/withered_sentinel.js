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

const WS = 'withered_sentinel'
const WS_ANIM = n => `animation.${WS}.${n}`
const WS_TEX = n => `kubejs:textures/entity/${n}.png`
const WS_ACTIONS = ['sweep', 'push', 'summon_start', 'summon_loop', 'summon_end', 'awaken', 'stomp', 'dash']
const WS_LOOPS = { summon_start: 'HOLD_ON_LAST_FRAME', summon_loop: 'LOOP' }

// action lengths and hit frames in ticks (20 per second), matched to the animations
const WS_LEN = { sweep: 56, push: 40, summon_start: 32, summon_end: 28, awaken: 68, stomp: 38, dash: 32 }

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
    .textureResource(e => e.getHealth() <= e.getMaxHealth() * 0.5 ? WS_TEX(`${WS}_awakened`) : WS_TEX(WS))
    .newGlowingGeoLayer(layer => layer.textureResource(e => e.getHealth() <= e.getMaxHealth() * 0.5
      ? WS_TEX(`${WS}_awakened_glowmask`) : WS_TEX(`${WS}_glowmask`)))
    .attributes(a => {
      a.add($Attributes.MAX_HEALTH, 600)
      a.add($Attributes.ARMOR, 14)
      a.add($Attributes.ARMOR_TOUGHNESS, 6)
      a.add($Attributes.KNOCKBACK_RESISTANCE, 1.0)
      a.add($Attributes.MOVEMENT_SPEED, 0.23)
      a.add($Attributes.FOLLOW_RANGE, 48)
      a.add($Attributes.ATTACK_DAMAGE, 14)
    })
    // base layer: idle / combat stance / walk / death
    .addAnimationController('base', 6, ev => {
      let e = ev.entity
      if (e.isDeadOrDying()) return ev.thenPlayAndHold(WS_ANIM('death'))
      if (ev.isMoving()) return ev.thenLoop(WS_ANIM('walk'))
      if (e.isAggressive()) return ev.thenLoop(WS_ANIM('idle_combat'))
      return ev.thenLoop(WS_ANIM('idle'))
    })
    .isInvulnerableTo(ctx => {
      let d = ctx.entity.persistentData
      return d.getBoolean('ws_guarded')
    })
    .tick(e => { if (!e.level.isClientSide()) global.wsTick(e) })
    .tickDeath(e => {
      e.deathTime++
      if (e.deathTime >= 80 && !e.level.isClientSide()) {
        e.level.broadcastEntityEvent(e, 60)
        e.discard()
      }
    })
    .onDeath(ctx => { if (!ctx.entity.level.isClientSide()) global.wsOnDeath(ctx.entity) })
    .onRemovedFromWorld(e => { if (!e.level.isClientSide()) global.wsClearBar(e) })
    .setHurtSound(ctx => 'minecraft:entity.skeleton.hurt')
    .setDeathSound('minecraft:entity.wither_skeleton.death')
    .setSoundVolume(2.0)
  // one-shot actions layered over the base, started from the server with triggerAnim
  WS_ACTIONS.forEach(n => b.addTriggerableAnimationController(`c_${n}`, n === 'summon_loop' ? 0 : 4, n, WS_ANIM(n), WS_LOOPS[n] || 'PLAY_ONCE'))
})

// his AI goals (targeting players, looking around) are in server_scripts/bosses/withered_sentinel_goals.js;
// EntityJS only accepts goal events from server scripts

// ------------------------------------------------------------------ server-side fight logic
global.wsBars = global.wsBars || {}

function wsId(e) { return String(e.getStringUUID()).substring(0, 8) }
function wsDist(a, b) { let dx = a.x - b.x, dz = a.z - b.z; return Math.sqrt(dx * dx + dz * dz) }
function wsFace(e, t) {
  let yaw = Math.atan2(t.z - e.z, t.x - e.x) * 180 / Math.PI - 90
  e.setYRot(yaw); e.setYHeadRot(yaw); e.setYBodyRot(yaw)
}
function wsFwd(e) { let r = e.getYRot() * Math.PI / 180; return [-Math.sin(r), Math.cos(r)] }
function wsNear(e, r) {
  let box = new $AABB(e.x - r, e.y - 3, e.z - r, e.x + r, e.y + 10, e.z + r)
  return e.level.getEntities(e, box)
}
function wsCmd(e, c) { e.server.runCommandSilent(`execute in ${e.level.dimension} positioned ${e.x} ${e.y} ${e.z} run ${c}`) }
function wsIsMinion(e, x) { try { return x.getTags().contains('wsm_' + wsId(e)) } catch (err) { return false } }

// hit every living thing (not his own minions) in range; arc = cosine of half-angle in front (-1 = all round)
function wsHit(e, range, arc, dmg, push, lift) {
  let f = wsFwd(e), hit = 0
  wsNear(e, range + 2).forEach(x => {
    if (!x.isLiving() || !x.isAlive() || wsIsMinion(e, x)) return
    if (x.isPlayer() && (x.isCreative() || x.isSpectator())) return
    let dx = x.x - e.x, dz = x.z - e.z, d = Math.sqrt(dx * dx + dz * dz)
    if (d > range + x.getBbWidth() / 2) return
    let nx = d > 0.01 ? dx / d : f[0], nz = d > 0.01 ? dz / d : f[1]
    if (arc > -1 && nx * f[0] + nz * f[1] < arc) return
    x.attack(e.damageSources().mobAttack(e), dmg)
    x.setDeltaMovement(nx * push, lift, nz * push)
    x.hurtMarked = true
    hit++
  })
  return hit
}

function wsStart(e, action) {
  let d = e.persistentData
  d.putString('ws_act', action); d.putInt('ws_t', 0)
  e.getNavigation().stop()
  e.triggerAnim(`c_${action}`, action)
}

function wsStopAll(e) { WS_ACTIONS.forEach(n => { try { e.stopTriggeredAnimation(`c_${n}`, n) } catch (err) {} }) }

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
  let tag = `wsq_${wsId(e)}_${e.tickCount}`, cx = Math.floor(e.x), cz = Math.floor(e.z), y = Math.floor(e.y) - 1
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
    d.putInt('cd_sweep', 20); d.putInt('cd_push', 120); d.putInt('cd_summon', 300); d.putInt('cd_stomp', 60); d.putInt('cd_dash', 160)
  }
  if (e.tickCount % 5 == 0) wsBar(e)
  ;['cd_sweep', 'cd_push', 'cd_summon', 'cd_stomp', 'cd_dash'].forEach(k => { if (d.getInt(k) > 0) d.putInt(k, d.getInt(k) - 1) })

  let target = e.getTarget()
  e.setAggressive(!!target)
  let act = d.getString('ws_act'), t = d.getInt('ws_t')
  let p2 = e.getHealth() <= e.getMaxHealth() * 0.5

  // ---------------------------------------------------------- running action
  if (act != '') {
    d.putInt('ws_t', t + 1)
    if (act == 'sweep') {
      if (t < 24 && target) wsFace(e, target)
      if (t == 22) wsCmd(e, 'playsound minecraft:entity.player.attack.sweep hostile @a ~ ~ ~ 3 0.4')
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
      if (t == 23) {
        wsCmd(e, 'playsound minecraft:entity.generic.explode hostile @a ~ ~ ~ 2 0.5')
        wsCmd(e, 'particle minecraft:soul_fire_flame ~ ~0.5 ~ 3 0.2 3 0.05 120 force')
        let tag = 'wsm_' + wsId(e), mobs = ['minecraft:wither_skeleton', 'minecraft:wither_skeleton', 'minecraft:skeleton']
        if (p2) mobs.push('minecraft:wither_skeleton')
        mobs.forEach((m, i) => {
          let a = (i / mobs.length) * Math.PI * 2, x = e.x + Math.cos(a) * 5, z = e.z + Math.sin(a) * 5
          e.server.runCommandSilent(`execute in ${e.level.dimension} run summon ${m} ${x} ${e.y} ${z} {Tags:["${tag}","ws_minion"],PersistenceRequired:1b}`)
          e.server.runCommandSilent(`execute in ${e.level.dimension} run particle minecraft:soul ${x} ${e.y + 1} ${z} 0.4 0.8 0.4 0.02 30 force`)
        })
        d.putBoolean('ws_guarded', true)
      }
      if (t >= WS_LEN.summon_start) { d.putString('ws_act', 'summon_hold'); d.putInt('ws_t', 0); e.triggerAnim('c_summon_loop', 'summon_loop') }
    } else if (act == 'summon_hold') {
      if (t % 20 == 0) wsCmd(e, 'particle minecraft:soul ~ ~0.5 ~ 1.5 0.2 1.5 0.01 8 force')
      if (t % 10 == 0 && wsMinionsAlive(e) == 0) {
        try { e.stopTriggeredAnimation('c_summon_loop', 'summon_loop'); e.stopTriggeredAnimation('c_summon_start', 'summon_start') } catch (err) {}
        d.putBoolean('ws_guarded', false)
        wsStart(e, 'summon_end')
        d.putInt('cd_summon', 900)
      }
    } else if (act == 'awaken') {
      if (t == 1) wsCmd(e, 'playsound minecraft:entity.warden.roar hostile @a ~ ~ ~ 4 0.6')
      if (t == 25) {
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
        e.setDeltaMovement(f[0] * 1.35, e.getDeltaMovement().y(), f[1] * 1.35)
        e.hurtMarked = true
        if (!d.getBoolean('ws_dash_hit') && wsHit(e, 3.0, 0.2, 18, 1.4, 0.4) > 0) d.putBoolean('ws_dash_hit', true)
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

  if (dist > 4.2) e.getNavigation().moveTo(target, 1.0)
  else { e.getNavigation().stop(); e.getLookControl().setLookAt(target, 30, 30) }
}
