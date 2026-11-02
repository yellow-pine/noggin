# Computational design of mechanical characters, and stylised gaze, for the next Mech

Researched 2026-11-02. Purpose: the computer-graphics literature that bears on #51. It covers mechanisms designed from motion (the Coros 2013 line) and how they could run in our model (CadQuery parts, MuJoCo). It also covers procedural gaze and eyelid models, only where they add to `2026-10-31-natural-eye-motion.md` and `2026-11-01-blink-kinematics.md`.

Every source below was read in full text unless tagged [A] (abstract only). [I] marks my inference. "Via [X]" means the claim is cited second-hand from X.

Sources:
- [CO13] Coros, Thomaszewski, Noris, Sueda, Forberg, Sumner, Matusik, Bickel. Computational Design of Mechanical Characters. SIGGRAPH 2013. https://doi.org/10.1145/2461912.2461953 . PDF: https://s3-us-west-1.amazonaws.com/disneyresearch/wp-content/uploads/20140804211255/CDMC1.pdf
- [ZH12] Zhu, Xu, Snyder, Liu, Wang, Guo. Motion-Guided Mechanical Toy Modeling. SIGGRAPH Asia 2012. https://doi.org/10.1145/2366145.2366146 . PDF: https://www.microsoft.com/en-us/research/wp-content/uploads/2016/12/toy.pdf
- [CE13] Ceylan, Li, Mitra, Agrawala, Pauly. Designing and Fabricating Mechanical Automata from Mocap Sequences. SIGGRAPH Asia 2013. https://doi.org/10.1145/2508363.2508400 . PDF: https://infoscience.epfl.ch/record/195590/files/functional_modeling.pdf
- [TH14] Thomaszewski, Coros, Gauge, Megaro, Grinspun, Gross. Computational Design of Linkage-Based Characters. SIGGRAPH 2014. https://doi.org/10.1145/2601097.2601143 . PDF: https://la.disneyresearch.com/wp-content/uploads/Project_Linkages_Siggraph2014_paper.pdf
- [BA15] Bächer, Coros, Thomaszewski. LinkEdit: Interactive Linkage Editing using Symbolic Kinematics. SIGGRAPH 2015. https://doi.org/10.1145/2766985 . PDF: https://la.disneyresearch.com/wp-content/uploads/LinkEdit-Interactive-Linkage-Editing-using-Symbolic-Kinematics-Paper.pdf
- [BH15] [A] Bharaj, Coros, Thomaszewski, Tompkin, Bickel, Pfister. Computational Design of Walking Automata. SCA 2015. https://doi.org/10.1145/2786784.2786803 (the full text links I found returned 404 or HTML)
- [ME15] Megaro, Thomaszewski, Nitti, Hilliges, Gross, Coros. Interactive Design of 3D-Printable Robotic Creatures. SIGGRAPH Asia 2015. https://doi.org/10.1145/2816795.2818137 . PDF: https://la.disneyresearch.com/wp-content/uploads/Interactive-Design-of-3D-Printable-Robotic-Creatures-Paper.pdf
- [ME17] Megaro, Zehnder, Bächer, Coros, Gross, Thomaszewski. A Computational Design Tool for Compliant Mechanisms. SIGGRAPH 2017. https://doi.org/10.1145/3072959.3073636 . PDF: https://la.disneyresearch.com/wp-content/uploads/A-Computational-Design-Tool-for-Compliant-Mechanisms-Paper1.pdf
- [ZA17] Zhang, Auzinger, Ceylan, Li, Bickel. Functionality-aware Retargeting of Mechanisms to 3D Shapes. SIGGRAPH 2017. https://doi.org/10.1145/3072959.3073710 . PDF: https://research-explorer.ista.ac.at/download/1002/4728/IST-2018-1050-v1%2B1_MechRet.pdf
- [SO17] Song, Wang, Tang, Fu, Xu, Liu, Mitra. Computational Design of Wind-up Toys. SIGGRAPH Asia 2017. https://doi.org/10.1145/3130800.3130808 . PDF: https://sutd-cgl.github.io/supp/Publication/projects/2017-SIGAsia-Wind-upToy/download/paper.lowres.pdf
- [HO19] Hoshyari, Xu, Knoop, Coros, Bächer. Vibration-Minimizing Motion Retargeting for Robotic Characters. SIGGRAPH 2019. https://doi.org/10.1145/3306346.3323034 . PDF: https://la.disneyresearch.com/wp-content/uploads/VibSupPaper_2.pdf
- [RU14] Ruhland, Andrist, Badler, Peters, Badler, Gleicher, Mutlu, McDonnell. Look me in the Eyes (Eurographics 2014 STAR). https://doi.org/10.2312/egst.20141036 . PDF: https://hal.science/hal-01025241/document . It is the earlier version of the CGF 2015 review (https://doi.org/10.1111/cgf.12603), whose full text I could not reach.
- [PE13] Pejsa, Mutlu, Gleicher. Stylized and Performative Gaze for Character Animation. Eurographics 2013, CGF 32(2). https://doi.org/10.1111/cgf.12034 . PDF: https://pages.cs.wisc.edu/~bilge/pubs/2013/EG13-Pejsa.pdf
- [ST10] [A] Steptoe, Oyekoya, Steed. Eyelid kinematics for virtual characters. CAVW 21(3-4) 2010. https://doi.org/10.1002/cav.354
- [BE15] Bermano, Beeler, Kozlov, Bradley, Bickel, Gross. Detailed Spatio-Temporal Reconstruction of Eyelids. SIGGRAPH 2015. https://doi.org/10.1145/2766924 . PDF: https://www.cs.tau.ac.il/~amberman/eyelids_paper.pdf

