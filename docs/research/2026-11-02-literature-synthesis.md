# Literature synthesis for the next Mech (#51)

Researched 2026-11-02. Purpose: one view of what the eight literature notes of the same date say for #51 (on hold, its cranium layout parked), and the changes they propose to it, inside and outside its fixed limits.

The notes: `2026-11-02-literature-graphics.md`, `-mechanical.md`, `-electrical.md`, `-simulation.md`, `-patents.md`, `-perception.md`, `-motion-control.md` and `-cams-am.md`. This file reads no new source.

Key:
- A finding cites the note by its short name and that note's own tag: mechanical [V] is the source tagged [V] in `2026-11-02-literature-mechanical.md`.
- mechanical [I] is that note's author's inference. A bare [I] is mine, made in this synthesis.
- "Cost" says what acting on the finding takes: parts, print, code, model work or money. "None" means free.
- Where notes disagree, both are given.

## Hardware

- **Seven servo starts overload the one pack.** A step command saturates a PG001 at stall current, 0.55–0.65 A; seven at once is 3.9–4.6 A, over the 3 A that the Shield, the pack and the switch board each allow (motion-control [PG][I]). Start current is stall current in a DC motor (electrical [MC][PG]). Both notes budget starts in software: at most two saturating steps per Core (motion-control [I]), or N starts per 20 ms frame across both Cores sized on an empty pack (electrical [C][I]), and the noggin service offsets the two Cores' gesture starts by a frame (electrical [I]). Cost: code in the noggin service and the eye program; model work in `model/electrical.py`.
- **The pack sags most when nearly empty.** Series resistance is flat over 20–100% charge and rises steeply below 20%: about 0.50 Ω for our 2S pack at empty, against the constant 0.21 Ω in `model/electrical.py` (electrical [C][I]). A 20–200 ms servo start sees only that resistance (electrical [C][I]). Cost: model work.
- **The pack cuts on loaded voltage, before the open-circuit voltage reaches 5.8 V.** A protector trips after a 20–144 ms delay (electrical [BQ]), so near empty a multi-servo start darkens the whole Mech mid-gesture (electrical [I]). The 5 V servo rail is already at 3.65 V at cutoff, under the servos' 4.8 V minimum (electrical, from `model/electrical.py`). Cost: none to accept; model work to model the cutoff as an event.
- **No Core can read the pack voltage.** The Shield has no sense and the ADC tops out at 2.5 V (electrical [DS][HDG]). A divider of 100 k / 39 k plus 100 nF on the neck Core's free port 4 (GPIO0, ADC1_CH0) would read it (electrical [DS][HDG][I]). Cost: two resistors and a capacitor, cents, but parts #51 does not own.
- **A pack cut can be detected without new parts.** Both Cores' beacon uptimes resetting together with no `reboot` sent means a cut; `reset_cause()` cannot tell a brownout from a power-on (electrical [MP][I]). The pack cut comes before an ESP brownout (electrical [KC][DS][I]). Cost: code in the noggin service and `noggin status`.
- **One USB cable at a time.** The only shared conductor between boards is the pack's negative; a ground loop forms only if both Cores are on USB to the Mac at once (electrical [I]). Cost: none.
- **A bulk capacitor cannot carry a servo start.** One 0.57 A start for 20 ms at 0.3 V sag needs about 40 mF (electrical [TI][I]). Only firmware can limit starts. Cost: none.
- `docs/build/wiring.md` called one pack per Shield a planned edit, which #51 drops (electrical); #616 made it one pack and the Y lead. Cost: none left.

## Mechanism

### Neck, head mass and the base candidates

