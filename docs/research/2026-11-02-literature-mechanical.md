# Mechanical engineering for the next Mech: linkages, the neck, flexures, magnets, tip-over

Researched 2026-11-02. Purpose: test #51's mechanism decisions against the mechanical-engineering literature, inside the fixed limits: seven PG001 servos, two Cores and Shields, one 2S pack, no imported part designs, PLA Pure cosmetics and black PETG skeleton, Morty and Bart as magnet-held shells on one skeleton.

Builds on `2026-10-31-neck.md` (the stock four-bars, the 40° rule, the 0.47 pan and 0.32 tilt gains), `2026-10-31-shafts.md`, `2026-10-31-electrical.md` (PG001: stall ≥1.0 kgf·cm at 4.8 V, 0.14 s/60°), `model/beams.py` (SF 2 on stall force) and `model/mujoco_report.py` (holding force, static CoM margin). None of that is repeated here.

Sources:
- [FW] French & Widden 2000, "The spring-and-lever balancing mechanism, George Carwardine and the Anglepoise lamp", Proc. IMechE C 214:501. Full text: https://eprints.lancs.ac.uk/id/eprint/20295/1/20295.pdf
- [FBL] Franchetti, Boschetti & Lenzo 2021, "Passive gravity balancing with a self-regulating mechanism for variable payload", Machines 9:145, CC BY. https://doi.org/10.3390/machines9080145 (full text: https://shura.shu.ac.uk/28896/)
- [V] Vokoun, Beleggia, Heller & Šittner 2009, "Magnetostatic interactions and forces between cylindrical permanent magnets", J. Magn. Magn. Mater. 321:3758. https://doi.org/10.1016/j.jmmm.2009.07.030 (author copy: https://jontalle.web.engr.illinois.edu/Public/Allen/Noori-pdf/VokounBeleggiaHellerSittner.09.pdf)
- [MP] Magpylib 6.1.0, `getFT` force and torque (open-source, BSD). https://magpylib.readthedocs.io/en/5.2.1/_pages/user_guide/docs/docs_forcecomp.html
- [S] Slocum 2010, "Kinematic couplings: a review of design principles and applications", Int. J. Machine Tools & Manufacture 50:310. Author's manuscript: https://dspace.mit.edu/handle/1721.1/69013
- [L] Lütkebohle et al. 2010, "The Bielefeld anthropomorphic robot head Flobi", ICRA, 3384–3391 [A]. https://pub.uni-bielefeld.de/record/1991980. Magnet details come only from IEEE Spectrum's report (https://spectrum.ieee.org/robot-head-flobi-designed-to-dodge-uncanny-valley) [2nd].
- [J] Jacobsen, Chen, Howell & Magleby 2009, "Lamina emergent torsional (LET) joint", Mech. Mach. Theory 44:2098 [A]. https://doi.org/10.1016/j.mechmachtheory.2009.05.015
- [T] Trease, Moon & Kota 2005, "Design of large-displacement compliant joints", J. Mech. Des. 127:788 [A]. https://doi.org/10.1115/1.1900149
- [HM] Howell & Midha 1994, "A method for the design of compliant mechanisms with small-length flexural pivots", J. Mech. Des. 116:280 [A]. https://doi.org/10.1115/1.2919359
- [BC] Balli & Chand 2002, "Transmission angle in mechanisms", Mech. Mach. Theory 37:175 [A]. https://doi.org/10.1016/S0094-114X(01)00067-2
- [PR] Papadopoulos & Rey 1996, "A new measure of tipover stability margin for mobile manipulators", ICRA, 3111–3116 [A]. https://doi.org/10.1109/ROBOT.1996.509185
- [IC] iCub eyes: first-party joint docs, https://icub-tech-iit.github.io/documentation/icub_kinematics/icub-joints/icub-joints; Beira et al., "Design of the robot-cub (iCub) head" [A].
- [SF] "Optimization of a spherical five-bar parallel drive linkage", J. Mech. Des. 116:166 (1994) [A]. https://doi.org/10.1115/1.2919341
- [AE] Gosselin & Hamel 1994, "The Agile Eye", ICRA, 781–787 [A]. Lab page: https://robot.gmc.ulaval.ca/en/research/research-thrusts/parallel-mechanisms/the-agile-eye

Tags: [A] = from the abstract only; [2nd] = secondary report; [I] = my inference or arithmetic.

