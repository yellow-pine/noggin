# The Skeleton in two styles, plain and Bones

> Decided by Cansin on 2026-11-02, #704, after the Bones pilot (#703).
> Amended 2026-11-03 (#805, ADR 0022): the two styles are the Skeleton's Theme values, Bones `realistic` and plain
> renamed `mechanical` (`next-mech-back-mechanical`, the Viewer's Skeleton switch).
> Amended 2026-11-03 (#809, Cansin: "The bone vs. mechanical difference should only be visual, not calibration,
> configuration etc."): every Bone is carved from its mechanical part, lying inside it (model/printed/bone.py `carved`,
> a test per styled part); where a Bone that prints as drawn cannot fit inside (the tie-bar's V, the yoke's cradle, the
> bail's struts), the mechanical part takes it in instead (`grown`), its interfaces unchanged. So physics runs on the
> mechanical documents alone (geometry.SIMULATED: the whole Mech and Stage 1): clearance, overlap, torque, strength,
> the sim and its gates; realistic is visual only (renders, the Viewer, the print files) and its figures are the
> mechanical one's. The Bones' own strength checks are dropped (Cansin's call: a thin Bone could pass and break on the
> printer). Read "every gate" below as the mechanical one's.

Every Skeleton part is drawn in two styles behind one switch: plain (boxes and cylinders) and as Bones (GLOSSARY),
with the same interfaces (bores, pockets, seats, sockets) in both, and each head variant is built twice from the same
layout, as Bones (`next-mech-back`, "Back") and plain (`next-mech-back-plain`, "Back plain"). Both stay permanently:
each has its gestures, Explode, pictures and every gate, and the Viewer's toggle offers both, so the two looks can be
compared on the same Mech and the plain one stays the fallback should a Bone fail on the printer. A new Skeleton part,
or one a ticket reshapes, is drawn in both styles (model/printed: `STYLED`; one still drawn plain alone names the ticket
that draws its Bones, `UNSTYLED`).

## Considered Options

- Replace the plain shapes with Bones (#704 as first filed): one look, half the builds, but nothing to compare or fall
  back to.