- **A big head on the stock low tilt pivot eats the torque budget.** A 450 g head with its CoM 80 mm above the pivot needs 0.40 kgf·cm at 20° tilt through the 3.1× tilt linkage: the whole rated figure (mechanical [I]). Steady holds belong against the rated 0.4 kgf·cm, gravity plus inertia peaks against stall/2 = 0.5 kgf·cm (mechanical [I]). Cost: model work.
- **Put the head's CoM on the tilt axis.** Three notes agree: it removes the gravity load (mechanical [FBL][I]), drops hold current from about 20× standby towards the 8 mA standby (motion-control [PG][I], electrical [PG][MC]), and cures hunting at rest (motion-control [M5][I]). In candidate (a) the boards sit behind the tilt axis as counterweight; otherwise the model raises the tilt pivot towards the head's CoM (mechanical [I], motion-control [I]). Mechanical [I] keeps a small gravity bias to preload backlash; motion-control [I] instead approaches every rest target from the same side. Cost: model work; no parts.
- **Spring balancing does not fit #51.** A zero-free-length spring balances exactly for one mass only (mechanical [FBL][FW]), so Morty and Bart's different shell masses break it, and it is a second purchase (mechanical). Cost: n/a.
- **Keep the stock load path.** The head rides on its own pivots and the servos drive through bars, so splines carry torque only; never seat the head on a horn (mechanical [I]). Pan on the body with tilt carried on it is in [BOS]'s description only; its live claims are a method the noggin service does not perform (patents [BOS][I]). The PG001's own slip clutch already does what a held-head clutch does (patents [HCL]). Cost: none.
- **Candidate (a) against (b) is a trade.** (a) adds board mass to the moving head and helps only if the boards counterweight (mechanical [I]). (b) puts five servo leads (15 conductors) across both axes, against one power pair plus the pan (maybe tilt) lead for (a) (electrical [I]). (b)'s tower stands in the head's sweep and needs its own sway-mode check (motion-control [I]). Cost: model work.
- **Optimise each candidate before ranking it.** Design methods split a discrete choice from a continuous optimisation of pin positions (graphics [TH14][CO13]); link lengths alone cut a quadruped's peak servo torque by 32% on hardware (simulation [HA]), likely more than the gap between (a) and (b) (simulation [I]). MjSpec stays editable after compiling, so two to five parameters per candidate become arguments and `model/mujoco_report.py` the objective (simulation [MJE][I]); derivative-free search such as CMA-ES or Nelder–Mead (graphics [TH14][I]). Cost: model work, run in CI.
- **The model's servo sets its own peaks.** `model/mjcf.py` slews at the no-load 428 °/s and clips a stiff P at stall, so peak torque and acceleration read from it come from the clip (simulation [I]). A constraint-style position servo diverged from hardware until replaced by a DC motor plus the servo's PD and latency (simulation [TAN]). MuJoCo 3.17 ships this as `dcmotor` with `delay`; for the PG001 at 4.8 V, `nominal = "4.8 0.098 7.48"` and `delay` 0.02 s (simulation [MJX][MJC][I]). Its back-EMF term flatters a voltage H-bridge servo at speed (simulation [MJX][I]). Cost: model work.
- **Identify one PG001 once.** Film a marked horn in phone slow motion with two known loads and fit with `mujoco.sysid` (simulation [MJS][HWG]); RC servo dynamics change with load (simulation [HWG]). Find the lowest mode the same way at 240 fps (motion-control [I]). Expect the Mech to fall about 20% short of the sim (graphics [ME15]). Cost: a phone video and model work; no parts.
- **Gates, not rankings.** Transmission angle ≥ 40° over each linkage's travel stays (mechanical [BC]). Add the smallest singular value of the loop-constraint Jacobian over each joint's range as a singularity margin; the stock pan four-bar already toggles at −43.4° (graphics [TH14][BA15]). Cost: model work.
- **Lowest mode and rest torque as ranking criteria.** Printed parts barely damp (PETG ζ 0.0037, PLA 0.0068) (motion-control [Dr]); a low mode rings through whole gestures. Proposed: gravity torque at rest ≈ 0, and a lowest mode of about ≥ 8 Hz so a 250 ms head move spans two periods (motion-control [I]). Mechanical [I] scores both candidates on m·H and inertia. Cost: model work (compliant printed joints in MuJoCo).
- **Tip-over needs a dynamic term.** The static margin ignores CoM height; the force-angle measure counts inertial forces (mechanical [PR]). Shift the CoM by h·a/g at the gestures' peak accelerations; keep the pack as low as the shirt allows (mechanical [I]). Cost: model work.
- **Leads across pan and tilt.** Split the Y lead after the joint so one pair crosses; keep solder joints and splices out of the flexing span; clamp each span at its two ends only (electrical [N][L]). Bend radius ≥ 10 × lead OD (electrical [N]); larger radius, longer life (electrical [IPC]). Pan: leads along the axis as twist; tilt: a breathing loop; no slip ring (electrical [I]). Cost: none.
- **Antenna in the cranium.** Keep 15 mm clear around the antenna (electrical [HDG]). A 2 mm PLA wall costs about 0.01 dB (electrical [CA][I]); the risk is servos, the pack, leads and the nickel-plated magnets in the zone, and black PETG if its pigment is carbon (electrical [CA][I]). Check RSSI with the shell on (electrical [HDG]). Cost: none.
- **Head proportions.** Baby schema (round face, high forehead, large eyes, small nose and mouth) raises cuteness (perception [G]); cuteness falls as head shape ages (perception [Al][HB]). The cranium electronics should push the forehead up, not the eyes down (perception [I]). Cost: none.