## 1. Linkages and the servo budget

- **Torque gain:** in an ideal linkage, the output-to-input torque ratio is the inverse of the speed ratio. The stock tilt four-bar turns the head 0.32× the servo angle (`2026-10-31-neck.md`), so it multiplies servo torque about 3.1× and cuts head speed to about 137 °/s; pan is 0.47×, about 2.1× [I]. The ratio follows the transmission angle and drops to zero at the output toggle. Transmission angle is the standard figure of merit for force transfer in 4- to 7-bar linkages, and synthesis with a transmission-angle limit is an established method [BC]. The 40° minimum is already in the repo.
- **What the budget means** [I]:
  - The servo's continuous figure is the rated 0.4 kgf·cm (`model/sim.py`). The peak is stall 1.0 kgf·cm, so SF 2 allows 0.5 kgf·cm (0.049 N·m).
  - A steady gravity hold heats the servo, so judge it against the rated figure. Judge gravity plus inertia peaks against stall/2.
- **Head gravity torque, servo side, through the 3.1× tilt linkage** (m·g·H·sinθ/3.1, where H is the CoM height above the tilt axis) [I]:
  - 350 g, H 60 mm, 20° tilt: 0.23 kgf·cm.
  - 450 g, H 80 mm, 20° tilt: 0.40 kgf·cm, which is the whole rated figure.
  - A big head on the stock low tilt pivot is an inverted pendulum. Its load grows with m·H, not with the shell's look.
- **Dynamic load** [I]: τ = M(q)q̈ + c(q,q̇) + g(q) along each gesture trajectory. MuJoCo's inverse dynamics gives this directly. The static holding force that `mujoco_report.py` measures today leaves out the M·q̈ term. For a 120 mm, 300 g head, I ≈ 7×10⁻⁴ kg·m². A 30° bang-bang move in 0.2 s needs about 0.038 N·m at the head, about 0.012 N·m at the servo: small next to gravity at large H.

## 2. Linked eyes: parallelogram tie-bar against push-rods

- **Parallelogram** [I, planar kinematics]: two equal cranks joined by a tie-bar as long as the crank pivots are far apart give the two eyes exactly equal yaw at every angle.
  - Unequal crank radii or bar length make it a general four-bar. The eyes then converge or diverge by an amount that grows with angle.
  - The model can test the build tolerance as vergence error against yaw.
- **Gimbal coupling** [I]:
  - In a Cardan gimbal with yaw outer (on the frame) and pitch inner, a yaw push-rod on the outer ring cannot change pitch.
  - A pitch push-rod from a frame-fixed servo couples to yaw unless its ball end lies on the yaw axis. Put the pitch lever along the yaw axis below or above the eye centre, and the push-rod runs fore-aft.
  - What remains is second-order, the Hooke-joint form: sin θ′ ≈ sin θ / cos ψ. At 15° pitch and 25° yaw that is 16.6°, an error of 1.6°.
- **What others do:**
  - iCub drives both eyes' tilt from one common joint, with pan per eye [IC].
  - A spherical five-bar or 3-RRR spherical parallel mechanism points from ground-fixed actuators. The Agile Eye covers a 140° cone at over 1000 °/s [SF][AE].
  - Both are heavier than two push-rods on a Cardan gimbal. For two 9 g servos the gimbal is the simplest [I].

## 3. Neck under a heavy head

