// Essence staffs: drop Mystical Agriculture's "Not Yet Implemented" line (they work here: see
// server_scripts/recipes/essence_staffs.js) and say how many spells the staff holds.

ItemEvents.tooltip(event => {
  let staffs = global.fairytaleStaffs
  if (!staffs) return
  Object.keys(staffs).forEach(id => {
    event.addAdvanced(id, (stack, advanced, text) => {
      try {
        for (let i = text.size() - 1; i >= 0; i--) {
          let line = text.get(i)
          let s = String(line.getString()).trim().toLowerCase()
          if (s == 'not yet implemented' || s == 'tooltip.cucumber.not_yet_implemented') text.remove(line)
        }
        let n = staffs[id].slots
        text.add(1, Text.lightPurple(`Spell slots: ${n}`))
        text.add(2, Text.gray('Imbue scrolls at an Arcane Anvil'))
      } catch (e) { }
    })
  })
})