### Linked eyes and lids

- **Linked eyes are supported by every note that looks.** Hanson's eye frame is #51's gimbal almost exactly, and expired (patents [HAN]; also [WR]). Errors in conjunctive eye movement disturb observers far less than disjunctive ones (simulation [KIS]). No #51 face decision is beaten (perception). Cost: none.
- **Gimbal layout.** A Cardan gimbal with yaw on the outer ring, the pitch push-rod's ball end on the yaw axis, and equal-crank parallelogram tie-bars gives equal yaw at every angle; what remains is the Hooke error, 1.6° at 15° pitch and 25° yaw (mechanical [I]). Place each tie rod's pins where their distance varies least over the (yaw, pitch) grid; the residual is the crosstalk (graphics [TH14][I]). Front-plate sockets can fix each eye's centre (patents [WR]). Cost: CadQuery parts and model work.
- **Hold gaze error to about 2°.** The cone of being looked at is about 8–9° at 1 m (perception [GH]); 1 mm of pupil slip on a 25 mm cap is 2.3° (perception [I]). Gimbal play ≤ ~2° and pupils keyed to ~0.5 mm (perception [GH][I]). Cost: print and model work.
- **Vergence: fixed toe-in, number open.** Kismet and iCub keep vergence (simulation [KIS][FOE]), KASPAR does not (simulation [ADM]); parallel is the stylised default (graphics [PE13]). Proposals differ: optional 0–3° (graphics [I]), 2.9° per eye for 0.6 m (simulation [I]), 1.7° per eye for 1 m, which keeps 0.5–2 m within ±3.5° (perception [LH22][N][I]). At a 25 mm cap the 1.7° is a 0.74 mm inward pupil offset in the cap's seat, with no gimbal change (perception [I]). Never a vergence DOF (graphics [I]). Cost: none.
- **Lids pivot on the gimbal's up/down axis.** Lids on the eye's own axis stay concentric with the eyeball (patents [FUR]); the lid margin moves nearly rigidly (graphics [BE15]); lids must turn about the eye centre to clear the eyeball (mechanical [I]). Lids on a fixed head axis need more travel and an uneven gap (patents [WR][I]). Cost: part design only.
- **Pins, not flexures, for lids and jaw.** Flexures drift, limit range and lack off-axis stiffness (mechanical [HM][T][J]). A flexure is an option only for the eye tie-bar joints (mechanical [I]) or tie-rod ball joints (graphics [ME17]), once PETG's allowable strain is set; [ME17]'s evidence is PolyJet, not FDM PETG (graphics [I]). Mechanical's 1% strain is a placeholder; cams-am [I] gives ≤ ~2% for PETG beams in X-Y. Cost: none.
- **Four-bars by function generation.** Three (servo angle, output angle) pairs fix a four-bar by Freudenstein's equations; this can make lid travel linear in servo angle (the #213 non-linearity) (graphics [CE13]). Cost: model work.
- **No cams.** With one servo per DOF, a cam on a position servo only maps angles; the smoothing law belongs in firmware (cams-am [NO][I]; graphics [I]). Cost: none.

## Skeleton and shells

