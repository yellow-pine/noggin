# Simulation, robotics and HRI for the next Mech

Researched 2026-11-02. Purpose: what the robotics and HRI literature says about modelling PG001-class servos in MuJoCo,
optimising the next Mech's mechanism in simulation, the degrees of freedom that carry gaze and expression, and checking
the clearance of moving shells. Input to #51 (on hold).

Builds on `2026-11-01-mujoco-loops.md`, `2026-11-01-mujoco-report.md`, `2026-11-01-coacd-tuning.md`, model/mjcf.py
(position actuator: kp = stall / 0.5 deg, armature 1e-4, critically damped, all inferred) and model/mujoco_report.py.
Eye and lid timing are in `2026-10-31-natural-eye-motion.md`; this note does not repeat them.

Tags: [P] a preprint from an established lab; [A] only the abstract or a secondary account was read; [I] my inference.

Sources:
- [MJX] MuJoCo 3.17.0 XML reference (the version in uv.lock): actuator `dcmotor`, `pid`, `delay`/`nsample`, joint
  `frictionloss`. https://github.com/google-deepmind/mujoco/blob/3.17.0/doc/XMLreference.rst , rendered at
  https://mujoco.readthedocs.io/en/stable/XMLreference.html#actuator-dcmotor
- [MJC] MuJoCo changelog 3.17.0: `dcmotor` added 3.7.0, `pid` 3.12.0, actuator delays 3.5.0, System Identification
  toolbox 3.5.0. https://github.com/google-deepmind/mujoco/blob/3.17.0/doc/changelog.rst
- [MJS] MuJoCo sysid toolbox README. https://github.com/google-deepmind/mujoco/blob/3.17.0/python/mujoco/sysid/README.md
- [MJE] MuJoCo Model Editing (MjSpec). https://mujoco.readthedocs.io/en/stable/programming/modeledit.html
- [MJA] MuJoCo API reference, `mj_geomDistance`. https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html
- [TAN] Tan et al., Sim-to-Real: Learning Agile Locomotion for Quadruped Robots, RSS 2018.
  https://doi.org/10.15607/RSS.2018.XIV.010
- [BAM] Duclusaud, Passault, Padois, Ly, Extended Friction Models for the Physics Simulation of Servo Actuators [P]
  (Rhoban, Bordeaux; arXiv v4 2025). https://arxiv.org/abs/2410.08650 ; code https://github.com/Rhoban/bam (Apache-2.0)
- [HWG] Hwang et al., Virtual Torque Sensor for Low-Cost RC Servo Motors Based on Dynamic System Identification,
  Sensors 18(11):3856, 2018 (MDPI, outside the listed venues). https://doi.org/10.3390/s18113856
