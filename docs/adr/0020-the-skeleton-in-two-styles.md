# The Skeleton in two styles, plain and Bones

> Decided by Cansin on 2026-11-02, #704, after the Bones pilot (#703).

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
