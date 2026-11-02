# Cams, automata and printed mechanisms for the next Mech

Researched 2026-11-02. Purpose: literature basis for the next Mech's (#51) PETG skeleton and PLA shells: cams and servo-driven coupling, what automata teach, FDM fits, anisotropy, creep, fasteners, magnet pockets, snap fits and printed pivots. Builds on `2026-10-31-filament.md` (PLA Pure colours, density), `2026-10-31-shafts.md` (horn geometry) and `model/beams.py` (beam checks); does not repeat them.

Tags: [A] abstract only (full text not read), [I] my inference. No tag means the source's full text or the cited page was read.

Sources:
- [TDS-PB] Bambu Lab, PETG Basic Technical Data Sheet V2.0. https://cdn.shopify.com/s/files/1/0380/5149/files/Bambu_PETG_Basic_Technical_Data_Sheet.pdf
- [TDS-PH] Bambu Lab, PETG HF Technical Data Sheet. https://cdn.shopify.com/s/files/1/0584/7236/6216/files/Bambu_PETG_HF_Technical_Data_Sheet.pdf
- [TDS-LB] Bambu Lab, PLA Basic Technical Data Sheet V2.0. https://cdn.shopify.com/s/files/1/0380/5149/files/Bambu_PLA_Basic_Technical_Data_Sheet.pdf. The PLA Pure TDS was not found on Bambu's CDN; the only copy is on a retailer's site, which blocked fetching.
- [NO] Norton, *Cam Design and Manufacturing Handbook*, 2nd ed., ch. 18 "Cam design guidelines", p. 551 (page posted by the author). https://designofmachinery.com/wp-content/uploads/2018/11/Ch182edp551.pdf
- [MR] MechRef (University of Illinois course reference), "Cams": the fundamental law of cam design. https://www.mechref.org/md/Cams
- [ZF] Zayas Figueras & Buj-Corral 2023, Micromachines 14:377, PLA FFF vs milled constant-breadth cams. https://doi.org/10.3390/mi14020377
- [FI] The Franklin Institute, "Maillardet's Automaton" (collection page). https://www.fi.edu/en/science-and-education/collection/maillardets-automaton
- [LH] Linda Hall Library, "Scientist of the Day: Pierre Jaquet-Droz". https://www.lindahall.org/about/news/scientist-of-the-day/pierre-jaquet-droz/
- [ST] Stankevics et al. 2025, Polymers 17:2075, viscoelastic creep of FFF PETG. https://doi.org/10.3390/polym17152075
- [AN] Anghel et al. 2021, Processes 9:925, clearance of FDM non-assembly revolute joints. https://doi.org/10.3390/pr9060925
- [GR] Grgić et al. 2023, Processes 11:2810, ISO 286 clearance fits in FDM PLA. https://doi.org/10.3390/pr11102810
- [PO] Popescu et al. 2022, Appl. Sci. 13:41, accuracy of printed holes [A]. https://doi.org/10.3390/app13010041
- [KA] Kastner et al. 2023, J. Manuf. Mater. Process. 7:42, pull-out of metal threaded inserts in FFF parts [A]. https://doi.org/10.3390/jmmp7010042
- [MH] Moritzer & Held 2023, Welding in the World 67:2835, direct screwing into AM screw bosses [A]. https://doi.org/10.1007/s40194-023-01610-7
- [TH] Polymers 2025, 18:112, M8 printed threads vs heat-set inserts vs Helicoil in SLS PA12. https://doi.org/10.3390/polym18010112
- [KL] Klahn, Singer & Meboldt 2016, Procedia CIRP 50:264, snap fits for FDM and SLS [A]. https://doi.org/10.1016/j.procir.2016.04.130
- [OZ] Öz & Öztürk 2025, Welding in the World, adhesives on PLA, PETG, ABS and ASA [A]. https://doi.org/10.1007/s40194-025-02048-9
- [VA] Vasilev et al. 2026, Tribology and Materials 5:116, FFF PETG on C45 steel, with PTFE inserts. https://doi.org/10.46793/tribomat.2026.013
- [VP] Vaught & Polycarpou 2023, Wear 204736, FFF PETG tribology [A]. The abstract was not retrievable; its numbers come via [VA]. https://doi.org/10.1016/j.wear.2023.204736
- [CH] Chişiu et al. 2021, Materiale Plastice 58(1), friction of printed PLA and ABS vs print direction [A]. https://doi.org/10.37358/mp.21.1.5457