- [BKL] Tanaka et al., Mechanical Intelligence-Aware Curriculum RL for Humanoids with Parallel Actuation [P] (UCLA,
  Hong's group, arXiv 2025). https://arxiv.org/abs/2507.00273
- [HA] Ha, Coros, Alspach, Kim, Yamane, Joint Optimization of Robot Design and Motion Parameters using the Implicit
  Function Theorem, RSS 2017 (Disney Research). https://doi.org/10.15607/RSS.2017.XIII.003
- [KIS] Breazeal, Edsinger, Fitzpatrick, Scassellati, Active Vision for Sociable Robots, IEEE TSMC-A 31(5), 2001.
  https://doi.org/10.1109/3468.952718 (author copy https://people.csail.mit.edu/edsinger/doc/brezeal_active_vision.pdf)
- [ADM] Admoni & Scassellati, Social Eye Gaze in Human-Robot Interaction: A Review, JHRI 6(1), 2017.
  https://doi.org/10.5898/JHRI.6.1.Admoni
- [FOE] Foerster, Bailly, Elisei, Impact of Iris Size and Eyelids Coupling on the Estimation of the Gaze Direction of a
  Robotic Talking Head by Human Viewers, Humanoids 2015. https://doi.org/10.1109/HUMANOIDS.2015.7363528 ,
  full text https://hal.science/hal-01228887
- [AND] Andrist, Pejsa, Mutlu, Gleicher, A Head-Eye Coordination Model for Animating Gaze Shifts of Virtual Characters,
  Gaze-In workshop at ICMI 2012 (virtual agents, not robots). https://doi.org/10.1145/2401836.2401840
- [PAN] Pan et al., Realistic and Interactive Robot Gaze, IROS 2020 (Disney Research) [A].
  https://doi.org/10.1109/IROS45743.2020.9341297
- [SSL] Schwarzer, Saha, Latombe, Adaptive Dynamic Collision Checking for Single and Multiple Articulated Robots in
  Complex Environments, IEEE T-RO 21(3), 2005 [A]. https://doi.org/10.1109/TRO.2004.838012

## 1. Modelling a hobby position servo

- **The model in use is the kind TAN replaced.** A constraint-style position control "guarantees that the motor angle
  and velocity at the end of the time step satisfy the constraint ... if large gains are used, the motors can remain
  stable in simulation but oscillate in reality"; the fix was an ideal DC motor, `tau = Kt (Vpwm - Kt qdot) / R`,
  driven by the servo's own PD on voltage, `Vpwm = V (kp (q* - q) + kd (0 - qdot))`, and a measured latency. Without
  the actuator model and latency, the real robot "fell to the ground immediately" [TAN].
- **What that model gets right [I, from TAN's equations]:** speed falls with load along the torque-speed line, and
  acceleration is bounded by stall torque minus back-EMF. model/mjcf.py instead slews the command at the no-load 428
  deg/s whatever the load (eyes/servo.py `Plant`) and follows it with a stiff P whose force clips at stall. A
  trajectory's start then asks for an instant step to 428 deg/s, so any peak torque or peak acceleration read from it is
  set by the clip, not by the servo.
- **MuJoCo 3.17 has this servo built in.** `dcmotor` takes `nominal = "voltage stall_torque no_load_speed"` and derives
  `K = voltage / no_load_speed`, `R = K voltage / stall_torque`; `input="pos"` with `controller = "kp ki kd slewmax Imax
  Vmax"` closes a PID on position, `Vmax` clamps the drive voltage; optional `lugre` friction (Stribeck), `cogging`,
  `inductance`, `thermal` [MJX]. Actuator `delay` with `nsample` reads the control from a time-stamped history [MJX].
  All are in 3.17.0 [MJC].
  - For the PG001 at 4.8 V (`2026-10-31-electrical.md`): stall 1.0 kgf.cm = 0.098 N.m, no-load 0.14 s/60 deg = 7.48
    rad/s, so K = 0.64 V.s/rad and R = 31 ohm, referred to the output shaft [I, arithmetic].
  - The PWM frame is 20 ms, so a new command waits up to one frame: `delay` 0.02 s [I].
- **One caveat in the docs:** the `dcmotor` controller adds `K qdot` to its voltage "as in a current-controlled
  driver" [MJX]. A hobby servo's driver is a voltage H-bridge (TAN's Minitaur model is the same kind), so the back-EMF
  compensation flatters the servo at speed [I]. Drive it with `input="voltage"` from a P law computed per step in
  Python, or accept the optimism and say so.
- **Friction.** MuJoCo's own joint friction is Coulomb (`frictionloss`) plus viscous (`damping`) [MJX]. On four
  Dynamixel/eRob servos, Stribeck and load-dependent models cut the trajectory error 1.5 to 2.9 times against
  Coulomb-viscous [BAM]; BAM fits these from a pendulum on the servo and ships a MuJoCo binding. No hobby PWM servo is in
  its library [BAM].
- **Deadband.** No peer-reviewed source models a hobby servo's deadband; the PG001 sheet does not give one. A servo
  holds anywhere within `frictionloss / kp` of its target, so `frictionloss` is the plain stand-in for a deadband
  [I, from MJX's semantics].
- **Backlash.** Not native. A deadband in an equality's impedance (solimp kept low inside |r| < eps) modelled it on a
  humanoid's linkages; only qualitative effects reported [BKL]. Plainer [I]: a hinge with `range = +/- b/2` between the
  servo's output body and the horn, so the horn swings freely inside the gap.
- **RC servo dynamics depend on the load.** The closed loop of an RC servo, its controller unknown, was identified per
  load inertia and its response changes with it [HWG]. Identify with at least two loads.
- **Identifying it.** MuJoCo's sysid toolbox fits any MjSpec parameter (actuator gains, joint damping, masses) to
  recorded trajectories by Gauss-Newton over batched `mujoco.rollout`s, and can fit a measurement delay [MJS]. The PG001
  reports no position, so the trajectory has to come from video of a marked horn [I].

## 2. Optimising the mechanism in simulation

- Link lengths and actuator placement optimised jointly with the motion cut a small quadruped's peak servo torque
  from 2.08 to 1.42 N.m (32 %), confirmed on Dynamixel hardware [HA]. HA derives analytic gradients; with a handful of
  continuous parameters a derivative-free sweep needs no gradients [I].
- MjSpec makes the loop cheap: edit the spec, compile, edit again; "after compilation, the mjSpec remains editable"
  [MJE]. model/mjcf.py already builds through MjSpec, so a parameter (a horn radius, a pivot offset, where the boards sit
  on the tilt axis) becomes an argument and model/mujoco_report.py the objective [I].
- Practical size for seven servos [I]: per candidate, two to five continuous parameters, a grid or `scipy.optimize`
  minimise over the report's peak torque and LIMITS clearance, run in CI (heavy builds stay in CI). Learning-based
  co-design is for locomotion and needs no place here.

## 3. Which degrees of freedom carry gaze and expression

- **Linked eyes are the safe choice.** Kismet: eyes pan independently, tilt together; "errors in disjunctive eye
  movements can give the eyes a disturbing appearance of moving independently. Errors in conjunctive movements have a
  much smaller impact on an observer, since the eyes clearly move in lock-step" [KIS]. KASPAR's eyes do not move
  independently, which removes vergence [ADM]. iCub keeps vergence (azimuth, elevation, vergence) [FOE].
- **Eyes that move apart from the head matter.** For a back-projected head, people read the gaze target worse when the
  gaze is head orientation alone (Al Moubayed & Skantze 2012, via ADM) and when the head is seen from the side
  (via ADM). Robots without movable eyes (Keepon, Nao) "rely on head turns" [ADM].
- **The neck carries engagement.** Eyes flicking without rest read as low engagement; "prolonged fixation with smooth
  pursuit and orientation of the head towards the target conveys a much greater level of engagement"; leaning or
  craning the neck read as interest [KIS]. Kismet compensates the eyes for head motion by efference copy [KIS].
- **Eye-head coordination (virtual agents) [AND]:** head onset from 100 ms before to 100 ms after the eyes; head peak
  speed 50 deg/s in their implementation; human oculomotor range 45 to 55 deg; once the eyes reach the target they
  counter-rotate against the head (VOR) until the head stops; a head-alignment parameter from 0 % to 100 %. Rated more
  realistic than the earlier model (p = .017) and as accurate as human confederates (96 participants).
- **Disney's animatronic bust** layers saccades, blinks, breathing and small head motions under its gaze states
  (read, glance, engage, acknowledge), with habituation [PAN, A].
- **Lids that track eye elevation make gaze readable.** On iCub, upper lids held "as low as possible" for each eye
  position lowered the global, elevation and azimuth reading errors against static lids, on a 10 x 10 board at 70 cm
  [FOE]. An earlier study found no such effect (FOE's ref. 24); FOE's is the more recent and controlled.
- **Physical eyes.** Flat displays carry the Mona Lisa effect; 3D eyes like iCub's "may also offer a better view of
  the robot's gaze direction ... from a range of viewing angles" [ADM].

## 4. Clearance of moving shells

- `mj_geomDistance(m, d, g1, g2, distmax, fromto)` returns the smallest signed distance between two geoms, capped at
  `distmax`; "distances are inaccurate when using the legacy CCD pipeline" [MJA]. On CoACD's convex pieces it gives a
  separation, not only contacts inside a margin [I].
- **Sampled poses can miss a collision.** Adaptive checking makes a path segment exact: compare the separation at its
  ends with an upper bound on how far any point of the moving body can travel along it, and subdivide only where the
  bound exceeds the separation [SSL, A]. The bound for a hinge [I]: a point at radius r moves at most r * |dtheta|.
  For a shell edge 60 mm from the tilt axis and the report's 0.1 mm clearance, a sample every 0.1 deg; at 428 deg/s
  that is every 0.2 ms, and the trajectories' 100 ms frames move a servo up to 43 deg.

## Practices for #51

1. Model each PG001 as a MuJoCo `dcmotor` with `nominal = "4.8 0.098 7.48"` (output-referred), a P controller, `Vmax`
   4.8 V and `delay` 0.02 s; keep `frictionloss` as the deadband and an `armature` for the gear train. Mark every
   number inferred until item 2 measures it. (TAN, MJX)
2. Identify one PG001 once: film its horn at the phone's slow-motion rate with a marker, two known loads, steps and
   sweeps; fit kp, `frictionloss`, armature and delay with `mujoco.sysid`. If the fit misses at low speed, try `lugre`.
   (MJS, HWG, BAM)
3. Read dynamic torque and the shells' peak acceleration only from that actuator, along the gestures' own trajectories:
   SF = stall / peak |actuator force|. (TAN, I)
4. Before ranking the base candidates, tune each one's few continuous parameters (board position along the tilt axis,
   horn and coupler lengths, gimbal pivots) through MjSpec against the report, then rank the tuned designs. (HA, MJE)
5. Keep the eyes linked; set a fixed toe-in in the gimbal so the eyes converge at the user's desk distance instead of
   running parallel (e.g. 2.9 deg each for 60 mm between eye centres at 0.6 m). (KIS, I)
6. Make the lids track eye elevation in the eye program: lid target = expression opening + k * eye up/down. The model
   then checks lid travel and clearance over the eye up/down x lid grid, not the lid alone; each lid servo's range must
   cover closure plus the tracked elevation. (FOE, I)
7. Gaze shifts past the eyes' range: eyes first, neck within 100 ms, eyes counter-rotate as the neck arrives. The eyes
   and the neck sit on different Cores over Wi-Fi, so simulate the counter-rotation with an actuator `delay` per Core to
   find the jitter it tolerates. (AND, KIS, MJX)
8. Certify a moving shell's clearance adaptively: `mj_geomDistance` at samples, subdivide where r * |dtheta| exceeds
   the separation; no fixed-step sweep. (SSL, MJA)

## Conflicts with #51

- **"Servo torque (SF 2 incl. dynamic)" and the magnets' "peak gesture acceleration".** #51 ranks on dynamic torque and
  checks magnets against peak acceleration, but the model's actuator (a no-load slew followed by a stiff P clipped at
  stall) sets both peaks by its own clip; ADR 0007 already dropped the torque at peak acceleration. TAN shows a
  constraint-style position servo diverging from hardware and fixes it with a DC motor plus the servo's PD, which
  MuJoCo 3.17 ships as `dcmotor`. Proposed: #51's prototypes measure both on `dcmotor` actuators (Practices 1 to 3)
  before the ranking runs.
- **"Prototype both ... the ranking picks".** Ranking two hand-placed candidates compares placements, not concepts:
  optimising link lengths alone moved peak torque by 32 % on hardware (HA), likely more than the gap between (a) and (b)
  [I]. Proposed: each candidate is tuned (Practice 4) before the ranking.
- **"Eyes linked".** Supported (KIS), but #51 is silent on vergence: linked parallel eyes look past a viewer half a
  metre away, while every reference head keeps vergence (KIS, iCub via FOE). Proposed: a fixed toe-in in the gimbal
  (Practice 5); no servo added.

Not found: a peer-reviewed deadband or backlash figure for any 9 g hobby servo; FOE's iCub lids are the only measured
lid-coupling result; Pan et al. (IROS 2020) and Al Moubayed & Skantze (2012) were read through abstracts or reviews only.
