// The Gate Knight's fighting brain. The entity itself is registered in startup_scripts/fighters/gate_knight.js.
//
// Moves (all timed to the animations in kubejs/assets/kubejs/animations/entity/gate_knight.animation.json):
//   sweep      low cut across his front, reaches ~5 blocks
//   stomp      slams a foot down; the ground heaves up around him, everyone within 6 blocks takes ~6 damage
//   dash       charges ~10 blocks at the target behind a two-handed thrust
//   shockwave  open palm thrust; a wave throws players in front of him 5-6 blocks back
//   block      raises his sword to stop arrows and other projectiles from the front
//   at half health he kneels, invincible, while 8-10 wither skeletons rise; when they are all dead he stands,
//   roars and burns brighter (faster, harder hitting) for the rest of the fight. Heavily magic resistant.

const GK_ID = 'kubejs:gate_knight'
const GK_AABB = Java.loadClass('net.minecraft.world.phys.AABB')
const GK_Projectile = Java.loadClass('net.minecraft.world.entity.projectile.Projectile')
const GK_Player = Java.loadClass('net.minecraft.world.entity.player.Player')
const GK_LivingEntity = Java.loadClass('net.minecraft.world.entity.LivingEntity')
const GK_Monster = Java.loadClass('net.minecraft.world.entity.monster.Monster')
const GK_ServerBossEvent = Java.loadClass('net.minecraft.server.level.ServerBossEvent')
const GK_BossEvent = Java.loadClass('net.minecraft.world.BossEvent')
const GK_Component = Java.loadClass('net.minecraft.network.chat.Component')
const GK_EquipmentSlot = Java.loadClass('net.minecraft.world.entity.EquipmentSlot')
const GK_ItemStack = Java.loadClass('net.minecraft.world.item.ItemStack')
const GK_Items = Java.loadClass('net.minecraft.world.item.Items')
const GK_Attributes = Java.loadClass('net.minecraft.world.entity.ai.attributes.Attributes')
const GK_RemovalReason = Java.loadClass('net.minecraft.world.entity.Entity$RemovalReason')

const GK = {
  speed: 0.27, speedEnraged: 0.31,
  sweep: { len: 28, hit: 13, reach: 5.5, arc: 70, dmg: 16, cd: 40 },
  stomp: { len: 32, hit: 16, radius: 6, dmg: 6, cd: 140 },
  dash: { len: 26, go: 7, stop: 16, speed: 1.15, dmg: 18, cd: 160, min: 6, max: 16 },
  wave: { len: 28, hit: 11, reach: 8, arc: 55, dmg: 4, push: 0.68, cd: 200 },
  block: { len: 36, cd: 120 },
  kneel: { len: 30, minions: 9 },
  roar: { len: 52, glow: 24 },
  gap: 14,                    // breathing room between moves
  magicTaken: 0.15,           // share of magic damage that gets through
  bossRange: 48,
}
const GK_MAGIC_NS = ['irons_spellbooks', 'ars_nouveau', 'traveloptics', 'gtbcs_spell_lib', 'ice_and_fire_spellbooks', 'ars_elemental']

const gkBars = {}

function gkData(e) { return e.persistentData }
function gkUuid(e) { return String(e.getStringUUID()) }
function gkShort(e) { return gkUuid(e).substring(0, 8) }
function gkEnraged(e) { return gkData(e).getInt('gk_phase') >= 2 }
function gkFlat(a, b) { const dx = b.getX() - a.getX(), dz = b.getZ() - a.getZ(); return Math.sqrt(dx * dx + dz * dz) }
function gkYawTo(a, b) { return Math.atan2(b.getZ() - a.getZ(), b.getX() - a.getX()) * 180 / Math.PI - 90 }
function gkFace(e, yaw) { e.setYRot(yaw); e.setYBodyRot(yaw); e.setYHeadRot(yaw) }
function gkFacing(e) { const y = e.getYRot() * Math.PI / 180; return [-Math.sin(y), Math.cos(y)] }
function gkCmd(e, c) { try { e.server.runCommandSilent(c) } catch (err) {} }
function gkAt(e) { return `${e.getX().toFixed(2)} ${e.getY().toFixed(2)} ${e.getZ().toFixed(2)}` }
function gkSound(e, s, vol, pitch) { gkCmd(e, `playsound ${s} hostile @a ${gkAt(e)} ${vol || 2} ${pitch || 1}`) }

