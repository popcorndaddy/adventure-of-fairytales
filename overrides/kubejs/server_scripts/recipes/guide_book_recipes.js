// Recipes the Adventure Book's "Further Reading" pages show for guide books whose own recipe
// can't be looked up from the mod's source. Both are extra recipes; the mods' own ones still work.
ServerEvents.recipes(event => {
  // Tide: a book and any fish (the recipe Tide documents)
  event.shapeless('tide:fishing_journal', ['minecraft:book', '#minecraft:fishes'])
    .id('kubejs:guide_books/fishing_journal')
  // Hexerei: a book and a mandrake root
  event.shapeless('hexerei:book_of_shadows', ['minecraft:book', 'hexerei:mandrake_root'])
    .id('kubejs:guide_books/book_of_shadows')
})
