# Themes: a Skeleton and a Skin, each value's Bambu filaments in the model

> Decided by Cansin on 2026-11-03, #805, in grilling. Amends ADR 0020 (its two styles are the Skeleton's values,
> plain renamed mechanical), ADR 0008 (the viewer's Skeleton switch) and ADR 0019 (the `-mechanical` documents).
> Amended 2026-11-03 (#806): the site's header has a Theme bar, a select per category, its values read from `THEMES`;
> the pick, kept in the address (`?skeleton=realistic&skin=morty`) and the reader's local storage, chooses the viewer's
> GLB and every page's pictures and filaments, each drawn in every Skeleton; the README shows the default.
> Amended 2026-11-03 (#819): a Theme is four axes, a Shape and a Palette per category (GLOSSARY): the Skeleton's Shape
> realistic or mechanical and Palette anatomical (the old realistic colours), robot (the old mechanical ones) or black
> (PETG Basic Black for every group); the Skin's Shape and Palette each morty, bart or cansin (#813). The Palettes of a
> category share its Colour groups, so any Palette paints any Shape. A Preset names one Theme: Cansin's build
> (mechanical, black, cansin, cansin; its Skin Morty's Shape until #813's Shells exist), the default the README, the
> site's first visit and the default pictures show, then Morty and Bart (realistic, anatomical, each its own Skin). The
> Theme bar is one select of the Presets, the address `?preset=cansins-build`; the buy list and the print tables follow
> it. Blender draws the GLBs per Shape alone, each material named by its Colour group, and the pictures per Preset alone;
> the viewer mixes any Shape with any Palette, setting each group's base colour from `THEMES` in the browser. That
> reverses the option below for the viewer only: the GLB carries just the satin material (base colour, roughness,
> specular) and the toon band and lines are Eevee's or the viewer's own, so a swapped base colour loses nothing, while
> Blender stays the source of the Shapes and the finish.
> Amended 2026-11-03 (#876): the Skin's Shape is none too, on every Preset's mix: the Skeleton bare as the stills' bare
> look has it (#843: its Shells off, the realistic skull's full bones for the worn ones). Blender draws Stage 3 bare in
> each Skeleton shape (`next-mech-back-bare`, `-mechanical-bare`); Stages 1 and 2 wear no Skin, so none draws them as
> they are.
> Amended 2026-11-03 (#883): a Preset is picked only by the address or the reader (stored); until one is, the pages
> show the default's and the viewer opens in its own mix, Morty's with Skin shape none: the bare anatomical Skeleton,
> a Skin switched on Morty's Palette.
> Amended 2026-11-04 (#894, spec #889): the default Preset is the Default build (slug `default-build`, first, in place
> of Cansin's build): Skeleton shape mechanical, Skeleton palette black, Skin shape none, Skin palette default. The
> Skin palette cansin is renamed default, its four PLA Pure colours unchanged; the Skin shape cansin (#813's Shells)
> keeps its name. The README's stills, the posters, the Site's first visit and every viewer with no Preset picked
> show the Default build, in place of #883's viewer mix; the Themes page says so once, read from the Model. Black
> parts render as a lifted charcoal (ADR 0008), the filament's hex unchanged.

The next Mech's look is a Theme (GLOSSARY): one value of each category, today the Skeleton (the PETG parts:
`realistic`, every part drawn as Bones, or `mechanical`, ADR 0020's plain style) and the Skin (the magnetic PLA Shells:
`morty` or `bart`); the default is `realistic` and `morty`, which the README, the site's first visit and the default
renders show. Each value names, for each of its category's Colour groups (at most four), the Bambu filament it is
printed in, by line, name, code and the hex BambuStudio's `filaments_color_codes.json` gives it. That data has one
source, model/geometry.py `THEMES` (ADR 0011): each printed part carries its Colour group (`PRINTED`), and the
pictures, the viewer's GLBs, `just view`, the build guides and the docs read the colour from the document's Theme.
A document is drawn per Skeleton (`next-stage1`, `next-stage1-mechanical`), each in the default Skin until the Skins'
Shells exist (#665), when Stage 3 is drawn per Skeleton and Skin; Blender writes each one's colours into its GLB and
pictures. More values or categories may join later, each a new key there. The picks and the research behind them:
docs/research/2026-11-03-bambu-theme-colours.md.

## Considered Options

- Colours per spool (black PETG, PLA Pure in four colours): one look; a second Skeleton style or a second Character
  had nothing of its own to show.
- The viewer recolours one GLB per Theme in the browser: fewer GLBs, but a second source of the look beside Blender's
  (ADR 0008).