// players he may fight: alive, not creative/spectator, within reach
function gkPlayersNear(e, r) {
  let box = new GK_AABB(e.getX() - r, e.getY() - 6, e.getZ() - r, e.getX() + r, e.getY() + 12, e.getZ() + r)
  let out = []
  e.level.getEntitiesOfClass(GK_Player, box).forEach(p => {
    if (p.isAlive() && !p.isCreative() && !p.isSpectator() && e.distanceTo(p) <= r) out.push(p)
  })
  return out
}
// is `t` inside the cone in front of him?
function gkInFront(e, t, halfAngle) {
  let f = gkFacing(e); let dx = t.getX() - e.getX(), dz = t.getZ() - e.getZ(); let d = Math.sqrt(dx * dx + dz * dz)
  if (d < 1.6) return true
  return (f[0] * dx + f[1] * dz) / d >= Math.cos(halfAngle * Math.PI / 180)
}
function gkMul(e) { return gkEnraged(e) ? 1.25 : 1.0 }
function gkHit(e, t, dmg) { try { t.hurt(e.damageSources().mobAttack(e), dmg * gkMul(e)) } catch (err) {} }
function gkPush(t, dx, dz, h, up) {
  let d = Math.sqrt(dx * dx + dz * dz) || 1
  t.setDeltaMovement(dx / d * h, up, dz / d * h); t.hurtMarked = true
}

// ------------------------------------------------------------------ boss bar
function gkBar(e) {
  let id = gkUuid(e)
  if (!gkBars[id]) {
    let bar = new GK_ServerBossEvent(GK_Component.literal('The Gate Knight'), GK_BossEvent.BossBarColor.PURPLE, GK_BossEvent.BossBarOverlay.NOTCHED_10)
    bar.setDarkenScreen(true)
    gkBars[id] = bar
  }
  return gkBars[id]
}
function gkUpdateBar(e) {
  let bar = gkBar(e)
  bar.setProgress(Math.max(0, Math.min(1, e.getHealth() / e.getMaxHealth())))
  let near = gkPlayersNear(e, GK.bossRange)
  let ids = near.map(p => String(p.getStringUUID()))
  bar.getPlayers().forEach(p => { if (ids.indexOf(String(p.getStringUUID())) < 0) bar.removePlayer(p) })
  near.forEach(p => bar.addPlayer(p))
}
function gkDropBar(e) {
  let id = gkUuid(e)
  if (gkBars[id]) { gkBars[id].removeAllPlayers(); delete gkBars[id] }
}

// ------------------------------------------------------------------ actions
function gkStart(e, name, anim) {
  let d = gkData(e)
  d.putString('gk_act', name); d.putInt('gk_t', 0)
  e.getNavigation().stop()
  if (anim) e.triggerAnim('action', anim)
}
function gkCooldown(e, key, ticks) { gkData(e).putInt('gk_cd_' + key, Math.round(ticks * (gkEnraged(e) ? 0.7 : 1))) }
function gkReady(e, key) { return gkData(e).getInt('gk_cd_' + key) <= 0 }

