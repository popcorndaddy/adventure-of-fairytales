// Load-order fix: stops a random startup crash in The Aether: Redux.
//
// Redux adds one entry ("data_condition") to Minecraft's placement-modifier list during
// common setup, which runs on several threads at once. If another mod writes to the same
// kind of list at that exact moment, the list gets corrupted and the game crashes with
// "ArrayIndexOutOfBoundsException ... ReduxPlacementModifiers".
//
// Here the same entry is registered a little earlier, during Forge's registry step, which
// runs on one thread. When Redux's own setup reaches that line later, the entry already
// exists and nothing is written, so there is nothing to collide with.
// Redux itself is unchanged: same entry, same name, same behaviour.

ForgeModEvents.onEvent('net.minecraftforge.registries.RegisterEvent', event => {
  if (String(event.getRegistryKey()).indexOf('worldgen/placement_modifier_type') < 0) return
  try {
    Java.loadClass('net.zepalesque.redux.world.placement.ReduxPlacementModifiers').init()
    console.info('[Fairytale] Aether Redux placement modifier registered early (startup crash guard)')
  } catch (e) {
    console.warn(`[Fairytale] could not pre-register the Aether Redux placement modifier: ${e}`)
  }
})