Not reached: Cuellar et al. 2018 (Additive Manufacturing 21:150) and Lussenburg et al. 2021 (Additive Manufacturing 39:101846), the TU Delft reviews of non-assembly mechanisms. The repository refused connections. Chapuis & Droz, *Automata* (1958), is lending-only on archive.org.

## 1. Cams for a position servo

- **The fundamental law of cam design:** follower position, velocity and acceleration must be continuous and jerk finite. Discontinuities excite vibration [MR].
- **Profile laws** [NO, guidelines 2–5]:
  - For rest-to-rest ("double-dwell") moves, the 3-4-5 polynomial or modified sine is the "workhorse".
  - The 4-5-6-7 polynomial vibrates least; the cycloidal law is an acceptable substitute if its higher peak acceleration is tolerable.
  - Motions with specified intermediate positions or velocities call for polynomials or B-splines.
- **Pressure angle** [NO, guideline 6]: about 30° maximum for translating followers (35° on a low-friction ball slide), and about 35° for oscillating-arm followers.
- **Roller followers** [NO, guideline 7]: the pitch curve's radius of curvature must exceed the roller radius everywhere to avoid undercutting. Target ρ/Rf > 2; 1.5 has been used.
- **Flat-faced followers** [NO, guideline 8]: the cam may have no concave (negative-radius) section.
- **Track cams** [NO, guideline 12]: a single roller in a groove has crossover shock and slips at each load reversal. The cures are a spring holding the roller against one side, or two preloaded rollers.
- **A servo-driven cam is not a timing cam** [I]. A classical cam turns at constant speed, so its profile is the motion law. A PG001 position servo sets the timing itself, so a cam on its horn only maps one angle to another. The smoothness law belongs in the firmware trajectory (motion control covers that); the cam profile only needs to be C2 and within the pressure-angle limits.
- **Driving a second feature from one servo** [I]: all seven #51 degrees of freedom have their own servo. A lid that follows eye pitch is therefore a firmware sum (lid command + k·pitch) costing zero parts, and it keeps the wink. A mechanical cam or link from pitch to lids would fight the lid servos.
- **Printed cams** [ZF]:
  - PLA FFF cams matched milled aluminium within 0.75% on dimensions in the print plane (XY), but erred up to 1.64% along Z (across layers).
  - The working face (the side wall) had Ra 10.41 µm, against 0.50 µm milled, at a 0.15 mm layer height. Metal cams want Ra < 0.4 µm.
  - The authors judge printed cams fit only for low-power transmission.
- **Print a cam flat** [I from ZF]: profile in the XY plane, so the profile is traced by the nozzle and not stair-stepped by layers.

## 2. Automata: how natural motion was encoded

- **Maillardet's automaton** (c. 1800) [FI]:
  - Its "memory" is a stack of brass cam discs turned by a clockwork motor.
  - Three steel followers trace the cam edges. Through levers and rods they drive the hand side to side, front to back and up and down: one follower per axis, no follower shared between axes.
  - It holds four drawings and three poems.
  - Its restorer believes the head and eye motions were originally more nuanced.
- **Jaquet-Droz automata** (Neuchâtel, 1768–1774) [LH]:
  - The Writer is programmed by setting input tabs that select the cams moving the pen, up to 40 characters. All gears, cams and followers sit inside the body.
  - The Musician's eyes follow her fingers, and her breast rises and falls while she waits. The Draughtsman pauses to blow charcoal dust from the paper.
- **What carries over** [I]:
  - **The keyframe table is the cam.** With one servo per axis, the Mech's gesture tables play the role of the cam stack. The automata keep axes independent (one follower each) rather than coupling them mechanically, and #51's seven independent servos already do the same.
  - **Life comes from secondary motion:** breathing, gaze following the action, small pauses. These are cheap in firmware and belong to the animation and motion-control notes (`2026-11-01-toon-eyes.md`, `2026-11-02-literature-motion-control.md`).

## 3. FDM materials: anisotropy, heat, creep

### Bambu TDS values

All specimens were printed at 100% infill and annealed and dried for 8 h before testing [TDS-PB, TDS-PH, TDS-LB].

| | E X-Y / Z (MPa) | tensile X-Y / Z (MPa) | elongation X-Y / Z (%) | bend X-Y / Z (MPa) | HDT 1.8 / 0.45 MPa (°C) |
|---|---|---|---|---|---|
| PETG Basic | 1460 / 1120 | 48 / 39 | 11.2 / 5.7 | 81 / 64 | 65 / 69 |
| PETG HF | 1810 / 1540 | 34 / 23 | 8.6 / 5.1 | 64 / 48 | 62 / 69 |
| PLA Basic | 2680 / 2160 | 39 / 35 | 12.2 / 7.5 | 76 / 68 | 54 / 57 |