function gkRaiseBlock(e, x, y, z, blockId, r, tag) {
  e.server.scheduleInTicks(r - 1, () => {
    gkCmd(e, `summon block_display ${x} ${y} ${z} {block_state:{Name:"${blockId}"},Tags:["${tag}","${tag}_${r}"]}`)
    gkCmd(e, `particle minecraft:block ${blockId} ${x + 0.5} ${y + 1.2} ${z + 0.5} 0.3 0.2 0.3 0.1 6 force`)
  })
}
function gkHeave(e, sel, r, up, back) {
  e.server.scheduleInTicks(r, () => gkCmd(e, `execute as ${sel} run data merge entity @s {start_interpolation:0,interpolation_duration:3,transformation:{translation:[0f,${up}f,0f],left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],scale:[1f,1f,1f]}}`))
  e.server.scheduleInTicks(r + back, () => gkCmd(e, `execute as ${sel} run data merge entity @s {start_interpolation:0,interpolation_duration:6,transformation:{translation:[0f,0f,0f],left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],scale:[1f,1f,1f]}}`))
}
function gkStompFx(e) {
  // the ground heaves up in a ring rolling outward from his foot (display blocks only - the terrain is not changed)
  let lvl = e.level, cx = Math.floor(e.getX()), cz = Math.floor(e.getZ()), y = Math.floor(e.getY())
  let tag = 'gkfx_' + gkShort(e) + '_' + Math.floor(Math.random() * 100000)
  for (let r = 2; r <= GK.stomp.radius; r++) {
    let count = Math.round(r * 4.5)
    for (let k = 0; k < count; k++) {
      let a = (k / count) * Math.PI * 2 + r * 0.37
      let x = Math.floor(cx + Math.cos(a) * r), z = Math.floor(cz + Math.sin(a) * r)
      let yy = y
      for (let s = 0; s < 3 && lvl.getBlock(x, yy - 1, z).blockState.isAir(); s++) yy--
      let b = lvl.getBlock(x, yy - 1, z)
      if (b.blockState.isAir() || !b.blockState.getFluidState().isEmpty()) continue
      gkRaiseBlock(e, x, yy - 1, z, String(b.id), r, tag)
    }
    gkHeave(e, `@e[type=block_display,tag=${tag}_${r}]`, r, (0.55 + Math.random() * 0.5).toFixed(2), 10)
  }
  e.server.scheduleInTicks(GK.stomp.radius + 20, () => gkCmd(e, `kill @e[type=block_display,tag=${tag}]`))
  gkCmd(e, `particle minecraft:explosion ${gkAt(e)} 1.5 0.2 1.5 0 6 force`)
  gkSound(e, 'minecraft:entity.generic.explode', 2.5, 0.6)
  gkSound(e, 'minecraft:entity.iron_golem.attack', 2.5, 0.5)
}

function gkRaiseMinion(e, x, y, z, tag, delay) {
  e.server.scheduleInTicks(delay, () => {
    gkCmd(e, `particle minecraft:soul_fire_flame ${x} ${y} ${z} 0.4 1 0.4 0.02 30 force`)
    gkCmd(e, `particle minecraft:large_smoke ${x} ${y} ${z} 0.4 0.6 0.4 0.02 20 force`)
    gkCmd(e, `summon minecraft:wither_skeleton ${x} ${y} ${z} {Tags:["${tag}","gk_minion"],PersistenceRequired:1b,` +
      `HandItems:[{id:"minecraft:stone_sword",Count:1b},{}],HandDropChances:[0f,0f],` +
      `ArmorItems:[{id:"minecraft:chainmail_boots",Count:1b},{id:"minecraft:chainmail_leggings",Count:1b},{id:"minecraft:iron_chestplate",Count:1b},{id:"minecraft:chainmail_helmet",Count:1b}],ArmorDropChances:[0f,0f,0f,0f]}`)
    gkSound(e, 'minecraft:entity.wither_skeleton.ambient', 1.5, 0.6)
  })
}
function gkSummonMinions(e) {
  let tag = 'gk_min_' + gkShort(e)
  let n = GK.kneel.minions
  for (let k = 0; k < n; k++) {
    let a = (k / n) * Math.PI * 2, r = 5 + Math.random() * 2.5
    gkRaiseMinion(e, (e.getX() + Math.cos(a) * r).toFixed(2), (e.getY() + 0.5).toFixed(2), (e.getZ() + Math.sin(a) * r).toFixed(2), tag, k * 4)
  }
}
function gkMinionsLeft(e) {
  let tag = 'gk_min_' + gkShort(e), r = 64
  let box = new GK_AABB(e.getX() - r, e.getY() - 32, e.getZ() - r, e.getX() + r, e.getY() + 32, e.getZ() + r)
  let n = 0
  e.level.getEntitiesOfClass(GK_Monster, box).forEach(m => { if (m.isAlive() && m.getTags().contains(tag)) n++ })
  return n
}

