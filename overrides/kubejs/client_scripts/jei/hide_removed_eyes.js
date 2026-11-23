// The Cursed, Cryptic, Wither and Corrupted Eyes aren't part of Adventures of Fairytale.
JEIEvents.hideItems(event => {
  ;['endrem:cursed_eye', 'endrem:cryptic_eye', 'endrem:wither_eye', 'endrem:corrupted_eye'].forEach(id => event.hide(id))
})
