# Patents on figure heads: eyes, lids, jaw, neck, swappable shells

Researched 2026-11-02. Purpose: techniques the Mech (#51) can learn from, and any live patent its design might
read on. Not legal advice: "reads on" below is a plain claim-by-claim comparison, marked [I].

Read from the patent's own text: Google Patents pages (claims, description, legal events) or the USPTO grant PDF
(image-ppubs.uspto.gov). Status is Google's legal-status line unless marked "by term" (20 years from filing, worked out
from the grant's front page because Google was rate-limiting).

Sources:
- [HAN] US7113848B2, David Hanson (individual), priority 2003-06-09. Expired, lifetime (2024-06-11). https://patents.google.com/patent/US7113848B2/en
- [HAN2] US8594839B2, same family and owner. Expired, fees not paid. https://patents.google.com/patent/US8594839B2/en
- [WR] US10723017B1, Shenzhen Wangrui Technology, priority 2019-04-01. Expired, fees not paid. https://patents.google.com/patent/US10723017B1/en
- [FB] US11376733B2, Facebook Technologies, priority 2019-06-11. Expired, fees not paid. https://patents.google.com/patent/US11376733B2/en
- [DEM] US9776097B2, Disney Enterprises, priority 2015-06-04. Live, expires 2035-08-21. https://patents.google.com/patent/US9776097B2/en
- [DEF] US8715033B2, Disney Enterprises, priority 2009-09-16. Live, expires 2033-03-06. https://patents.google.com/patent/US8715033B2/en
- [DLCD] US8651916B2, Disney Enterprises, priority 2010-01-18. Live, expires 2031-06-25. https://patents.google.com/patent/US8651916B2/en
- [FUR] US6149490A, Tiger Electronics (Furby), priority 1998-12-15. Expired, lifetime (2018-12-15). https://patents.google.com/patent/US6149490A/en
- [FUR2] US6544098B1, Hasbro, same family. Expired, lifetime (2018-12-15). https://patents.google.com/patent/US6544098B1/en
- [CAL] US4900289A, Cal R&D, priority 1988-01-29. Expired (2008). https://patents.google.com/patent/US4900289A/en
- [HCL] US7207859B1, Hasbro, priority 2004-04-30. Expired, lifetime (2025-04-28). https://patents.google.com/patent/US7207859B1/en
- [GEM] US6604981B1, Gemmy Industries, priority 2001-04-12. Expired, fees not paid. https://patents.google.com/patent/US6604981B1/en
- [PD] US5823847A, Pragmatic Designs, filed 1997-02-18. Expired by term (2017). Grant PDF: https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/5823847
- [BOS] US10120386B2, Robert Bosch Start-up Platform (Kuri), priority 2016-11-18. Live, to 2037-11-17. https://patents.google.com/patent/US10120386B2/en
- [WOW] US10449463B2, WowWee, priority 2017-05-09. Live, to 2037-11-03. https://patents.google.com/patent/US10449463B2/en
- [SONY] US6711469B2, Sony, priority 1999-10-29. Expired, fees not paid. https://patents.google.com/patent/US6711469B2/en
- [EVO] US11529567B2, Evollve (Ozobot), priority 2016-01-06. Live, expires 2037-06-04. https://patents.google.com/patent/US11529567B2/en
- [FUH] EP3437029B1, Furhat Robotics, priority 2016-03-29. Live (Europe), to 2037-03-20. https://patents.google.com/patent/EP3437029B1/en
- [RBX] US11235255B2, Realbotix, priority 2018-06-19. Live, expires 2039-11-23. https://patents.google.com/patent/US11235255B2/en
- [MCM] US8888553B2, M. McMullen (individual), priority 2012-04-28. Live (reinstated), to 2032-04-28. https://patents.google.com/patent/US8888553B2/en
- [HMAG] US10870064B1, Hasbro, filed 2016-06-24, 646 days of term adjustment. Live by term (about 2038); fee status
  not read. Grant PDF: https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10870064

## 1. Linked eyes and the eye gimbal

- **Hanson's eye frame** [HAN]. Each eye pivots on its own vertical axis. Rigid struts tie those pivots to one "eye
  frame" that keeps the axes parallel, so one actuator turns both eyes left/right. The whole frame then tilts on a
  hinge whose horizontal axis passes through both eye centres, so the eyes turn like balls in their sockets. Expired.
  This is #51's linked gimbal almost exactly: one servo for left/right, one for up/down.
- **Wangrui's eye system** [WR]. A horizontal movement frame carries both eyeballs and turns them together. A vertical
  movement block holds that frame with upper and lower arms. The sockets in a front panel fix each eye's centre. Both
  upper lids hinge on one axis on the front panel; one motor drives them, and the lower lids are fixed. Expired.
  The same layout as [HAN], with the lids mounted on the face plate rather than on the gimbal.
- **Two axes through the eye centre** [FB]. Each eyeball turns on two axes that cross at a fixed centre point,
  with encoder bars to measure the angle. Expired.
- **Disney's eyes** [DEM, DEF, DLCD] put an electromagnetic drive and a gimbal hub inside a floating eyeball, or show a
  screen under a lens. Live, but every independent claim needs the electromagnetic drive, a fluid suspension or a
  display. A servo-driven gimbal reads on none of them [I].

## 2. Eyelids

- **Lids on the eye's own axis** [FUR]. Furby's two eyelids are "one-third spherical" shells joined by a bearing ring.
  They sit on the same pivot shaft as the eyes, so each lid stays concentric with its eyeball. Expired.
  [I] On #51 this means the lid arms pivot on the gimbal's up/down axis. The lid then clears the eyeball cap by the
  same gap at every gaze angle, and lids that follow gaze are just software: lid angle = lid level + eye up/down angle.
- **Lids on the face plate** [WR] hinge on a fixed axis, so a lid does not follow the eye up or down. Expired.
- **Magnet-coupled lid** [RBX]. A drive band behind a soft face mask holds magnets that couple to the eyelid support
  glued inside the mask's own eyelid. Live to 2039. Every independent claim needs an eyelid that is "a unitary
  component of the face mask" plus an annular-sector support frame and drive band. #51's lid covers are separate rigid
  PLA parts on the lid arms, so they read on none of these claims [I].
- **Lids following gaze.** I found no patent with a mechanical link from eye pitch to lid; [HAN] and [BOS] drive the
  lids separately. [I] #51 keeps a servo per lid, so the coupling is software and needs no mechanism.

## 3. Jaw and mouth

- **Spring to closed, damper against bounce** [PD]. A motor winds a string that opens the lower lip. A tension spring
  shuts it when power drops, and a sprung friction brake on the motor shaft stops the lip bouncing past fully open.
  Expired by term.
- **Jaw motor in the head, pan motor in the body** [GEM]. A reciprocating motor in the body turns the head side to
  side on an upright axle, and a separate motor in the head drives the lower mandible. A neckerchief hides the seam
  between head and body. Expired.
- **One motor for jaw, eyes and lids** [CAL]. The jaw and eyes move whenever the motor runs. A friction coupling
  blinks the lids once each time the motor reverses. Expired.

## 4. Neck pan and tilt

- **Pan on the body, tilt carried by pan** [BOS]. A main head chassis turns on a body mount (pan). A head-tilt chassis
  rides on it, and the lower lids hang from the tilt chassis. Live to 2037, but the claims are a method: on a failed
  task the robot gathers more sensor data, makes an expressive move, then retries. The noggin service mirrors Claude
  Code events and attempts no task of its own, so it does not read [I]. The mechanism is in the description only.
- **Clutch against a held head** [HCL]. A clutch in the gear train lets the head stop when a child holds it, so the
  motor does not stall. Expired. The PG001's own slip clutch does this already (docs/build/calibration.md).
- No neck patent from Disney, Sony or Spin Master turned up in Google Patents searches by assignee with
  eye/eyelid/jaw/head/neck terms.

## 5. Swappable shells and faces

- **Cover recognised by a key** [SONY]. A detachable cover carries a pattern (in claim 2, a raised-and-recessed
  pattern that fits only the right partner). The robot reads it and switches the model that picks its actions.
  Expired.
- **Cover identified electronically** [EVO]. A tool-free character skin carries an ID. The toy reads it and runs that
  character's program. Live to 2037. Claim 1 needs a "self-propelled", "autonomous toy robot". The Mech stays put,
  so it does not read [I].
- **Detachable face with a display** [FUH]. The robot adapts its personality to the face part, using data received
  from that part. Live in Europe to 2037. It needs a display surface on the face part; #51's shells have none [I].
- **Magnets on a face mask** [MCM]. Magnets inside the mask couple to magnets on the support, which slide to change the
  face's shape. Live to 2032. Claim 1 needs the second magnet to be "adjustable over a range of positions". Fixed
  magnets do not read [I].
- **Polarity-keyed magnets** [HMAG]. An accessory carries a pair of magnets of opposite polarity, and the body carries
  a matching opposite pair. The accessory can sit only one way round and snaps into alignment. Live by term, but
  every claim needs a spherical self-propelled body with wheels, so it does not read [I].

## 6. Few actuators, many features

- **Furby** [FUR]. One small reversible motor turns one control shaft. Cams on that shaft move the eyes, lids, mouth,
  ears and feet; running the motor backwards gives non-cyclic, life-like motion. An optical counter on a slotted gear
  replaces a potentiometer, so there is less friction and the toy survives drop tests. Expired.
- **Cal R&D** [CAL]: motor reversal triggers a blink through a friction coupling. Expired.
- [I] #51 already has one servo per feature (7 servos), so the cam tricks are only a fallback if a servo is lost. The
  one to keep in mind: [FUR]'s lids and eyes on one shaft.

## Practices for #51

| Technique | Feature | From | Status |
|---|---|---|---|
| Struts on a frame keep both eyes' vertical axes parallel (one left/right servo); the frame tilts on a hinge through both eye centres (one up/down servo) | eye gimbal | [HAN] US7113848 | expired |
| Sockets in a front plate fix each eye's centre; the frame carries both eyes | eye gimbal | [WR] US10723017 | expired |
| Lid pivot on the eye's up/down axis; lid as a spherical shell concentric with the eyeball | lid arms, lid covers | [FUR] US6149490 | expired |
| Lid follows gaze in software: lid angle = level + eye pitch [I] | lid gestures | none needed | n/a |
| Spring biases the jaw closed; light friction stops overshoot [I: on a position servo the spring takes up gear backlash] | mouth | [PD] US5823847 | expired |
| A collar or neckerchief hides the head-to-body seam over the pan joint | collar/shirt shell | [GEM] US6604981 | expired |
| Opposite-polarity magnet pairs so a part seats only one way and self-aligns | every magnet-held shell | [HMAG] US10870064 | live, but its claims need a rolling ball robot |
| If shells are ever auto-detected: a key pattern on the cover, read by the base | shell swap | [SONY] US6711469 | expired |

## Conflicts with #51

- **Identical magnets everywhere let parts fit wrongly** [I]. With one disc size everywhere and every magnet the same
  way up, a left lid cover fits the right arm, and a symmetric shell can seat rotated. Proposed change: keep the
  one disc size, but give each part a polarity pattern (e.g. one magnet flipped, at a different spot for left and
  right) so it seats only one way ([HMAG], technique only).
- **Lid pivot axis.** #51 says only "eye gimbal with ... lid arms". If the lid arms hinge on a fixed head axis
  (as on [WR]), gaze-following lids need a large lid travel, and the lid-to-cap gap changes as the eyes look up and
  down. Proposed change: pivot the lid arms coaxially with the gimbal's up/down axis ([FUR]). Each lid keeps its own
  servo, so wink is unchanged.
- **Live patents to stay clear of** [I]:
  - [RBX], to 2039: do not mould the lids into the head shell as one flexible part with magnet-coupled drive bands.
    #51's separate lid covers are clear.
  - [EVO], to 2037: do not make the Mech self-propelled while also detecting its shell electronically to switch
    character software.
  - [FUH], Europe to 2037: do not put a display in a detachable face part.
  - Character selection by the noggin service's settings reads on none of them.
- No #51 decision is beaten on the eyes or neck: the linked gimbal, one servo per lid and pan with tilt carried on it
  all follow expired art ([HAN], [WR], [BOS]'s layout).

Unverified:
- [HMAG]'s maintenance-fee status. (The second Bosch patent, US10120387, claims a navigation method only:
  grant PDF, claim 1.)
- A Groove X costume patent (JP7708451B2), and the Teddy Ruxpin patent: Google Patents returned 503 during the session.
- Sony AIBO neck, Spin Master and Disney jaw or neck patents: searches by assignee found none relevant. That is not
  proof that none exist.
