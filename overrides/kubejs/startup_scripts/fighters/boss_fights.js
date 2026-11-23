// Boss fights in co-op. Counts a player as fighting a boss the moment they swing at it or shoot it, even when the boss
// blocks or is immune for now (the Ferrous Wroughtnaut shrugs off hits to its front, which never
// reach a normal damage event). The loot-sharing rules live in server_scripts/story/boss_route_pages_and_loot.js;
// this only reports the attack to it.

function ftFightTarget(entity) {
  // multipart bosses (the Ender Dragon) are hit through their parts
  try { if (entity.getParent && entity.getParent()) return entity.getParent() } catch (e) {}
  return entity
}

ForgeEvents.onEvent('net.minecraftforge.event.entity.player.AttackEntityEvent', event => {
  try {
    let player = event.getEntity()
    if (player.level.isClientSide()) return
    if (global.fairytaleMarkFighter) global.fairytaleMarkFighter(ftFightTarget(event.getTarget()), player)
  } catch (e) {}
})

ForgeEvents.onEvent('net.minecraftforge.event.entity.ProjectileImpactEvent', event => {
  try {
    let projectile = event.getProjectile()
    if (projectile.level.isClientSide()) return
    let hit = event.getRayTraceResult()
    if (!hit || !hit.getEntity) return
    let owner = projectile.getOwner()
    if (!owner || !owner.isPlayer()) return
    if (global.fairytaleMarkFighter) global.fairytaleMarkFighter(ftFightTarget(hit.getEntity()), owner)
  } catch (e) {}
})

// A boss's experience is split evenly between everyone who fought it (2 or more), straight into
// each of them, instead of a pile of orbs for whoever grabs them first.
ForgeEvents.onEvent('net.minecraftforge.event.entity.living.LivingExperienceDropEvent', event => {
  try {
    let boss = event.getEntity()
    if (boss.level.isClientSide()) return
    if (!global.fairytaleIsMajor || !global.fairytaleFighters || !global.fairytaleIsMajor(boss)) return
    let fought = global.fairytaleFighters(boss)
    if (fought.length < 2) return
    let xp = event.getDroppedExperience()
    if (xp <= 0) return
    event.setDroppedExperience(0)
    let each = Math.ceil(xp / fought.length)
    fought.forEach(p => p.giveExperiencePoints(each))
  } catch (e) {}
})
