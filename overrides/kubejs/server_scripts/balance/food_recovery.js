// Adventures of Fairytale - faster food recovery for Spice of Life: Classic Edition
//
// Spice of Life counts how many of your last 15 meals were the same food (see config/solclassic-defaults.toml):
// each one costs 5% until the food is at 50%, then 10% each. On its own, a food only recovers as old meals slide
// out of those 15. Here every meal of something else also gives every other food two steps back, by dropping the
// two oldest entries of each other food from the history right after you eat.
//
// Example: 5 apples, so apples are at 75%. Eat bread: bread goes to 95%, apples go back to 85% (3 apples left).
// Meals Spice of Life doesn't track (dried kelp, golden apples, honey, chorus fruit) don't count as a different meal.
//
// Fully depleted food (100%: 15 of your last 15 meals) restores nothing: guaranteeMinimumNutrition is off in the
// config. Spice of Life rounds hunger down, so without its minimum a small food (a 1-point berry at 95%) would also
// give 0 long before 100%. The top-up below restores that minimum: any food not yet at 100% still gives 1 point.

const FT_SOL_HOLDER = Java.loadClass('com.github.leopoko.solclassic.network.FoodHistoryHolder')
const FT_SOL_SYNC = Java.loadClass('com.github.leopoko.solclassic.network.FoodHistorySync')
const FT_SOL_STEPS_BACK = 2
const FT_SOL_CFG = Java.loadClass('com.github.leopoko.solclassic.config.SolclassicConfigData')

// The multiplier Spice of Life used for the meal just eaten. It records the meal before this event fires, so
// the newest history entry is this meal: count the same food in the 15 meals before it.
// Returns null when the meal wasn't tracked (blacklisted foods are never reduced).
function ftSolMealMultiplier(player, eatenId) {
  let history = FT_SOL_HOLDER.INSTANCE.getFoodHistory(player)
  if (!history) return null
  let list = history.consumedItems
  if (list.isEmpty() || String(list.getLast().id) != eatenId) return null
  let mods = FT_SOL_CFG.shortFoodDecayModifiers
  if (!mods || mods.isEmpty()) return null
  let window = FT_SOL_CFG.maxShortFoodHistorySize
  let end = list.size() - 1
  let count = 0
  for (let i = Math.max(0, end - window); i < end; i++) if (String(list.get(i).id) == eatenId) count++
  let mult = mods.get(Math.min(count, mods.size() - 1))
  let longMod = FT_SOL_CFG.longFoodDecayModifiers
  if (longMod > 0) {
    let all = 0
    for (let i = 0; i < end; i++) if (String(list.get(i).id) == eatenId) all++
    mult = Math.min(mult, Math.max(0, 1 - all * longMod))
  }
  return mult
}

function ftSolTopUp(player, stack, eatenId) {
  if (FT_SOL_CFG.guaranteeMinimumNutrition) return
  let mult = ftSolMealMultiplier(player, eatenId)
  if (mult == null || mult <= 0.0001) return            // 100%: no hunger, as intended
  let props = null
  try { props = stack.getItem().getFoodProperties(stack, player) } catch (e) {}
  if (!props) return
  let base = props.getNutrition()
  if (base <= 0) return
  if (Math.floor(Math.fround(base * mult)) >= 1) return  // Spice of Life already gave at least 1
  player.getFoodData().eat(1, 0)
}

function ftSolRecover(player, eatenId) {
  let handler = FT_SOL_HOLDER.INSTANCE
  if (!handler) return
  let history = handler.getFoodHistory(player)
  if (!history) return
  let list = history.consumedItems
  if (list.isEmpty()) return
  // the meal just eaten must be the newest entry, otherwise Spice of Life didn't track it
  if (String(list.getLast().id) != eatenId) return

  let dropped = {}
  let kept = []
  for (let i = 0; i < list.size(); i++) {
    let stack = list.get(i)
    let id = String(stack.id)
    if (id != eatenId) {
      let n = dropped[id] || 0
      if (n < FT_SOL_STEPS_BACK) {      // oldest first, so the two oldest of each other food go
        dropped[id] = n + 1
        continue
      }
    }
    kept.push(stack)
  }
  if (kept.length == list.size()) return

  // rebuild through the history's own methods so its per-food counts stay right
  history.clear()
  kept.forEach(stack => history.add(stack))
  FT_SOL_SYNC.syncFoodHistory(player)   // tooltips show the new percentages straight away
}

ItemEvents.foodEaten(event => {
  let player = event.entity
  if (!player || !player.isPlayer()) return
  let eatenId = String(event.item.id)
  try { ftSolTopUp(player, event.item, eatenId) } catch (e) { console.warn(`[Fairytale] food top-up failed: ${e}`) }
  // a tick later, after Spice of Life has recorded the meal
  player.server.scheduleInTicks(1, () => {
    try { ftSolRecover(player, eatenId) } catch (e) { console.warn(`[Fairytale] food recovery failed: ${e}`) }
  })
})
