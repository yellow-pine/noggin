# The neck stands still inside a skin that moves

> Decided by Cansin on 2026-11-27, spec #893 (its comment "Decided by Cansin (2026-11-27, second grilling round…)"):
> the neck's skin rides the head and the seam is at the collar. What follows for the mechanism was decided on ticket
> #1039 with #874 (made while away; Cansin to confirm the straight path). Builds on ADR 0027 and ADR 0028.

The mechanism turns and nods the skull at its base, so the neck's bones and the cervical carrier never move. Morty's
Sculpt shows no neck to cut a Shell from (ADR 0028), so everything above the collar is the head's skin: it turns ±45°
and nods ±20° round what stands still inside it.

- **The margin holds through the whole range.** Bone and mechanism stay 2.1 mm under Morty's surface (ADR 0027). For
  a part that does not turn with the head, that surface is the head's skin wherever tilt and pan together carry it:
  a part that stands still (the cervical carrier, its reaction anchor, C1 to C7) through both, a part on the nod
  plate through the pan, the tilt lever and its bar through their own swing besides. A part that rides the head keeps
  it at rest. `model/review/test_nape.py` holds the neck's parts to it on the Sculpt git holds.
- **The skin's rim swings through the neck.** The head tilts about an axis 60 to 70 mm above the collar. Face up 20°,
  the nape's rim comes forward to y 86 at z −119 (the head's frame, mm); face down 20°, the throat's rim goes back to
  y 58 at z −131. Between the two, what stands still has about y 60 to 84 at the collar.
- **The cervical path runs straight between them**, from C7's foot (y 72 at z −146) to the canal's top under the tilt
  axis (`neck.CERVICAL_PATH`). It no longer bulges back to y 91.6 to follow a real cervical spine's curve: that bulge
  stood where the nape's rim arrives. The vertebrae's canals follow the path (ADR 0025's Warp reads it), so the neck's
  bones stand in the middle of Morty's neck, leaning 4° forward going down where a real neck's lean back. It shows
  only with the Skin off.
- **The rails and the mechanism clear both rims; C5 and C6 do not, at any path.** A vertebra here is about 47 mm front
  to back, and the room between the rims is 24 mm. y 72 is where #874 measured the least of them left in the rims' way
  (#1039's comments). What gives for those two (the tilt's range, the seam, or the bones) is open, on #874.
- **The mechanism moves, the skin and the range stay.** The tilt lever's arm steps inboard round its horn, so the pan
  swings its tip across the nape nearer the pan axis. The reduction's arms, the tilt's hold and the range are
  unchanged.

## Considered Options

- The neck's skin fixed, with a seam under the jaw (#969 until today): Cansin chose the collar, where the Sculpt has
  its own edge.
- The rim gives way: Morty's nape and throat would lose their lower edge, and ADR 0029 has the Shell that stands
  still give way, not the head.
- A narrower tilt for the neck's sake: the range is the mechanism's (#978), and ADR 0027 has the mechanism fit the
  skin.
- Rails that weave round the rim's sweep and return to the curved canal: the vertebrae behind them would still stand
  in the rim's way.
- A shorter crank on the tilt servo: at 19.5 mm its bar meets the case's corner when the face is up, and every force
  in the reduction rises.
