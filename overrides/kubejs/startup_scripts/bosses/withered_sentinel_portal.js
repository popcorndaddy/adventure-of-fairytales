// The Withered Sentinel guards the ways between worlds: he only ever comes into the world through a Nether portal that
// players have just lit. Two seconds after the portal forms he steps out of it, kneeling and dormant, and wakes as soon
// as a player is near (his awakening: war horns, dust shaken off ancient armour).
// Once per portal location (a portal relit in the same place is already guarded); never while one is alive nearby.
// Forge: BlockEvent.PortalSpawnEvent fires only when a portal frame is lit (not for portals generated on arrival).

const $WSBlockPos = Java.loadClass('net.minecraft.core.BlockPos')
const $WSBlocks = Java.loadClass('net.minecraft.world.level.block.Blocks')
const $WSPortalBlock = Java.loadClass('net.minecraft.world.level.block.NetherPortalBlock')
const WS_PORTAL_RADIUS = 24          // a portal within this many blocks of a guarded one counts as the same place

ForgeEvents.onEvent('net.minecraftforge.event.level.BlockEvent$PortalSpawnEvent', event => {
  try {
    let level = event.getLevel()
    if (level.isClientSide()) return
    let server = level.getServer()
    let p = event.getPos()
    let px = p.getX(), py = p.getY(), pz = p.getZ()
    let dim = String(level.dimension)
    server.scheduleInTicks(40, () => {
      try { wsPortalGuardian(server, level, dim, px, py, pz) } catch (err) { console.error('[Withered Sentinel] portal spawn failed: ' + err) }
    })
  } catch (err) { console.error('[Withered Sentinel] portal event failed: ' + err) }
})

function wsPortalGuardian(server, level, dim, px, py, pz) {
  // the portal itself: its blocks around the lit spot, its axis and its bottom-centre
  let n = 0, sx = 0, sz = 0, minY = 9999, axis = 'x'
  for (let dx = -12; dx <= 12; dx++) for (let dy = -12; dy <= 12; dy++) for (let dz = -12; dz <= 12; dz++) {
    let st = level.getBlockState(new $WSBlockPos(px + dx, py + dy, pz + dz))
    if (!st.is($WSBlocks.NETHER_PORTAL)) continue
    n++; sx += px + dx; sz += pz + dz
    if (py + dy < minY) minY = py + dy
    try { axis = String(st.getValue($WSPortalBlock.AXIS)) } catch (err) {}
  }
  if (n == 0) return                                                    // the portal did not form (or was broken already)
  let cx = sx / n + 0.5, cz = sz / n + 0.5

  // once per place; never a second guardian while one is alive here
  let data = server.persistentData
  let list = []
  try { list = JSON.parse(String(data.getString('ws_portals') || '[]')) } catch (err) { list = [] }
  for (let i = 0; i < list.length; i++) {
    let q = list[i]
    if (q.d == dim && Math.abs(q.x - cx) < WS_PORTAL_RADIUS && Math.abs(q.z - cz) < WS_PORTAL_RADIUS && Math.abs(q.y - minY) < WS_PORTAL_RADIUS) return
  }
  let alive = 0
  try { alive = server.runCommandSilent(`execute in ${dim} positioned ${cx} ${minY} ${cz} if entity @e[type=kubejs:withered_sentinel,distance=..64]`) } catch (err) {}
  if (alive > 0) return
  list.push({ d: dim, x: Math.round(cx), y: minY, z: Math.round(cz) })
  data.putString('ws_portals', JSON.stringify(list))

  // he steps out on the side the nearest player is standing, facing them
  let pl = level.getNearestPlayer(cx, minY, cz, 48, false)
  let side = 1
  let ox = axis == 'x' ? 0 : 1, oz = axis == 'x' ? 1 : 0                  // out of the portal's plane
  if (pl) { let d = (pl.getX() - cx) * ox + (pl.getZ() - cz) * oz; side = d >= 0 ? 1 : -1 }
  let gx = cx + ox * side * 3.0, gz = cz + oz * side * 3.0
  let yaw = 0
  if (pl) yaw = Math.atan2(pl.getZ() - gz, pl.getX() - gx) * 57.29577951308232 - 90
  else yaw = Math.atan2(oz * side, ox * side) * 57.29577951308232 - 90
  let at = `execute in ${dim} positioned ${cx} ${minY + 1.5} ${cz} run`
  server.runCommandSilent(`${at} particle minecraft:reverse_portal ~ ~ ~ 1.2 1.6 1.2 0.6 400 force`)
  server.runCommandSilent(`${at} particle minecraft:dust 0.32 0.04 0.55 2.0 ~ ~ ~ 1.4 1.8 1.4 0.02 160 force`)
  server.runCommandSilent(`${at} playsound minecraft:block.portal.trigger hostile @a ~ ~ ~ 4 0.5`)
  server.runCommandSilent(`${at} playsound minecraft:event.raid.horn hostile @a ~ ~ ~ 4 0.45`)
  server.scheduleInTicks(20, () => {
    server.runCommandSilent(`execute in ${dim} run summon kubejs:withered_sentinel ${gx.toFixed(2)} ${minY} ${gz.toFixed(2)} {Rotation:[${yaw.toFixed(1)}f,0f],PersistenceRequired:1b}`)
    server.runCommandSilent(`execute in ${dim} positioned ${gx.toFixed(2)} ${minY + 1} ${gz.toFixed(2)} run particle minecraft:large_smoke ~ ~ ~ 1.2 0.4 1.2 0.02 60 force`)
    server.runCommandSilent(`execute in ${dim} positioned ${gx.toFixed(2)} ${minY} ${gz.toFixed(2)} run playsound minecraft:entity.iron_golem.step hostile @a ~ ~ ~ 3 0.4`)
    console.info(`[Withered Sentinel] a guardian stepped out of the portal at ${dim} ${Math.round(cx)} ${minY} ${Math.round(cz)}`)
  })
}
