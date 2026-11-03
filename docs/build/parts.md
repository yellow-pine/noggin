# Parts

> [!WARNING]
> **Being designed, not built yet.** The Mech is our own design (#51), in the model until it is printed; every size in
> it is inferred until then.

The Mech grows in three Stages, each complete on the desk: the eye block on its test stand with the eyes Core
([Stage 1](stage-1.md)), then on the neck over the Torso with the boards in the head and the neck Core
([Stage 2](stage-2.md)), then with the jaw, the whole Mech ([Stage 3](stage-3.md)). Each Stage's page lists, from the
model, the parts it adds. This page is the shopping list.

The Skeleton prints in PETG and the Skin's Shells in PLA, held on by magnets, each Colour group in its Theme's
filament ([Themes](../face-design.md)), Cansin's build unless you pick another Preset. Our printed parts print from
`just stl` (model/build/stl, mm).

## Parts to buy

The one place the shop's names and codes appear (2026-10-31, grilled; #51). Electronics are Bambu Lab's CyberBrick
range, filament is Bambu's PLA and PETG lines the Themes name.

- Owned: Beginner Hardware Kit ZK004 (2 Cores, an X11 receiver shield + a transmitter shield, switch module, 2S pack,
  charger, one 180 and one 360 servo), Battery Upgrade Kit ZL003 (second switch module + second pack), 4 PG001
  servos, M3x10, M2x12, M2 nuts (20 each); ordered 2026-10-31 from the Bambu EU store: X11 Receiver Shield XA004 x1,
  servo PG001 x3, battery PC003 x1.
- The Mech uses: 2 Cores, 2 Shields, 1 switch board, 1 pack with a Y lead to both Shields, 7 PG001 servos (4 on the
  eyes Core, 3 on the neck Core); the kit's spare M3 screws as the busy pivots' shanks. Spare: a pack on charge (the
  charger, off the Mech), a switch board. The 360 servo turns continuously, so it is not used.
- To buy: the magnets, 4x2 mm N52 discs, the one new purchase.
- Filament: each Preset's Bambu filaments, by line, name and code ([Themes](../face-design.md), from the model; the
  picks: docs/research/2026-11-03-bambu-theme-colours.md): PETG Basic and Matte for the Skeleton, the model taking
  PETG HF's figures as the worst case, PLA Basic and Matte for the Morty and Bart Skins. Owned: PLA Pure in Milky Pink, Pure White,
  Absolute Black and Apricot (docs/research/2026-10-31-filament.md), the cansin Skin's four, and black PETG, which
  prints Cansin's build's whole Skeleton.

The filaments of the Preset picked in the header, with the Colour groups each prints:

<!--{{ filaments }}-->

<!--{# GitHub shows the line below; the site drops it for the list, which it builds from the code -->
The list for the Preset you pick is [on the site](https://yellowpine.com/noggin/docs/build/parts/#parts-to-buy);
every Palette's filaments are in the table on [Themes](../face-design.md).
<!-- #}-->

## On the Mac

macOS, [uv](https://docs.astral.sh/uv/) (Python 3.14 and mpremote come with it) and Claude Code. `uv` manages
`.venv` and runs mpremote and pytest; the system Python is 3.9 and is not used.