- **Skeleton constants are PLA, the skeleton is PETG.** `model/beams.py` uses E 3.5 GPa and 50 MPa; PETG HF is 1.81/1.54 GPa and 34/23 MPa (X-Y/Z), so a beam at SF < 4.35 today falls under SF 2 across layers (cams-am [TDS-PH][TDS-LB]). Z costs 0.7–0.9 of X-Y strength and half the elongation (cams-am [TDS-PB][TDS-PH]). Cost: model work.
- **Creep.** PETG under 50% of strength creeps little; above it, unrecovered strain appears (cams-am [ST]). Keep sustained stress (parked loads, magnet pull) under ~1/3 of Z strength, and treat no press fit as permanent (cams-am [ST][I]). Cost: none.
- **Fits need a coupon.** Below a critical designed clearance a printed joint fuses (cams-am [AN]); ISO 286 fits in PLA needed 0.13 mm hole compensation (cams-am [GR]). Cost: one coupon print each in PETG and PLA.
- **Busy pivots on steel.** Play, not wear, is the failure mode at desk loads; a steel shank in a PETG bore with its axis along Z (cams-am [VA][CH][I]). Cost: none if the kit's spare screws serve; otherwise a purchase.
- **Fasteners and snap fits.** Insert walls ≥ 2.4 mm, ≥ 70% local infill (cams-am [KA]); printed threads are weakest (cams-am [TH]); snap-fit beams in X-Y (cams-am [KL][I]). Cost: none.
- **Generate the skeleton from servo enclosures.** A fixed printed enclosure per servo joined by the convex hull of attachment points (graphics [ME15][I]). Cost: CadQuery work.
- **Magnet pull falls fast with gap.** One 4×2 mm N52 pair gives 6.5 N at contact, 3.7 N at 0.4 mm, 2.1 N at 1 mm (mechanical [MP][I]); Magpylib matches the closed-form model and measurement (mechanical [V][MP]). Two 0.2 mm skins cost about 40% of the pull; mount magnets flush in open pockets (mechanical [I]). Size with Magpylib's `getFT`: pull ≥ 2·m·(g + a_peak) (mechanical [MP][I]). Cost: model work; no new magnet size.
- **Shear goes to geometry.** A pair restores only 0.9–1.6 N sideways, then friction; hanging shells are shear-loaded (mechanical [MP][I]). Locate each shell on a three-groove or pin-and-ledge seat with magnet preload covering the overturning moment (mechanical [S]). Flobi's face parts attach by magnet (mechanical [L][2nd]). Cost: part design.
- **Peak acceleration comes from simulated motion.** Light compliant assemblies under fast steps vibrate beyond the commanded curve (graphics [HO19]); the model's current actuator sets peaks by its clip (simulation [I]). Use 5.77·D/T² for minimum-jerk moves and the stall-limited acceleration for steps (motion-control [FH][I]), on `dcmotor` actuators (simulation [TAN][MJX]). A lid cover and a step stop are far below one pair; the head shell is the case to check (mechanical [I]). Cost: model work.
- **Polarity keys the parts.** With one disc everywhere, a left lid cover fits the right arm (patents [I]). One polarity rule for every seat, one reversed magnet where a part must be keyed (mechanical [I]; patents [HMAG], technique only, its claims need a rolling ball robot). Cost: none.
- **Magnets glued, not pressed.** PETG relaxes under constant strain and hole size varies with layer height (cams-am [ST][PO][GR]); adhesive type explains 91.6% of joint strength, MMA best on PETG (cams-am [OZ]). Cost: an adhesive, a purchase unless one is on hand [I].
- **Caps up to touching would rub.** Printed parts err up to 0.75% in X-Y and 1.64% in Z (cams-am [ZF]), ±0.3–0.65 mm on a 40 mm cap; PLA on PLA is the worst pairing (cams-am [I]). Cost: none.
- **Shells as constraints.** Write containment, clearance and magnet-seat alignment as named constraints, checked per character over every pose (graphics [ZA17]). Certify clearance adaptively with `mj_geomDistance`, subdividing where r·|dθ| exceeds the separation (simulation [SSL][MJA]). Cost: model work.
- **Collar over the pan seam.** A neckerchief hides the head-to-body seam over the pan joint (patents [GEM]). #51's collar already does this. Cost: none.
- **Live patents to stay clear of.** No lids moulded into a flexible mask with magnet-coupled drive bands (patents [RBX]); no self-propelled Mech that detects its shell electronically (patents [EVO]); no display in a detachable face (patents [FUH]). #51 as written reads on none (patents [I]). Cost: none.