## 1. Computational design of mechanical characters

### What the line does

All of these papers solve the same problem: one motor (or a few) and a passive mechanism must reproduce a motion that would otherwise need one actuator per degree of freedom.

- **[ZH12] Zhu et al. 2012, motion-guided toys.**
  - Input: the geometry of each feature and its time-varying rotation and translation, plus an "assembly box" under the toy.
  - Parts library: belt-pulleys, gears, crank-sliders, quick-returns, and snail, ellipse and double-ellipse cams.
  - Search: a special initialisation, then simulated annealing over discrete and continuous parameters.
  - Simulation: forward kinematics for the mechanism, then inverse kinematics for the features. That two-stage scheme cannot simulate kinematic loops [CO13 §3].
- **[CO13] Coros et al. 2013, mechanical characters.**
  - Input: an articulated character and user-sketched closed motion curves for chosen points.
  - Library: parameterised driving mechanisms (6–12 parameters each), each type pre-sampled with Poisson-disk sampling in a learned curve-feature metric. The closest curve picks the mechanism type and its initial parameters.
  - Optimisation: BFGS on the integrated marker-to-curve distance (Eq. 2). Gradients come from the implicit function theorem on the assembly constraints, `∂s/∂p = −(∂C/∂s)⁻¹ ∂C/∂p` (a pseudo-inverse when constraints are redundant).
  - Drive: gear trains join all mechanisms to one input. Timing is shaped with non-circular gear pairs whose phase map `f(α)` is a thin-plate RBF through user samples, with `f′` and `f″` periodic.
  - Simulation: constraint-based and kinematic only. Pin, point-on-line, phase and fixed-state connections are solved with Newton on `½CᵀC`. The solver flags over-constraint (non-zero minimum) and under-constraint (singular Hessian).
  - Limits stated by the authors: cyclic motions only, and no forces. Shaft and link thickness were found by trial; torque smoothing is left as future work.
