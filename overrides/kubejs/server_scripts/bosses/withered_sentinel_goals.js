// AI goals for the Withered Sentinel (the entity itself is registered in startup_scripts/bosses/withered_sentinel.js).
// His fighting is done in that startup script's tick; these goals only pick a target and keep him looking around.

const $WsPlayer = Java.loadClass('net.minecraft.world.entity.player.Player')

EntityJSEvents.addGoalSelectors('kubejs:withered_sentinel', e => {
  e.floatSwim(0)
  e.lookAtEntity(8, $WsPlayer, 24, 1.0, false)
  e.randomLookAround(9)
})

EntityJSEvents.addGoalTargets('kubejs:withered_sentinel', e => {
  e.hurtByTarget(1, [], false, [])
  e.nearestAttackableTarget(2, $WsPlayer, 10, true, false, p => !p.isCreative() && !p.isSpectator())
})
