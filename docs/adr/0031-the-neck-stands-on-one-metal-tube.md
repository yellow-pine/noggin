# The neck stands on one metal tube

> Decided by Cansin on 2026-11-27, ticket #1075, on #1060's numbers. What follows for its foot, its length and its
> screws was decided on the ticket (made while away; Cansin to confirm). Builds on ADR 0030.

The neck carries the head's torque down to the Torso: 3.4 N·m when the tilt servo stalls, and 0.95 N·m of twist when
the pan servo does. Printed rails strong enough for the first cut the third neck bone in two (#1064: 18 × 10.4 mm in
PETG), and the L rail still held only SF 0.58 under the second (#1063).

- **One aluminium tube, 10 mm outside with a 1 mm wall, on the cervical canal's line** (`neck.TUBE`, ADR 0030's
  straight path): the first part of the Skeleton that is bought and neither printed nor an electronic. It holds both
  stalls at once at SF 2 on the lowest proof stress a 6060, 6063 or 6061 tube in T6 or T66 is sold with (140 MPa,
  EN 1999-1-1; `docs/research/2026-11-28-neck-tube-aluminium.md`), hides the neck cable in its bore and passes no
  neck bone but through its canal.
- **The builder cuts it to 100 mm and drills it twice.** Each hole takes an M3 across the tube and a printed part,
  against the twist. The holes run across the Mech, along the axis the head's torque bends the tube about, where a
  hole costs 2 % of its strength; on the outer fibres it costs 40 %.
- **Two printed parts ride it.** The neck socket holds its foot on the Torso's floor. The cervical carrier, on its
  top, is one piece: sleeve, a wing to each trunnion and the strut to the tilt's reaction anchor. The tilt's own loop
  (the bar on the anchor, the nod plate on the trunnions) closes inside that piece, so the tube under it carries a
  pure couple.
- **The tube's foot stands 13.6 mm over the Torso's floor**, and the neck cable turns out under it in a 12 mm bend.
  The Torso is 24 mm high inside and C7's foot 28 mm over its floor: a 16 mm bend (the flexing spans' floor) would
  leave the socket 10 mm of tube and SF 1.2. That bend never flexes, and its own floor is 3 lead diameters.
- **The socket is bolted through the Torso's floor**, four M3 countersunk from below with nuts on its flange, so no
  printed thread carries the head's torque and nothing stands under the foot (#1062).

## Considered Options

- Printed rails, thicker still: both would need the R rail's section, through C3's and C4's sides on both sides.
- Two rods up the rails' lines (M6 in 8.8, or 8 mm steel): four clamps, and a hole through each lateral mass.
- A steel tube, 8 × 1 mm stainless: SF 2.05 on recalled figures, with nothing to spare for a hole.
- A collar and a crosshead apart on the tube: a third hole, and the tilt's loop through the tube between them.
- The socket up into C7's canal for a 16 mm bend at the foot: 4.5 mm of C7 carved for a bend that never moves.
- A socket printed as part of the Torso: no joint at all, but the Torso is to be redrawn (#879) and the socket
  outlives it.
