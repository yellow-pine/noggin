# A seam is a 0.8 mm gap, and the Shell that stands still gives way

> Decided on 2026-11-27, ticket #850 (made while away), and confirmed by Cansin the same day: the shirt gives way,
> its collar cut lower and scooped under the chin (spec #893). Builds on ADR 0028.

ADR 0028 cuts Morty's Shells with no room between them. A worn Shell must keep 0.5 mm from every part it does not
sit on, another Shell included, in every pose (`model/printed/test_skin.py`). This is the room each seam gets
(`model/morty/shells.py`: `SEAM`, `cleared()`).

- **At rest, 0.8 mm at every seam.** The face steps back that far from the hair and from the chin, and the shirt
  from the collar. The hair and the chin keep the Sculpt's own boundary. A brow is no seam: it is glued in the face,
  0.2 mm off it all round (ADR 0028). 0.8 mm is the gate's 0.5 mm and what its sampling
  can misread (inferred).
- **Where two Shells move against each other, the one that stands still gives way.** The head keeps Morty's shape
  through tilt ±20°, pan ±45° and the jaw's 25°, all at once. The shirt is cut back wherever the hair, the face or the
  chin comes within the gap of it, and the face wherever the opening chin does.
- **What that costs, measured.** The shirt loses 48.6 cm² of its 329 cm² near the collar: its top stands 9 mm lower
  all round, and under the chin it is scooped out to 38 mm deep, where the open jaw of a head tilted down reaches. It
  weighs 57 g, 69 g before. The face loses 9.8 cm² under the jaw behind the chin, where the chin's back edge swings
  down and back.
- **The walls decide, not the solid head.** The head's rim turns down inside the shirt's collar where there is room,
  and nothing is cut for it there. Bone and mechanism under the rim are held by the worn Shells' gates, not here.
- **Measured on grids, held by exact checks.** The reach is read on 0.5 mm grids: the least distance over the pan
  along each point's circle round the pan's axis, then the tilt every 0.1°. `model/morty/test_shells.py` measures the
  gap that is left on the solids themselves, at poses the cutter did not sample: 0.8 mm between the hair and the
  face, and 1.2 mm at least between Shells that move against each other (the grids' rounding is allowed for).

## Considered Options

- The head gives way: Morty's face and hair would lose their lower rim, the part of him people look at.
- A narrower range for the Skin's sake: the tilt, the pan and the jaw are the mechanism's (#978), and ADR 0027 has
  the mechanism fit the Skin's shape, not the Skin limit the motion. If Cansin prefers the shirt whole, the range the
  noggin service drives is where to take it from.
- A swept solid from unions of the turned head: thousands of solid cuts for 0.1° steps, and still no gap round it.
- The solid head against the shirt: it cuts 3 cm³ more at one pose alone, for a floor the head does not have.