### What the table means

- **Z costs a lot:** about 0.7–0.9 of the X-Y tensile strength, and about half the elongation.
- **These are best-case values** [I]: 100% infill and annealing. Walls and infill on real parts do worse.
- **Transverse to the raster:** with every raster in one direction and no walls, PETG gave 50.4 MPa along the raster and 22.5 MPa across it (E 2.33 vs 2.19 GPa) [ST].
- **Oil and grease:** both TDSs rate PETG and PLA "resistant to most kinds of oil and grease" [TDS-PB, TDS-LB].
- **PETG creep** [ST], measured at 21 °C:
  - Below 50% of strength, creep added up to 1% strain (X) or 0.6% (Y) in 5 h.
  - At 50% of strength, creep was about 5% of the elastic strain in 5 h and doubled by 20 h.
  - At 70%, it reached 25% of the elastic strain (X).
  - Plastic, unrecovered strain appears once creep exceeds 0.1% (X) or 0.05% (Y), which happened above 50% of strength.
  - One relaxation spectrum fitted both directions, so anisotropy enters through the moduli only.
- **Constant strain relaxes too** [I from ST]: an interference fit in PETG is constant strain, so its grip relaxes over time. A press fit is not a permanent retainer.

## 4. Fits, clearances, fasteners, magnets, snap fits

- **Clearances in non-assembly revolute joints** [AN]:
  - Literature values: 0.2 mm (PolyJet), 0.2 and 0.05 mm (FDM, the latter with shape changes), 0.4 mm (Stratasys F370 FDM).
  - The measured clearance is zero (fused) below a critical designed clearance, then follows it once large enough.
  - So every printer and material pair needs its own test coupon [I].
- **Hitting ISO 286 clearance fits** in PLA (0.4 mm nozzle, 0.1 mm layers) needed a 0.13 mm hole horizontal expansion in the slicer [GR].
- **Hole accuracy** depends most on layer height, then on the number of shells around the hole [PO, A].
- **Threaded inserts** [KA, A]: pull-out depends most on infill in the joining zone, which should be ≥70%. Walls around the pre-hole need ≥2.4 mm for the insert they tested; thicker walls did not help.
- **Printed thread vs inserts** [TH], M8 in SLS PA12: the printed thread failed at 3.41 kN, a heat-set insert at 3.83 kN (+12%), a Helicoil at 4.78 kN (+40%). Heat-set insertion bulges material at the top face. The authors limit printed threads to large sizes and low loads. Transfer to FDM PETG is [I].
- **Direct screwing** [MH, A]: AM screw bosses built to injection-moulding guidelines differ significantly with build orientation and process.
- **Adhesives** [OZ, A]: the adhesive type explains 91.6% of joint-strength variance and the substrate only 5.3%. PETG bonded best with a methyl methacrylate adhesive; PLA did best with PU, epoxy and acrylate.
- **Snap fits** [KL, A]: the injection-moulding working principles hold for FDM. The guidelines must add FDM's restrictions, notably the beam's orientation to the build direction.
- **Snap-fit strain** [I from the TDS]: Z elongation is about half of X-Y. A snap beam should lie in the X-Y plane, along its length, with a design strain well under the Z elongation (≤ ~2% for PETG).

## 5. Printed pivots: friction and wear

- **PETG on steel, dry:**
  - Unfilled FFF PETG on hardened C45 steel (Ra 0.06–0.08 µm, 0.64–1.91 MPa, 0.2 m/s) gave COF 0.57–0.64 [VA].
  - Vaught & Polycarpou measured a steady COF of 0.34–0.44, highest on vertically printed specimens, where layer interfaces are exposed [VP via VA].
- **Adding PTFE:** press-fit PTFE plugs covering 30–40% of the face cut COF to 0.18–0.24 and mass loss by up to 76% [VA].
- **Print direction:** sliding across the rasters gives a higher COF than sliding along them, for PLA and ABS; COF rises with load and speed [CH, A].
- **What this means for the Mech** [I]:
  - **Our pivots run far gentler than these tests.** A ~0.5 N eye load on a 3 × 3 mm projected bearing is about 0.06 MPa. Even the 9.2 N stall force at the 12.75 mm horn pin (beams.py) on a 2 × 3 mm pin is only ~1.5 MPa, briefly.
  - **Play, not wear, is the failure mode:** wear is not the life limit at desk duty; the fit clearance the print needs is.
  - **Use metal shafts on busy joints:** a steel shank in a printed bore avoids the weak polymer-on-polymer and across-layer contact.
  - **Orient the bore axis along Z:** the shaft then slides along the perimeter lines, not across layers.

