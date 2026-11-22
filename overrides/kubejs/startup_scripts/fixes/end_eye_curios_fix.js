// Fix: "Invalid player data" kick on joining a world (End Remastered ProMax + Curios).
//
// End Remastered ProMax stops you wearing two copies of the same eye in the "endeye"/"curio" slots. It
// does that by cancelling Curios' CurioEquipEvent, which can't be cancelled in Curios 5.14, so it throws
// an error. It also counts the slot the item is already in as a duplicate. When your saved curios load
// on join, the error throws, the player can't be loaded, and you're kicked with "Invalid player data".
// That failed load also leaves the world locked (it vanishes from the list until a restart) and makes
// the next world crash with "Multiple servers running at once".
//
// Here the mod's handler is switched off and the same rule is applied correctly: a second copy of an
// item in those slots is refused (Curios hands it back), and an item never counts against its own slot.

const $Bus = Java.loadClass('net.minecraftforge.common.MinecraftForge').EVENT_BUS
const $Result = Java.loadClass('net.minecraftforge.eventbus.api.Event$Result')
const $CuriosApi = Java.loadClass('top.theillusivec4.curios.api.CuriosApi')
const FT_EYE_SLOTS = ['endeye', 'curio']

function ftDropBrokenEyeHandler() {
  try {
    $Bus.unregister(Java.loadClass('org.example.xianziyu.end_remastered_promax.effect.EndEyeExclusiveHandler'))
  } catch (e) {}
}
ftDropBrokenEyeHandler()
// the mod registers its handler while mods load; make sure it is gone before any world starts
ForgeEvents.onEvent('net.minecraftforge.event.server.ServerAboutToStartEvent', event => ftDropBrokenEyeHandler())

ForgeEvents.onEvent('top.theillusivec4.curios.api.event.CurioEquipEvent', event => {
  try {
    let ctx = event.getSlotContext(), slot = ctx.identifier()
    if (FT_EYE_SLOTS.indexOf(String(slot)) < 0) return
    let entity = event.getEntity()
    if (!entity || !entity.isPlayer() || entity.level.isClientSide()) return
    let stack = event.getStack()
    if (stack.isEmpty()) return
    let inv = $CuriosApi.getCuriosInventory(entity).resolve().orElse(null)
    if (!inv) return
    let dupe = false
    FT_EYE_SLOTS.forEach(id => {
      let handler = inv.getStacksHandler(id).orElse(null)
      if (!handler || dupe) return
      let stacks = handler.getStacks()
      for (let i = 0; i < handler.getSlots(); i++) {
        if (id == String(slot) && i == ctx.index()) continue      // the slot it's going into (or already in)
        let other = stacks.getStackInSlot(i)
        if (!other.isEmpty() && other.getItem() == stack.getItem()) { dupe = true; break }
      }
    })
    if (dupe) event.setResult($Result.DENY)
  } catch (e) {}
})