- **Load path** [I]: the PG001 has no published radial or thrust rating (`2026-10-31-electrical.md`). The stock neck already puts the head on its own pivots (the upright on the pan boss, the tilt arm on the upright's pins) and drives them through bars, so the splines carry only torque. Keep that pattern. Never seat the head on a horn.
- **Spring balancing:**
  - A zero-free-length spring between a frame point at distance a and a link point at distance b balances a pendulum exactly when m·c·g = k·a·b, at every angle [FBL eq. 2][FW]. A close-coiled spring with initial tension gives an effectively zero free length [FW].
  - The balance holds for one mass only. When the payload changes, the system is no longer in indifferent equilibrium [FBL]. Morty and Bart shells differ in mass, so a spring tuned for one is off for the other.
  - A spring would also be a second purchase, and #51 allows only magnets.
- **Mass placement:**
  - Balancing removes the gravity load from the actuator, leaving only inertia, which allows a smaller actuator [FBL §1].
  - The no-purchase route is mass placement. Put the head's CoM on the tilt axis, using the boards as the counterweight in candidate (a). Or put the tilt axis through the head's CoM [I].
- **Backlash** [I]: with the CoM exactly on the axis, nothing holds the gears on one flank, so gear backlash and pin clearance show as wobble. A small deliberate gravity bias, well inside the budget, preloads them. One linkage per axis with tight pins beats stacked joints.

## 4. Flexures for lids and jaw

- **What the literature says about flexures:**
  - A small-length flexural pivot behaves as a pin with a torsion spring (pseudo-rigid-body model) [HM].
  - Common flexure joints have limited range, axis drift and low off-axis stiffness [T].
  - LET joints reach large rotations where off-axis stiffness matters less [J].
- **Strain limit** [I, Euler–Bernoulli]: in a uniform flexure bent through θ over length L, the peak strain is ε = θ·t/(2L), where t is the thickness. At 1% allowable strain:
  - 0.4 mm thick, 44° (±22° eye yaw): L ≈ 15 mm.
  - 0.6 mm thick, 58° (jaw): L ≈ 30 mm.
  - 0.6 mm thick, 80° (lid): L ≈ 42 mm.
  - The allowable strain for printed PETG is the materials agent's to set.
- **Verdict** [I]: lids must turn about the eye centre to clear the eyeball, and the jaw needs a fixed hinge. The axis drift and length make flexures worse than pins for both.
- **Where a flexure could fit:** the four joints of the eye tie-bar parallelogram, which turn about ±22°. They would remove backlash at the cost of a return torque the servo must carry. At t 0.4, b 4, L 7.7 mm and E ≈ 2 GPa, that is about 0.09 kgf·cm total.

## 5. Magnets

- **Pull and gap:**
  - Measured contact forces match the closed-form cylinder model within about 5%, and within 1% at gaps that are not small [V].
  - Between two coaxial magnets, force falls as 1/x⁴ in the far field [V].
  - Magpylib reproduces [V]: for 3 mm × 3 mm magnets at 0.859 MA/m it gives 2.74 N against 2.63 measured and 2.76 from [V]'s formula. That check, and the numbers below, are my runs (meshing converged to 0.05 N).
- **Magpylib, one coaxial pair of 4×2 mm N52, J = 1.44 T (the grade's nominal, inferred)** [MP][I]:

| gap mm | 0 | 0.2 | 0.4 | 0.6 | 0.8 | 1.0 | 1.5 | 2.0 |
|---|---|---|---|---|---|---|---|---|
| pull N | 6.5 | 4.7 | 3.7 | 3.0 | 2.5 | 2.1 | 1.4 | 1.0 |

  - A printed skin over each magnet (two skins of 0.2 mm, so a 0.4 mm gap) costs about 40% of the pull.
- **Shear:**
  - At a 0.4 mm gap, a 0.5, 1 and 2 mm sideways offset gives restoring forces of only 0.9, 1.4 and 1.6 N [MP][I].
  - Beyond that, shear is friction, μ·F_pull. A shell hanging on a vertical face is shear-loaded.
- **Locate with geometry, hold with magnets:**
  - Exact-constraint design uses as many contact points as degrees of freedom to constrain. Over-constrained fits need clearance, which limits repeatability [S].
  - A three-groove kinematic coupling locates a part on six contacts. For lightly loaded systems, magnets can be the preload [S].
  - Without enough preload, external loads can tip the coupling [S]. The preload must exceed the overturning moment from the part's weight plus its peak acceleration.
- **Precedent:** Flobi's exterior is "fully modular and replaceable" [L][A]. Its face parts attach to the frame with magnets, and its lips are magnet-coupled to slides under the mask [2nd].
- **Peak acceleration** [I]: a lid cover on a 40° bell blink in 80 ms at r 15 mm sees about 8 m/s². A step stop at 428 °/s within about 5 ms gives about 2 g. For a 2 g cover, both are far below one pair. The head shell (tens of grams, on pan and tilt stops) is the case to check.
- **Polarity** [I]: one rule everywhere (for example, skeleton faces north out) lets any shell fit any skeleton seat. One reversed magnet in a pattern keys a part that must not go on wrong.

## 6. Tip-over

- **What the measures say:**
  - The static margin, the CoM projection inside the footprint (what `mujoco_report.py` measures), ignores CoM height.
  - The force-angle measure takes the net force on the CoM, inertial forces included, against each tipping axis. It is sensitive to CoM height and to how heavy the system is [PR][A].
- **Dynamic shift** [I]: the head's acceleration a moves the effective support point by about (m_head·a·h_head)/(M·g).
- **Where low ballast helps** [I]: a heavy low pack lowers h and dilutes the head's horizontal offset in the combined CoM. On static margin it helps only through that dilution, and on the dynamic shift through both.

## Practices for #51

1. **Torque check per servo** along every gesture trajectory with MuJoCo inverse dynamics. Steady gravity hold ≤ rated 0.4 kgf·cm; gravity plus inertia peak ≤ stall/2 = 0.5 kgf·cm. Run it for each character's shell set (§1).
2. **Bound m·H for the head** (head mass × CoM height above the tilt axis). Aim the CoM at the tilt axis, using the boards as counterweight or putting the tilt axis through the head CoM. Leave a small bias for backlash preload (§1, §3).
3. **Keep the load path:** head on its own pivots, servos driving through bars, splines carrying torque only (§3).
4. **Transmission angle ≥ 40°** over each linkage's whole travel, checked in the model as now (§1).
5. **Linked eyes:** equal-crank parallelogram tie-bars for yaw and for pitch. Yaw on the outer gimbal ring. The pitch rod's ball end on the yaw axis. The model reports vergence error and yaw-pitch coupling over the range (§2).
6. **Pins, not flexures,** for lids and jaw. A flexure parallelogram for the eye tie-bars is an option, after the materials agent sets PETG's allowable strain (§4).
7. **Magnet sizing with Magpylib's `getFT`, not a custom formula** (CLAUDE.md: OSS libraries for numerics). Needed pull ≥ 2 × m·(g + a_peak) in the pull direction. Shear goes to geometry (§5).
8. **Magnets flush in open pockets facing each other,** or skins ≤ 0.2 mm; every 0.2 mm of extra gap costs about 20–30% of the pull (§5).
9. **Each shell locates on a three-groove or pin-and-ledge kinematic seat with magnet preload.** The preload covers the overturning moment at peak acceleration (§5).
10. **One polarity rule across all seats;** a reversed magnet only where a part must be keyed (§5).
11. **Tip-over with a dynamic term:** CoM shifted by h·a/g at the gestures' peak accelerations, not only the static pan × tilt grid; the pack as low as the shirt allows (§6).

## Conflicts with #51

- **#51: "Our neck and jaw as built", with a cartoonishly big head.**
  - Evidence (§1): the stock tilt pivot sits low under the head. A 450 g head with its CoM 80 mm above the pivot uses the whole rated 0.4 kgf·cm at 20° tilt, even through the 3.1× linkage. Balancing literature removes gravity from the actuator rather than sizing for it [FBL].
  - Change: keep the stock linkages, the pivot pattern and the load path, but let the model move the tilt pivot up toward the head's CoM, or require CoM-on-axis by layout. Make "servo torque" in the ranking the inverse-dynamics check in practice 1.
- **#51 ranking, candidate (a) against (b).** Not a conflict, a sharpening.
  - Evidence: (a) adds board mass to the tilted and panned body. It only helps if the boards sit behind the tilt axis as counterweight; otherwise (b), with the boards on a static tower, carries less moving mass [I].
  - Change: score both on m·H and inertia from the model, as in practice 2.
- **#51: "one small disc size everywhere (start 4x2 mm N52) ... the model checks each part holds against its weight and its peak gesture acceleration".**
  - Evidence (§5): the check as written is pull-only. A pair gives at most about 1.6 N sideways from magnetism, and beyond that only friction, while hanging shells are shear-loaded. Pull also halves by about a 0.5 mm gap.
  - Change: add a locating seat per shell to take shear (practice 9), compute pull at the as-printed gap with Magpylib (practices 7 and 8), and fix one polarity rule (practice 10). The disc size can stay.
- **Spring gravity balance: not proposed.** It is exact only for one mass, so two characters break it [FBL], and it would be a second purchase. Mass placement does the job inside #51's limits.

Unverified: Herder's 2001 thesis (TU Delft) could not be reached; [A] sources were read from abstracts only; Flobi's magnet details are second-hand; the 1% PETG strain and J 1.44 T for N52 are placeholders, marked inferred. The 40° transmission-angle floor comes from the textbook convention already cited in `2026-10-31-neck.md`; I found no free primary source for it.