## Practices for #51

1. Put any smoothing law (3-4-5 or 4-5-6-7 polynomial, or cycloidal, rest to rest) into the firmware trajectory, not into a printed cam. A cam on a position servo only maps angles [NO, I].
2. Use no cam or link to couple lids to eye pitch. Add k·pitch to each lid command in firmware, which keeps the wink and adds no parts [I].
3. If a cam is used anyway:
   - keep the pressure angle ≤30° (translating follower) or ≤35° (oscillating arm);
   - keep ρ/Rf > 2 for a roller follower, and no concave flank for a flat follower [NO];
   - print it flat, with the profile in X-Y [ZF].
4. Size every skeleton beam with PETG Z-direction values: worst case PETG HF, E 1.54 GPa and 23 MPa tensile [TDS-PH]. Use X-Y values only where the bending stress runs along the layers, and confirm which PETG is on the spool.
5. Keep sustained stress (parked loads, magnet pull, preloads) under ~1/3 of the Z strength: ≤ ~8 MPa for PETG HF, ≤ ~13 MPa for PETG Basic [I from ST: plastic creep above 50%].
6. Retain magnets with adhesive, not by interference alone. PETG relaxes under constant strain [ST, I], and hole size varies with layer height and shell count [PO, GR]. Pick the adhesive by test: an MMA adhesive bonded PETG best [OZ, A].
7. Print a clearance coupon on the Bambu (0.4 mm nozzle; PETG and PLA Pure) before fixing fits. Step pins in 0.05 mm from 0.1 to 0.4 mm per side, because below a critical clearance the joint fuses [AN]. Hold holes to the slicer's hole compensation [GR].
8. Busy pivots (eye gimbal axes, lid arms, jaw) get a steel shaft, such as a smooth screw shank, in a printed PETG bore with its axis along Z. Printed-on-printed bearings are only for rarely moving joints [VA, CH, I].
9. Give screw bosses and insert holes ≥2.4 mm wall and ≥70% local infill [KA, A]. Self-tapping kit screws are enough at these loads; printed threads are the weakest option [TH, I].
10. Lay snap-fit and flexure beams in X-Y with strain ≤ ~2% (PETG), never bending across layers [KL, TDS, I].
11. Grease is permitted on PETG and PLA [TDS-PB, TDS-LB]. A drop of PTFE grease on the steel-in-PETG pivots attacks the 0.34–0.64 dry COF [VA, VP, I].

## Conflicts with #51

1. **The SF 2 checks assume PLA, but the skeleton is PETG.**
   - #51 ranks candidates on servo torque at SF 2 and has the model check that every part holds.
   - `model/beams.py` uses E 3.5 GPa and yield 50 MPa (PLA). Bambu's own PLA Basic TDS gives 2.68 GPa and 39 MPa X-Y. PETG HF gives 1.81/1.54 GPa and 34/23 MPa (X-Y/Z); PETG Basic gives 1.46/1.12 GPa and 48/39 MPa.
   - With PETG HF across layers, a beam showing SF < 4.35 today falls below SF 2, and deflections grow 1.9–3.1×.
   - **Change:** the #51 model reads skeleton constants from the PETG TDS (Z values by default), and the spool's PETG variant is recorded.
2. **Eyeball caps "may grow up to touching".**
   - Printed parts err up to 0.75% in X-Y and 1.64% in Z [ZF]. On a ~40 mm cap that is ±0.3–0.65 mm, before magnet-seat play.
   - Touching PLA caps on linked eyes would rub, and PLA-on-PLA dry contact is the worst pairing of all those above.
   - **Change:** "up to a gap of ≥1 mm between caps at every pose" [I], checked in the model like the other collisions.
3. **"The one new purchase: magnets" (conditional).**
   - Practice 8 wants steel shafts at the busy pivots. If the kit's spare screws cannot serve as smooth shanks of the right length, that needs a second small purchase (steel pins or rod). This is within the fixed limits; the hardware list is not fixed.
   - **Change:** allow steel pins if the kit's screws do not fit.