- **[CE13] Ceylan et al. 2013, automata from mocap.**
  - Each bone becomes a module: a four-bar turns the crank's rotation into the bone's oscillation, and gears, pulleys and belts propagate the crank along a chain.
  - Initialisation: each bone's angle is fitted to its strongest Fourier component, `Φ = µ cos(2πf j/n + ρ)`. Three sampled (input, output) angle pairs fix the four-bar's link lengths by Freudenstein's three-precision-point function generation.
  - Refinement: SQP adds a bar-ratio penalty (no very short or long bars) and Grashof constraints, so the crank turns fully.
  - Periodicity: crank turns per cycle are integers (branch and bound), so the loop does not drift.
  - Layout: mixed-integer optimisation (tooth counts, belt lengths) in Gurobi. Validation: a kinematic simulator and two fabricated figures.
- **[TH14] Thomaszewski et al. 2014, linkage-based characters.** Start from the character driven by one virtual motor per joint, then repeatedly "remove one motor, add a link". This keeps constraints equal to DOFs: a link adds 3 DOFs and two pins add 4 constraints.
  - **Where the new link goes:** at the pair of material points whose distance varies least over the cycle (variance `δab`, Eq. 3). An exponential penalty keeps the triangle (pin, removed motor, pin) from collapsing, which keeps the moment arm, and so the drive force, reasonable (Eq. 4).
  - **Singularity:** collinearity of three joints is "neither necessary nor sufficient". The authors take the smallest singular value λmin of the constraint Jacobian `∂C/∂s` as the measure. The penalty `E_sing = Σ (λmin + ε)^−α` (ε 1e-8, α 2) sits in a CMA-ES global optimisation together with marker tracking, state tracking and pins-near-skeleton terms (weights 100, 100, 500, 1).
  - **Collisions:** not checked during design. Links are layered afterwards.
- **[BA15] LinkEdit 2015.** Closed-form ("symbolic") kinematics: a linkage that decomposes into basic loops is solved loop by loop instead of by a global Newton solve. This makes edits interactive. Users move joints, edit point paths or bound the enclosure, and Jacobian singular values guard against degenerate configurations.
- **[BH15] [A] Walking automata 2015.** Drag-and-drop template mechanisms. Physical simulation plus evolutionary optimisation make the toy walk.
- **[ME15] Robotic creatures 2015.** Servo-driven (12 Dynamixel MX-28) legged robots.
  - Joint angles are the control variables, "because the internal torques … cannot be directly reproduced by off-the-shelf servomotors".
  - The body geometry comes from "structural features": tight-fitting printed enclosures around each servo, allowing ±90°. Consecutive features are joined by the convex hull of their attachment points (a solid union for FFF, a truss for SLS).
  - Measured gap: feet rose ~8 cm against 10 cm in simulation, attributed to print compliance and accuracy and the servos' speed-dependent torque.
- **[ME17] Compliant mechanisms 2017.** Rigid joints are replaced by optimised flexures, with objectives for tracking, collision, lateral stability, failure (von Mises) and motor torque.
  - Without the failure term, a printed Chebyshev linkage broke after one cycle; with it, the linkage ran over 2000 cycles.
  - One example is an **animatronic eye**: 2 motors, 2 hinges, 4 ball-and-sockets, 8 links. A dime-scale rigid version had to have its ball-joint range cut so the balls would not pop out; the compliant version kept its range.
  - Printed on a Stratasys Connex in Rigur, not FDM.
- **[ZA17] MechRet 2017.** A mechanism "template" holds a parameterised mechanism plus three kinds of constraints: mechanical (validity, clearance), functional (intended behaviour) and spatial (alignment to the shape, interior parts kept inside it). An optimisation keeps all three valid while the user moves parts or edits the outer shape.
- **[SO17] Wind-up toys 2017.** Eleven analytically modelled elemental mechanisms are chained by a "motion transfer tree" from one spring motor, then optimised for compactness, weight and collisions.
- **[HO19] Vibration-minimising retargeting 2019.** Not a design method but the same group's answer to fast motion on light, compliant robots. Motor profiles are C²-continuous splines ("to prevent infinite motor torques").
  - An adjoint-method space-time optimisation over a rigid-plus-reduced-elastic simulation suppresses low-frequency, large-amplitude vibrations. It does this by smoothing and pre-empting the motion while tracking the artist's input, with a regulariser on motor acceleration.
  - It ran on Dynamixel XM-430 servos assumed to track their commands.