## Characters

- **Stay stylised and consistent.** The uncanny valley comes from mismatch between realistic and unrealistic features (perception [K][SN][MD]); aim for Mori's first peak (perception [M]). Flat matte PLA, no realistic iris, gloss or lashes (perception [I]). Cost: none.
- **Black on white, never reversed.** White sclera signals gaze (perception [KK]); dark-on-light reads accurately (perception [R]). Small pupils leave much white showing, a fear signal (perception [Wh]). Pupil shape (jagged, dots) has no study (perception). Cost: none.
- **Eye size changes natural eye speed.** Large eyes read cross-eyed sooner and want slower, tuned speed (graphics [PE13]). Eye width W = cap diameter ÷ 25 mm is ≈ 1.6, up to ≈ 2.4 with caps touching (graphics [I]); on a ~150 mm head, touching caps make each eye ~40% of face width, twice the infant extreme, fine on a stylised face (perception [G][I]). Cost: one parameter per character.
- **Each character is its own load case.** Run the torque check per character's shell set (mechanical [I]); a spring balance fails across two masses (mechanical [FBL]). Cost: model runs.
- **Character choice by settings.** Picking the character in the noggin service's settings reads on no live patent (patents [EVO][FUH][I]). A key pattern read by the base is expired art if shells are ever auto-detected (patents [SONY]). Cost: none.

## Gestures

- **Lids follow eye pitch, in software.** Lids follow vertical eye rotation in "lid saccades" (graphics [RU14][ST10]); lids tracking elevation lowered gaze-reading errors on iCub (simulation [FOE]). Five notes agree it costs one line, `lid = rest + k·pitch`, keeps the wink, and needs no mechanism (graphics [I], cams-am [I], patents [FUR][I], simulation [I], perception [I]). Each lid servo's range must cover closure plus tracked elevation, checked over the pitch × lid grid (simulation [I]). Cost: code; model work.
- **Smooth trajectories in firmware.** Minimum jerk leaves under 3% residual vibration once T ≥ 2 periods of the lowest mode (motion-control [FH][I]); C² splines with an acceleration penalty (graphics [HO19]); continuous position, velocity and acceleration (cams-am [MR][NO]). The `in`/`out` eases end at speed and stay for the lids only (motion-control [I]). Cap acceleration as well as speed (motion-control [PM][I]). Cost: code.
- **Input shaping for low modes.** A ZVD shaper (¼, ½, ¼ at ζ ≈ 0) rounded to 20 ms frames works for modes up to 6–8 Hz; above, lengthen T (motion-control [SS][Mo][I]). One shaper serves every joint (motion-control [SS]). Cost: code.
- **One write per 20 ms frame.** LEDC takes a new duty only on the next PWM cycle; faster setpoints are lost (motion-control [LEDC][I]). Cost: none.
- **Stagger by whole durations.** Two minimum-jerk moves peak at 2.0× current together, 1.42× at 0.3 T apart, 1.95× at half, 1.0× sequential (motion-control [I]). Cost: code.
- **Eye–head coordination.** Shifts above 10–15° recruit the head; eyes lead by 20–50 ms on a reaction, the head by ~100 ms on a predictable target (graphics [RU14]). Eyes counter-rotate as the head arrives (simulation [AND][KIS]). The eyes and neck sit on different Cores over Wi-Fi, so simulate with a per-Core `delay` (simulation [MJX][I]). Run eye saccades at full speed when the neck is still, down to 1/3 when it carries the shift, and cover the counter-rotation with a gaze-evoked blink (graphics [PE13]). Cost: code; model work.
- **Engagement needs the neck.** Prolonged fixation with the head oriented reads as engagement; eyes flicking without rest as low engagement (simulation [KIS]). Layer saccades, blinks, breathing and small head motions under gaze states (simulation [PAN]). Cost: code.
- **Blinks carry meaning.** 18/min read friendliest, 9/min intelligent, 36/min inactive (perception [Ta]); a ~600 ms blink reads as "got it" (perception [Hö]). Cost: code.
- **Lid level is the strongest eye cue.** Widening reads as interest or awe, narrowing as suspicion (perception [LA]). Rest lid at or just over the top of the pupil; show white above it only for eureka and attention (perception [LA][Wh][I]). Cost: code.
- **Anticipation buys appeal, not legibility.** A visible forethought raised appeal on a robot; a reaction made it seem smarter; neither raised reading accuracy (perception [TDJ]). Scale intensity by amplitude, not by slowing (perception [M][I]). Cost: code.
- **Look at the user or far away.** Linked eyes cannot convincingly fixate nearer than ~0.5 m (perception [LH22][I]). Cost: none.
- **Holding and releasing.** Approach rest from one side; do slow drift as small hops, since moves under one deadband per frame (~25 °/s at a 0.5° guess) step visibly (motion-control [M5][I]). Release (`deinit`) only for long idles; re-attach one servo at a time about 100 ms apart, because re-attach is a step (motion-control [LEDC][M5][I]). Cost: code.
- **Idle life as software.** Periodic time-warps and integer-frequency loops carry over from cam design as code (graphics [CO13][CE13][I]); the keyframe table is the cam stack, and life comes from secondary motion (cams-am [FI][LH][I]). Cost: code.
- Outside #51: a blink every 3–6 s at Rest, against the glossary's still Rest; Cansin's call (perception [Ta]).

