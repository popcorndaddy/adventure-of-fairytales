// The Gate Knight: an ancient dark knight boss (GeckoLib model + animations, EntityJS entity).
// This file only registers the entity, its model/animations and the hooks; his fighting brain lives in
// server_scripts/fighters/gate_knight_ai.js (so it can be tuned with /reload).

const GK_SLOT_CHEST = Java.loadClass('net.minecraft.world.entity.EquipmentSlot').CHEST

StartupEvents.registry('entity_type', event => {
  event.create('gate_knight', 'entityjs:mob')
    .sized(2.6, 8.4)
    .modelResource(e => 'kubejs:geo/entity/gate_knight.geo.json')
    .textureResource(e => 'kubejs:textures/entity/gate_knight.png')
    .animationResource(e => 'kubejs:animations/entity/gate_knight.animation.json')
    // the purple trim, runes and visor burn in the dark; brighter once he has roared
    .newGlowingGeoLayer(layer => layer.textureResource(e => {
      try { if (!e.getItemBySlot(GK_SLOT_CHEST).isEmpty()) return 'kubejs:textures/entity/gate_knight_glowmask_enraged.png' } catch (err) {}
      return 'kubejs:textures/entity/gate_knight_glowmask.png'
    }))
    .mobCategory('monster')
    .isPersistenceRequired(true)
    .canBeLeashed(ctx => false)
    .isPushable(false)
    .fireImmune(true)
    .canBreatheUnderwater(true)
    .setSoundVolume(2.0)
    .setDeathSound('minecraft:entity.wither.death')
    .setHurtSound(ctx => 'minecraft:entity.iron_golem.hurt')
    .experienceReward(e => 500)
    .defaultDeathPose(false)
    .calculateFallDamage(ctx => 0)
    .canBeAffected(ctx => {
      // heavily magic immune: no harmful potion or spell effects take hold
      try { return ctx.effect.getEffect().isBeneficial() } catch (err) { return false }
    })
    .tickDeath(e => { if (global.gkTickDeath) global.gkTickDeath(e) })
    .tick(e => { if (!e.level.isClientSide() && global.gkTick) global.gkTick(e) })
    .onAddedToWorld(e => { if (!e.level.isClientSide() && global.gkAdded) global.gkAdded(e) })
    .onRemovedFromWorld(e => { if (!e.level.isClientSide() && global.gkRemoved) global.gkRemoved(e) })
    .onDeath(ctx => { if (global.gkDied) global.gkDied(ctx.entity, ctx.damageSource) })
    // walking / idling
    .addAnimationController('base', 6, e => {
      if (e.isMoving()) e.thenLoop('walk'); else e.thenLoop('idle')
      return true
    })
    // attacks and phase moves, started from the server with triggerAnim('action', <name>)
    .addAnimationController('action', 4, e => {
      e.addTriggerableAnimation('sweep', 'sweep', 'PLAY_ONCE')
      e.addTriggerableAnimation('stomp', 'stomp', 'PLAY_ONCE')
      e.addTriggerableAnimation('dash', 'dash', 'PLAY_ONCE')
      e.addTriggerableAnimation('shockwave', 'shockwave', 'PLAY_ONCE')
      e.addTriggerableAnimation('block', 'block', 'PLAY_ONCE')
      e.addTriggerableAnimation('kneel', 'kneel', 'HOLD_ON_LAST_FRAME')
      e.addTriggerableAnimation('roar', 'roar', 'PLAY_ONCE')
      e.addTriggerableAnimation('death', 'death', 'HOLD_ON_LAST_FRAME')
      return false
    })
    .eggItem(egg => egg.backgroundColor(0x141018).highlightColor(0xA040FF))
})

EntityJSEvents.editAttributes(event => {
  event.modify('kubejs:gate_knight', attr => {
    attr.add('minecraft:generic.max_health', 600)
    attr.add('minecraft:generic.movement_speed', 0.27)      // a little quicker than a walking player
    attr.add('minecraft:generic.attack_damage', 14)
    attr.add('minecraft:generic.armor', 14)
    attr.add('minecraft:generic.armor_toughness', 8)
    attr.add('minecraft:generic.knockback_resistance', 1.0)
    attr.add('minecraft:generic.follow_range', 48)
  })
})

// Damage handling is done here (startup) because only Forge's events can change the amount; the logic is in the server script.
ForgeEvents.onEvent('net.minecraftforge.event.entity.living.LivingAttackEvent', event => {
  try { if (global.gkOnAttack) global.gkOnAttack(event) } catch (e) {}
})
ForgeEvents.onEvent('net.minecraftforge.event.entity.living.LivingHurtEvent', event => {
  try { if (global.gkOnHurt) global.gkOnHurt(event) } catch (e) {}
})