### What it means for our seven position servos

- **The design line exists to remove actuators.** #51 fixes seven servos, each with its own DOF. Every move the noggin service commands is already arbitrary in time, so cams, non-circular gears and Fourier loops buy nothing for driven DOFs [I]. Their ideas carry over as software: a periodic time-warp `f(α)` [CO13] and integer-frequency loops [CE13] for idle motions.
- **Lids following eye pitch belong in software.** Each lid keeps its own servo (#51) and must still wink and blink independently. A mechanical lid–pitch coupling would need a summing (differential) linkage between the lid servo and the pitch servo. That adds parts and play for what one line of code does: `lid = rest + k·pitch` (§2) [I].
- **The linked eyes are exactly "remove a motor, add a link" [TH14].** Start from four virtual eye motors (L/R yaw, L/R pitch), remove the two right-eye motors and add tie links. [TH14] says where the pins go: at the points whose distance varies least over the whole gaze workspace, here a (yaw, pitch) grid rather than a cycle.
  - For an ideal parallelogram the variance is zero. In a real 3D gimbal, the yaw tie rod and pitch tie rod are offset from the gimbal axes, so the variance across the yaw × pitch grid measures yaw–pitch crosstalk and left/right mismatch [I].
- **[ME17]'s eye shows the same layout for one eye.** Two motors and a spatial linkage of 2 hinges and 4 ball joints drive a two-axis eye. The ball joints are the small-scale weak point, which is where compliance helped.
- **How it maps onto our model [I]:**
  - **Parameters:** pin coordinates in `model/geometry.py`, the inputs `model/linkage.py`'s `four_bar` already takes.
  - **Kinematics:** `four_bar` (closed form, the [BA15] approach) for planar chains. MuJoCo connects (as in `2026-11-01-mujoco-loops.md`) for the spatial gimbal and tie rods.
  - **Singularity:** λmin of the loop-constraint Jacobian. MuJoCo exposes the constraint Jacobian `efc_J` for the connect rows (efc_type equality); a numeric `∂C/∂q` from `four_bar` works for planar chains. This replaces "toggles at −43.4°" (geometry.py's pan note) with a continuous margin over the range.
  - **Torque:** MuJoCo `actuator_force` along the swept trajectory, as the report already does.
  - **Optimiser:** derivative-free (CMA-ES or scipy Nelder–Mead) like [TH14], since an SVD has no easy gradient. Objective: marker tracking plus E_sing plus torque. Heavy sweeps run in CI (memory: heavy builds in CI).

## 2. Gaze and eyelids: additions to the existing notes

- **Lids follow eye pitch.** The upper lid follows vertical eye rotation in "lid saccades", which are much less asymmetric between down and up than blinks [RU14, citing Evinger 1991 and Guitton 1991].
  - Normoyle et al. 2013 animate the lid displacement in proportion to eyeball rotation, except the blink's down phase, which is a step [RU14].
  - [ST10] [A] split lid motion into "lid follows vertical eye rotation" and "blink". Viewers rated their parametric model close to motion capture and clearly better than linear interpolation.
  - Steptoe & Steed 2008 (via [RU14]): eye-socket deformation (lids and skin moving with the eye) raised perceived authenticity and gaze-reading confidence. Vergence had "a much more modest effect".
- **The lid margin moves nearly rigidly.** The eye–eyelid interface "transforms mostly rigidly … sliding over" the eye and "mostly just rotates when the lid opens" [BE15]. Lid shapes and timing also differ between a person's two eyes [BE15]. This supports rigid lid shells pivoting on the eye centre [I].
- **Big eyes break human gaze models [PE13]:**
  - Cross-eyedness becomes visible with large or widely spaced eyes. The default allowed vergence is γMAX = 0.002°, essentially parallel.
  - Convergence is restored only when the viewer is the target, in a viewing cone of 9.6°·W, where W = eye width ÷ 2.5 cm.
  - "Speedy eyes": eye peak velocity is scaled by F′/W³, with F′ = (1−αH)W³ + αH·W³/3. Eyes move at human speed when the head does not move, and down to 1/3 when the head carries the whole shift.
  - A liveliness multiplier χ of 1.2–1.7 suits stylised characters.
  - A gaze-evoked blink is scheduled at t_VOR − 0.35·T_B to hide the eyes' counter-rotation while the head catches up.
  - "Performative" partial gaze αE 0.6–1 keeps the eyes partly on the audience while still reading as looking at the target.
  - 48 participants rated naturalness and appeal. Gaze-target accuracy did not drop significantly.
- **Eye–head coordination** (graphics practice via [RU14]):
  - Shifts above 10–15° recruit the head (physiology: 15–20°, Stahl 1999).
  - For a reaction, the eyes lead (~200 ms latency) and the head starts 20–50 ms later. For a predictable target the head starts ~100 ms before the eyes.
  - Not in the existing notes.
- **Applied to our Mech [I]:**
  - The eyeball is r 20.5 (`model/printed/eyeball.py`), so W ≈ 41/25 ≈ 1.6, up to ≈ 2.4 if a character's caps grow to touching (59 mm centres). [PE13]'s viewing cone is then 15–23°.
  - Parallel linked eyes match [PE13]'s default. Converging both eyes on a viewer 600 mm away would need ≈ 2.8° toe-in per eye (atan(29.5/600)), and the vergence evidence above says that matters little.

## Practices for #51

1. **Design the eye gimbal's tie links by "remove a motor, add a link" [TH14].** Sample the four-motor eye pair over the (yaw, pitch) workspace. Put each tie rod's pins at the point pair with least distance variance, with [TH14]'s area term to keep moment arms. Report the residual variance as crosstalk in degrees.
2. **Score every linkage by its singularity margin.** Report the smallest singular value λmin of the loop-constraint Jacobian over each joint's full range, and penalise it with Σ(λmin+ε)^−2 [TH14, BA15]. Apply this to the eye gimbal, the lid bars, the jaw and the neck.
3. **Optimise continuous pin positions before ranking.** After picking a topology (candidate a or b, the gimbal), run a derivative-free optimisation (CMA-ES as in [TH14]) of the pin coordinates against tracking, the singularity margin and servo torque from MuJoCo. Only then rank. [TH14] and [CO13] both split the problem into a discrete choice and a continuous refinement.
4. **Shape each planar four-bar by function generation [CE13].** Pick three (servo angle, output angle) pairs, for example rest, mid and shut for a lid, and solve Freudenstein's equations for the link lengths. Then add a bar-ratio penalty and the Grashof or range checks. This makes a lid's travel linear, or deliberately eased, in servo angle (the #213 non-linearity).
5. **Couple the lids to eye pitch in software, not by mechanism.** Use `lid = rest + k·pitch` for both lids (lid saccades [RU14, ST10]), with blink closure stacked on top as a step (Normoyle via [RU14]). Start with k ≈ 1 on the downward side and less on the upward side [I, from the existing note's Becker & Fuchs]. No parts are added, and winks keep working.
6. **Scale gaze speed to eye size and head motion [PE13].** Run eye saccades at full speed when the neck is still. Slow the eye servo towards 1/3 when pan or tilt carries the shift. Time a gaze-evoked blink to cover the counter-rotation. Derive W per character from its cap diameter, so Morty and Bart can differ.
7. **Leave the eyes parallel, with an optional fixed toe-in parameter.** [PE13] defaults to parallel and vergence reads weakly (Steptoe & Steed via [RU14]). If the gimbal makes it free, expose a fixed toe-in of ≈ 0–3° per eye; never add a vergence DOF [I].
8. **Recruit the neck above about 15° of gaze shift.** Eyes lead by 20–50 ms on reactive shifts; the head leads by ~100 ms on deliberate ones [RU14].
9. **Command C² trajectories and check magnets against simulated acceleration.** Write gestures as C²-continuous splines with an acceleration penalty [HO19]. Take the magnet hold check's "peak gesture acceleration" from MuJoCo's simulated shell motion under servo slew, not from the commanded curve. Fast moves of light, compliant assemblies excite visible low-frequency vibration that the rigid commanded curve hides [HO19].
10. **Generate the skeleton from servo "structural features" [ME15].** Use a fixed printed enclosure per PG001, then join consecutive features by the convex hull of their attachment points (a solid union, since we print FFF). This is CadQuery-friendly and keeps every servo mount identical [I].
11. **Encode the shells as a template's spatial constraints [ZA17].** Write containment, clearance and magnet-seat alignment between skeleton and shell as named constraints, checked per character across every pose. A new character is then a constraint check, not a hand fit.
12. **Expect the physical Mech to fall about 20% short of the sim.** [ME15] measured 8 cm against 10 cm of foot lift from print compliance, accuracy and speed-dependent servo torque. That supports #51's SF 2. Calibrate travel on the Mech, not from the model [I].
13. **Keep flexures as a fallback for the gimbal's tie-rod ball joints only [ME17].** They help where small printed ball joints pop out or bind. But they need a failure (stress) objective, and [ME17]'s evidence is PolyJet Rigur, not FDM PETG, so fatigue in our material is unverified [I].

## Conflicts with #51

1. **Ranking by prototype alone. #51: "Prototype both and the eye gimbal in the model … the ranking picks."**
   - Evidence: [TH14] and [CO13] get their designs from a discrete choice and then a continuous optimisation of pin positions. Hand-placed pins compare candidates at arbitrary points in their design spaces.
   - Change: optimise each candidate's pins (Practice 3) before applying the ranking. The ranking stays as Cansin set it.
2. **The ranking lacks a singularity margin. #51 ranks simplicity, torque, fit, leads, tip-over and pack access.**
   - Evidence: [TH14] calls singularity avoidance crucial, because near-singular configurations raise drive forces and make fabrication tolerance decide which way the mechanism goes. [BA15] guards edits the same way. Our stock pan four-bar already toggles at −43.4°.
   - Change: make λmin over the full range (Practice 2) a pass/fail gate alongside torque SF 2, not a ranked criterion. This adds no hardware.
3. **The magnet check uses the commanded peak acceleration. #51: "the model checks each part holds against its weight and its peak gesture acceleration."**
   - Evidence: [HO19] shows that light, compliant assemblies under fast steps vibrate well beyond the commanded motion. Our gestures close lids as steps (blink note §4).
   - Change: take the acceleration from MuJoCo's simulated parts under servo slew (Practice 9), and treat each magnet joint as a compliance to check, not a weld.
4. **One choreography for both shells (implied by "shared skeleton", not stated).**
   - Evidence: [PE13] shows that eye size changes what reads as natural eye speed. Eye speed should scale with W and head participation, and big eyes need tuned speed and blink timing.
   - Change: a per-character gaze-speed parameter derived from cap size (Practice 6). The skeleton and servos are unchanged.

No conflict found with the linked eyes (two servos for both eyes, as in [ME17]'s two-motor eye; parallel gaze as [PE13]'s default), with per-lid servos (lid–pitch coupling is software, Practice 5), or with any fixed limit.

Unverified: [BH15] and [ST10] are from their abstracts only. Normoyle 2013, Steptoe & Steed 2008, Evinger 1991, Guitton 1991 and Stahl 1999 come via [RU14]. No paper tests flexures or tie-rod linkages in FDM PETG at our 9 g servo scale.