## Changes to #51

The fixed limits: (a) the electronics and servos #51 lists, and only what we own ("the one new purchase: magnets"); (b) nothing imported from other people's part designs; (c) PLA Pure in #51's four colours for cosmetics, black PETG for the skeleton; (d) the characters Morty and Bart. Every change below stays inside them. Gestures is not yet a section of #51; changes under it would add one.

- Hardware: drop the low-battery park, since no Core can read the pack voltage within #51's parts (electrical [DS][HDG]).
- Hardware: replace "runs to the pack's 5.8 V cutoff" with an accepted hard cut on loaded voltage near empty (electrical [C][BQ]).
- Hardware: the noggin service detects a pack cut from both Cores' uptimes resetting together and shows it in `noggin status` (electrical [MP][I]).
- Hardware: one pack holds only under a start budget, at most two saturating steps per Core, sized on an empty pack (electrical [C][I], motion-control [PG][I]).
- Hardware: `model/electrical.py` models pack resistance as a function of charge and the cutoff as a loaded-voltage event (electrical [C][BQ]).
- Hardware: one USB cable at a time while both Cores are on the pack (electrical [I]).
- Mechanism: "our neck and jaw as built" keeps linkages and load path, but the tilt pivot moves towards the head's CoM or the layout puts the CoM on it (mechanical [FBL][I], motion-control [I]).
- Mechanism: "servo torque (SF 2 incl. dynamic)" means MuJoCo inverse dynamics along every gesture per character, hold ≤ rated 0.4 kgf·cm, peaks ≤ stall/2 (mechanical [I]).
- Mechanism: the model's servos are `dcmotor` actuators with a 20 ms `delay`, fitted to one filmed PG001 (simulation [TAN][MJX][MJS]).
- Mechanism: each candidate's pins and parameters are optimised before the ranking runs (graphics [TH14][CO13], simulation [HA][MJE]).
- Mechanism: pass/fail gates before ranking: singularity margin (graphics [TH14][BA15]) and gaze error ≤ 2° including play and pupil seating (perception [GH][I]).
- Mechanism: two ranking criteria after torque: gravity torque at rest ≈ 0, and a lowest mode ≥ ~8 Hz, with (b)'s tower checked for sway (motion-control [Dr][I]).
- Mechanism: tip-over margin includes the dynamic CoM shift at peak acceleration; the pack sits as low as the shirt allows (mechanical [PR][I]).
- Mechanism: the Y lead splits after the joint; flexing spans clamped at both ends, bend radius ≥ 10 × OD, no slip ring (electrical [N][L][I]).
- Mechanism: the Core's antenna sits 15 mm clear of shell, servos, magnets, pack and leads, checked by RSSI with the shell on (electrical [HDG]).
- Mechanism: the cranium electronics raise the forehead, not lower the eyes (perception [G][Al][I]).
- Mechanism: the eye gimbal has yaw on the outer ring, the pitch rod's ball end on the yaw axis, and parallelogram tie-bars; the model reports vergence error and crosstalk (mechanical [I], graphics [TH14]).
- Mechanism: a fixed toe-in, its viewing distance (0.6 or 1 m) Cansin's choice, in the gimbal or the caps' pupil seats (perception [LH22][I], simulation [KIS][I]).
- Mechanism: the lid arms pivot coaxially with the gimbal's up/down axis (patents [FUR], mechanical [I]).
- Skeleton and shells: the model reads skeleton constants from the PETG TDS, Z values by default, and records the spool's variant (cams-am [TDS-PH]).
- Skeleton and shells: sustained stress stays under ~1/3 of PETG's Z strength (cams-am [ST][I]).
- Skeleton and shells: busy pivots get a steel shank from the kit's spare screws in a PETG bore along Z (cams-am [VA][CH][I]).
- Skeleton and shells: magnet pull is computed with Magpylib at the as-printed gap; magnets sit flush in open pockets (mechanical [MP][I]).
- Skeleton and shells: each shell locates on a kinematic seat that takes shear, with magnet preload (mechanical [S]).
- Skeleton and shells: the magnet check's peak acceleration comes from the simulated motion, not the commanded curve (graphics [HO19], simulation [TAN], motion-control [FH][I]).
- Skeleton and shells: one polarity rule, with a reversed magnet to key parts that must not swap (mechanical [I], patents [HMAG][I]).
- Skeleton and shells: pupils keyed to ~0.5 mm, not held by magnets alone (perception [GH][I]).
- Skeleton and shells: eyeball caps grow up to a gap of ≥ 1 mm at every pose, not up to touching (cams-am [ZF][I]).
- Skeleton and shells: shell containment, clearance and seat alignment are named constraints checked per character, clearance certified adaptively (graphics [ZA17], simulation [SSL][MJA]).
- Characters: both stay flat matte and stylised, with no realistic iris, gloss or lashes (perception [MD][SN][M]).
- Characters: a gaze-speed parameter per character, derived from cap size (graphics [PE13]).
- Characters: the character is chosen in the noggin service's settings, not detected from the shell (patents [EVO][I]).
- Gestures: lids follow eye pitch in software, `lid = rest + k·pitch`; lid servo ranges cover closure plus tracking (graphics [RU14], simulation [FOE][I]).
- Gestures: head and gimbal moves use minimum jerk with T ≥ 2 periods of the lowest mode and an acceleration cap (motion-control [FH][PM][I]).
- Gestures: eye–head coordination: neck above ~15°, eyes counter-rotating as it arrives, eyes slower when the head carries the shift (graphics [RU14][PE13], simulation [AND]).
- Gestures: rest lid just over the pupil; blinks near 18/min engaged and 9/min thinking; a ~600 ms blink as the "got it" beat (perception [LA][Ta][Hö]).
- Before any build: a clearance coupon in PETG and PLA Pure, pins stepped 0.05 mm from 0.1 to 0.4 mm per side (cams-am [AN][GR]).
- Before any build: film one PG001 with two known loads and fit its model with `mujoco.sysid` (simulation [MJS][HWG]).

## Out of bounds

- A pack-voltage divider (two resistors and 100 nF) for a low-battery park: breaks (a), parts #51 does not own (electrical [DS][HDG]).
- A spring to balance the head: breaks (a), a second purchase, and exact for one shell mass only (mechanical [FBL]).
- A spring to bias the jaw closed or preload a held joint: breaks (a), a second purchase (patents [PD], motion-control [I]).
- Steel pins or rod for the busy pivots if the kit's screws do not fit: breaks (a) (cams-am [VA][I]).
- An adhesive for the magnet pockets, unless one is on hand: breaks (a) (cams-am [OZ]; the purchase is [I]).
- PTFE grease or PTFE plugs on the pivots: break (a), a purchase (cams-am [VA][I]).

Not proposed by any note, so not listed: a vergence servo, a slip ring, a bulk capacitor, imported part designs, other materials or colours, other characters.
