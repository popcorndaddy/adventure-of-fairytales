// AI goals for the Withered King (the entity and his whole fight are in startup_scripts/bosses/withered_king.js).
// These only give him a target and let him look around; while he kneels, roars or dies the startup script holds his
// facing still, so these goals can't turn him.

const $WkPlayer = Java.loadClass('net.minecraft.world.entity.player.Player')

EntityJSEvents.addGoalSelectors('kubejs:withered_king', e => {
  e.floatSwim(0)
  e.lookAtEntity(8, $WkPlayer, 24, 1.0, false)
  e.randomLookAround(9)
})

// EntityJS calls the target-goal event 'addGoals'
EntityJSEvents.addGoals('kubejs:withered_king', e => {
  e.hurtByTarget(1, [], false, [])
  e.nearestAttackableTarget(2, $WkPlayer, 10, true, false, p => !p.isCreative() && !p.isSpectator())
})