function gkSetGlow(e, on) {
  // the chest slot is invisible on this model; an item there tells every client to use the enraged glow texture
  e.setItemSlot(GK_EquipmentSlot.CHEST, on ? new GK_ItemStack(GK_Items.AMETHYST_SHARD) : GK_ItemStack.EMPTY)
  e.setDropChance(GK_EquipmentSlot.CHEST, 0)
}

// one tick of the current action; returns false when it has finished
function gkRunAction(e, act, t) {
  let tgt = e.getTarget()
  if (act === 'sweep') {
    if (t < 6 && tgt) gkFace(e, gkYawTo(e, tgt))
    if (t === 8) gkSound(e, 'minecraft:entity.player.attack.sweep', 2, 0.5)
    if (t === GK.sweep.hit) {
      let f = gkFacing(e)
      gkCmd(e, `particle minecraft:sweep_attack ${(e.getX() + f[0] * 3).toFixed(2)} ${(e.getY() + 1.2).toFixed(2)} ${(e.getZ() + f[1] * 3).toFixed(2)} 1.2 0.2 1.2 0 6 force`)
      gkPlayersNear(e, GK.sweep.reach + 1.3).forEach(p => {
        if (gkFlat(e, p) <= GK.sweep.reach + 1.3 && gkInFront(e, p, GK.sweep.arc) && p.getY() < e.getY() + 3.5) {
          gkHit(e, p, GK.sweep.dmg); gkPush(p, p.getX() - e.getX(), p.getZ() - e.getZ(), 0.6, 0.25)
        }
      })
    }
    return t < GK.sweep.len
  }
  if (act === 'stomp') {
    if (t === GK.stomp.hit) {
      gkStompFx(e)
      gkPlayersNear(e, GK.stomp.radius + 1.3).forEach(p => {
        if (gkFlat(e, p) <= GK.stomp.radius + 1.3 && p.getY() < e.getY() + 2.5) { gkHit(e, p, GK.stomp.dmg); gkPush(p, p.getX() - e.getX(), p.getZ() - e.getZ(), 0.25, 0.55) }
      })
    }
    return t < GK.stomp.len
  }
  if (act === 'dash') {
    let d = gkData(e)
    if (t < GK.dash.go && tgt) { gkFace(e, gkYawTo(e, tgt)); d.putFloat('gk_dyaw', e.getYRot()) }
    if (t === GK.dash.go) { gkSound(e, 'minecraft:entity.ravager.roar', 2, 1.4); d.putString('gk_dhit', '') }
    if (t >= GK.dash.go && t < GK.dash.stop) {
      gkFace(e, d.getFloat('gk_dyaw'))
      let f = gkFacing(e)
      e.setDeltaMovement(f[0] * GK.dash.speed, e.getDeltaMovement().y(), f[1] * GK.dash.speed); e.hurtMarked = true
      gkCmd(e, `particle minecraft:cloud ${gkAt(e)} 0.8 0.2 0.8 0.02 6 force`)
      let hitList = String(d.getString('gk_dhit'))
      gkPlayersNear(e, 4.5).forEach(p => {
        let id = String(p.getStringUUID())
        if (hitList.indexOf(id) < 0 && e.getBoundingBox().inflate(1.4).intersects(p.getBoundingBox())) {
          gkHit(e, p, GK.dash.dmg); gkPush(p, f[0], f[1], 1.0, 0.45); d.putString('gk_dhit', hitList + id + ';')
        }
      })
      if (e.horizontalCollision && t > GK.dash.go + 1) { d.putInt('gk_t', GK.dash.stop); e.setDeltaMovement(0, e.getDeltaMovement().y(), 0) }
    }
    if (t === GK.dash.stop) e.setDeltaMovement(0, e.getDeltaMovement().y(), 0)
    return t < GK.dash.len
  }
  if (act === 'wave') {
    if (t < 8 && tgt) gkFace(e, gkYawTo(e, tgt))
    if (t === GK.wave.hit) {
      let f = gkFacing(e)
      for (let s = 1; s <= 7; s++) gkCmd(e, `particle minecraft:sonic_boom ${(e.getX() + f[0] * s * 1.1).toFixed(2)} ${(e.getY() + 4.2).toFixed(2)} ${(e.getZ() + f[1] * s * 1.1).toFixed(2)} 0 0 0 0 1 force`)
      gkSound(e, 'minecraft:entity.warden.sonic_boom', 2, 1.3)
      gkPlayersNear(e, GK.wave.reach + 1).forEach(p => {
        if (gkInFront(e, p, GK.wave.arc)) { gkHit(e, p, GK.wave.dmg); gkPush(p, p.getX() - e.getX(), p.getZ() - e.getZ(), GK.wave.push, 0.45) }
      })
    }
    return t < GK.wave.len
  }
  if (act === 'block') {
    if (tgt) gkFace(e, gkYawTo(e, tgt))
    if (t >= gkData(e).getInt('gk_blen')) return false     // the block animation lowers the sword by itself after 2 s
    return true
  }
  if (act === 'kneel') {
    if (t === GK.kneel.len) {
      gkData(e).putInt('gk_phase', 1)
      gkSummonMinions(e)
      gkSound(e, 'minecraft:entity.wither.spawn', 2, 0.7)
    }
    if (t > GK.kneel.len + 40 && t % 10 === 0 && gkMinionsLeft(e) === 0) {
      gkStart(e, 'roar', 'roar'); return true
    }
    if (t % 6 === 0) gkCmd(e, `particle minecraft:enchant ${gkAt(e)} 1.4 3 1.4 0.4 12 force`)
    return true
  }
  if (act === 'roar') {
    if (t === 10) gkSound(e, 'minecraft:entity.ender_dragon.growl', 3, 0.6)
    if (t === GK.roar.glow) {
      gkData(e).putInt('gk_phase', 2); gkSetGlow(e, true)
      e.getAttribute(GK_Attributes.MOVEMENT_SPEED).setBaseValue(GK.speedEnraged)
      gkCmd(e, `particle minecraft:dragon_breath ${gkAt(e)} 2 4 2 0.05 120 force`)
      gkCmd(e, `particle minecraft:flash ${(e.getX()).toFixed(2)} ${(e.getY() + 5).toFixed(2)} ${(e.getZ()).toFixed(2)} 0 0 0 0 1 force`)
      gkPlayersNear(e, 7).forEach(p => gkPush(p, p.getX() - e.getX(), p.getZ() - e.getZ(), 0.5, 0.3))
    }
    return t < GK.roar.len
  }
  return false
}

