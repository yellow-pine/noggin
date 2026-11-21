# Parts

> [!WARNING]
> **Being designed, not built yet.** The Mech is our own design (#51), in the model until it is printed; every size in
> it is inferred until then. Read the list, follow the design, and wait to buy for a Stage until its guide says it is
> built.

The Mech grows in three Stages, each complete on the desk: the eye block on its test stand with the eyes Core
([Stage 1](stage-1.md)), then on the neck over the Torso with the boards in the head and the neck Core
([Stage 2](stage-2.md)), then with the jaw, the whole Mech ([Stage 3](stage-3.md)). This page is the shopping list;
each Stage's guide lists, from the model, every part it adds, printed or bought.

## Parts to buy

What each Stage adds that you buy, from the model (a Stage buys only its own column):

<!--{{ shopping }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
The count per Stage is in [the table on the site](https://yellowpine.com/noggin/docs/build/parts/#parts-to-buy), built
from the model.
<!-- #}-->

Stage 1 needs Stage 2's pack and switch board too: a Core's USB-C powers the Core alone, never the servos, so they lie
beside the test stand until the Torso holds them (inferred). Buy both with Stage 1, and a fifth servo if you will
[film one](tests.md#filming-a-servo). Where to buy each:

| Part | What to buy | Code |
|---|---|---|
| Core | Bambu Lab CyberBrick Core | XA003 |
| Shield | CyberBrick X11 Receiver Shield | XA004 |
| servo | CyberBrick 9 g servo with clutch protection, the 180° one (the 360° one turns on and on, so it is not used) | PG001 |
| servo horn | the horns that come with each servo | with the servo |
| battery pack | CyberBrick 2S battery, 7.4 V 800 mAh | PC003 |
| switch board | CyberBrick switch module | XA007 |
| power-path board | nomo's BQ25886 2S charge board on Tindie, its 18650 holder snapped off and ICHGSET swapped to 2.87 kΩ for 0.75 A | BQ25886 |
| USB-C hub | Adafruit CH334F Mini 4-Port USB Hub Breakout | 5997 |
| bulk capacitor | a 470 µF 16 V low-ESR electrolytic, across the Y lead where it enters the Shields | 470 µF 16 V |
| M3 x 16 mm pivot screw | a steel M3 x 16 mm socket-head screw, greased: each busy pivot's shank | generic |
| M2 x 8 mm servo screw | an M2 x 8 mm self-tapping screw, two through each servo's tabs | generic |
| M3 x 10 mm head screw | an M3 x 10 mm screw, four holding the test stand, then the head mount, under the gimbal frame's plate | generic |
| M3 nut | an M3 nut, one on each head screw | generic |

The CyberBrick Beginner Hardware Kit ZK004 holds both Cores, one Shield (its other shield is the transmitter, which the
Mech doesn't use), a switch board, a pack, its USB charger and one usable servo; the Battery Upgrade Kit ZL003 adds a
second pack, to keep one on charge.

The screws and nuts are counted from the model: a pivot screw for each pin and pivot its linkages turn on, two servo
screws per servo, and the four head screws with their nuts. Their lengths are inferred: one pivot screw length covers
the deepest pin (the pan's), so cut each shallower pin's screw to its depth. A bar's end on a servo horn takes a pivot
screw in the model, though the horn's own hole is smaller (inferred). The model doesn't fix the boards yet, so it counts
no screws for them.

Also needed, which the model doesn't count as parts:

- From Stage 2: a Y lead from the switch board to both Shields, four 24 AWG conductors up the neck from the Torso to
  the head, and the balance spring, a torsion spring on the tilt shank holding the head's weight (the model sizes it
  to the head; inferred).
- A USB-C charger or laptop port advertising 3 A. *Upcoming (#971): a TUSB320 input-limit detector for lower-current
  sources ([Stage 2](stage-2.md#wiring)).*
- For a Skin: 4x2 mm N52 magnet discs, two per Seat ([Themes](../face-design.md#seats-and-magnets)).
- *Upcoming (#902): a standard metal-gear servo (about 10 kgf·cm at 5 V) for the tilt and a thrust bearing (an F8-16M,
  or a 608 in a seat) under the head for the pan, both inside the skull.*

### Filament

The Skeleton prints in PETG and the Skin's Shells in PLA, held on by magnets, each Colour group in its Theme's filament
([Themes](../face-design.md)): the default Preset's unless you pick another in the header. Bambu's PETG Basic and Matte
lines for the Skeleton (the model takes PETG HF's figures as the worst case), PLA Basic, Matte and Pure for the Skins.
The filaments of the Preset picked in the header, with the Colour groups each prints:

<!--{{ filaments }}-->

<!--{# GitHub shows the line below; the site drops it for the list, which it builds from the code -->
The list for the Preset you pick is [on the site](https://yellowpine.com/noggin/docs/build/parts/#filament);
every Palette's filaments are in the table on [Themes](../face-design.md).
<!-- #}-->

## Printer and tools

- A printer with a 0.4 mm nozzle that prints PETG and PLA; every printed part fits a 256 mm bed (#893). Our parts
  print from `just stl` (model/build/stl, mm).
- A small flat screwdriver and a small cross-head one, a ruler, superglue for the magnets and the glued-in Shells, and
  grease for the pivots, and a screw cutter for the pivot screws (the M3 hole in wire strippers; inferred).
- A soldering iron, for the power-path board's resistor, the capacitor and the leads (inferred).
- Print the [clearance coupon](tests.md#the-clearance-coupon) first: it finds the fit your printer gives a pivot and a
  magnet pocket.

## On the Mac

macOS, [uv](https://docs.astral.sh/uv/) (Python 3.14 and mpremote come with it), [just](https://just.systems/)
(`uv tool install rust-just`) and Claude Code, and this repo cloned (`git clone
https://github.com/yellow-pine/noggin`, then `just venv` in it). `uv` manages
`.venv` and runs mpremote and pytest; the system Python is 3.9 and is not used.
