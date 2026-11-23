// The pack's own sounds (files in kubejs/assets/kubejs/sounds/, listed in kubejs/assets/kubejs/sounds.json)
StartupEvents.registry('sound_event', event => {
  event.create('title_dawn_of_adventure')   // welcome title card
  event.create('letter_secret_found')       // a torn page / letter recovered
})