function gkChoose(e, tgt) {
  let d = gkFlat(e, tgt), dy = Math.abs(tgt.getY() - e.getY())
  let ranged = (() => { try { let id = String(tgt.getMainHandItem().getId()); return id.indexOf('bow') >= 0 || id.indexOf('crossbow') >= 0 || id.indexOf('trident') >= 0 || id.indexOf('staff') >= 0 || id.indexOf('wand') >= 0 } catch (err) { return false } })()
  let opts = []
  if (d <= GK.sweep.reach + 0.5 && dy < 4 && gkReady(e, 'sweep')) opts.push(['sweep', 5])
  if (d <= GK.stomp.radius && gkReady(e, 'stomp') && gkPlayersNear(e, GK.stomp.radius).length > 0) opts.push(['stomp', d < 3.5 ? 5 : 3])
  if (d >= GK.dash.min && d <= GK.dash.max && dy < 4 && gkReady(e, 'dash')) opts.push(['dash', 4])
  if (d <= GK.wave.reach && gkReady(e, 'wave')) opts.push(['wave', d < 4 ? 4 : 2])
  if (ranged && d > 8 && gkReady(e, 'block')) opts.push(['block', 6])
  if (!opts.length) return null
  let sum = 0; opts.forEach(o => sum += o[1])
  let r = Math.random() * sum
  for (let i = 0; i < opts.length; i++) { r -= opts[i][1]; if (r <= 0) return opts[i][0] }
  return opts[0][0]
}

global.gkTick = e => {
  try {
    if (!e.isAlive() || e.isDeadOrDying()) return
    let d = gkData(e)
    if (e.tickCount % 5 === 0) gkUpdateBar(e)
    ;['sweep', 'stomp', 'dash', 'wave', 'block'].forEach(k => { let v = d.getInt('gk_cd_' + k); if (v > 0) d.putInt('gk_cd_' + k, v - 1) })
    if (d.getInt('gk_gap') > 0) d.putInt('gk_gap', d.getInt('gk_gap') - 1)

    // target: whoever hurt him, else the nearest player he can see
    let tgt = e.getTarget()
    if (!tgt || !tgt.isAlive() || (tgt.isCreative && (tgt.isCreative() || tgt.isSpectator())) || e.distanceTo(tgt) > GK.bossRange) {
      tgt = null
      let best = 1e9
      gkPlayersNear(e, 40).forEach(p => { let dd = e.distanceTo(p); if (dd < best && e.hasLineOfSight(p)) { best = dd; tgt = p } })
      e.setTarget(tgt)
    }

    let act = String(d.getString('gk_act'))
    if (act) {
      let t = d.getInt('gk_t')
      d.putInt('gk_t', t + 1)
      if (!gkRunAction(e, act, t)) { d.putString('gk_act', ''); d.putInt('gk_gap', GK.gap) }
      return
    }
    if (e.isPassenger()) e.stopRiding()

    // half health: kneel and call the dead to fight for him (once)
    if (d.getInt('gk_phase') === 0 && e.getHealth() <= e.getMaxHealth() * 0.5) {
      gkStart(e, 'kneel', 'kneel'); gkSound(e, 'minecraft:entity.iron_golem.damage', 2, 0.5); return
    }
    if (!tgt) { e.getNavigation().stop(); return }

    e.getLookControl().setLookAt(tgt, 30, 30)
    if (d.getInt('gk_gap') <= 0) {
      let pick = gkChoose(e, tgt)
      if (pick) {
        let L = { sweep: GK.sweep, stomp: GK.stomp, dash: GK.dash, wave: GK.wave, block: GK.block }[pick]
        gkCooldown(e, pick, L.cd)
        if (pick === 'block') d.putInt('gk_blen', GK.block.len)
        gkStart(e, pick, pick === 'wave' ? 'shockwave' : pick)
        return
      }
    }
    if (gkFlat(e, tgt) > 3.2) e.getNavigation().moveTo(tgt, 1.0)
    else e.getNavigation().stop()
  } catch (err) { console.error(`[GateKnight] tick: ${err}`) }
}

global.gkAdded = e => {
  try {
    e.setMaxUpStep(1.6)
    e.getAttribute(GK_Attributes.MOVEMENT_SPEED).setBaseValue(gkEnraged(e) ? GK.speedEnraged : GK.speed)
    // reloading mid-kneel: resume watching the minions; mid-attack: just finish clean
    let act = String(gkData(e).getString('gk_act'))
    if (act && act !== 'kneel') gkData(e).putString('gk_act', '')
    if (act === 'kneel') e.server.scheduleInTicks(5, () => { try { e.triggerAnim('action', 'kneel') } catch (err) {} })
  } catch (err) { console.error(`[GateKnight] added: ${err}`) }
}
global.gkRemoved = e => { try { gkDropBar(e) } catch (err) {} }
global.gkDied = (e, src) => {
  try {
    gkData(e).putString('gk_act', 'dead')
    e.triggerAnim('action', 'death')
    gkDropBar(e)
    gkSound(e, 'minecraft:entity.wither.death', 2, 0.6)
    let tag = 'gk_min_' + gkShort(e)
    gkCmd(e, `kill @e[tag=${tag}]`)
  } catch (err) { console.error(`[GateKnight] died: ${err}`) }
}
// death: he drops to one knee and rests his hands and head on the hilt (3.4 s), then crumbles away into dust
global.gkTickDeath = e => {
  e.deathTime++
  if (e.level.isClientSide()) return
  let t = e.deathTime
  if (t > 40 && t % 2 === 0) {
    let k = Math.min(1, (t - 40) / 30)
    gkCmd(e, `particle minecraft:white_ash ${gkAt(e)} 1.4 3 1.4 0.02 ${Math.round(20 + 60 * k)} force`)
    gkCmd(e, `particle minecraft:ash ${gkAt(e)} 1.2 2.8 1.2 0.02 ${Math.round(10 + 40 * k)} force`)
  }
  if (t === 66) gkSound(e, 'minecraft:block.sand.break', 2, 0.5)
  if (t >= 72 && !e.isRemoved()) {
    gkCmd(e, `particle minecraft:falling_dust minecraft:gravel ${gkAt(e)} 1.6 3.5 1.6 0 160 force`)
    gkCmd(e, `particle minecraft:large_smoke ${gkAt(e)} 1.4 3 1.4 0.03 60 force`)
    gkSound(e, 'minecraft:block.soul_sand.break', 2, 0.6)
    e.remove(GK_RemovalReason.KILLED)
  }
}

// incoming hits (LivingAttackEvent): invincible while kneeling; blocks projectiles from the front
global.gkOnAttack = event => {
  let e = event.getEntity()
  if (e.level.isClientSide() || String(e.getEncodeId()) !== GK_ID) return
  let src = event.getSource(), d = gkData(e)
  let killCmd = String(src.getMsgId()) === 'outOfWorld' || String(src.getMsgId()) === 'genericKill'
  if (killCmd) return
  if (d.getInt('gk_phase') === 1 || String(d.getString('gk_act')) === 'roar') {
    event.setCanceled(true)
    if (e.tickCount % 4 === 0) { gkCmd(e, `particle minecraft:enchanted_hit ${gkAt(e)} 1 3 1 0.2 16 force`); gkSound(e, 'minecraft:block.anvil.land', 0.8, 1.6) }
    return
  }
  let direct = src.getDirectEntity()
  if (direct && direct instanceof GK_Projectile) {
    let act = String(d.getString('gk_act'))
    let blocking = act === 'block'
    let free = !act && d.getInt('gk_gap') <= 0
    let fromFront = gkInFront(e, direct, 75)
    if (fromFront && (blocking || (free && Math.random() < 0.55))) {
      event.setCanceled(true)
      gkSound(e, 'minecraft:item.shield.block', 2, 0.6)
      gkCmd(e, `particle minecraft:crit ${direct.getX().toFixed(2)} ${direct.getY().toFixed(2)} ${direct.getZ().toFixed(2)} 0.2 0.2 0.2 0.3 12 force`)
      try { let v = direct.getDeltaMovement(); direct.setDeltaMovement(-v.x() * 0.25, 0.2, -v.z() * 0.25); direct.hurtMarked = true } catch (err) {}
      if (!blocking && free) { d.putInt('gk_blen', 24); gkStart(e, 'block', 'block') }
    }
  }
}
// damage that lands (LivingHurtEvent): magic barely scratches him
global.gkOnHurt = event => {
  let e = event.getEntity()
  if (e.level.isClientSide() || String(e.getEncodeId()) !== GK_ID) return
  let src = event.getSource()
  let msg = String(src.getMsgId()).toLowerCase()
  let ns = ''
  try { ns = String(src.typeHolder().unwrapKey().get().location().getNamespace()) } catch (err) {}
  if (msg.indexOf('magic') >= 0 || msg.indexOf('sonic') >= 0 || msg.indexOf('spell') >= 0 || GK_MAGIC_NS.indexOf(ns) >= 0) {
    event.setAmount(event.getAmount() * GK.magicTaken)
    if (e.tickCount % 3 === 0) gkCmd(e, `particle minecraft:witch ${gkAt(e)} 1 3 1 0.1 10 force`)
  }
}
