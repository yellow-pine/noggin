# Motion control for open-loop hobby servos (the next Mech)

Researched 2026-11-02. Purpose: the trajectory, vibration, current and hold rules the next Mech's (#51) bigger head on 9 g servos needs. This builds on `2026-11-01-blink-kinematics.md` (servo slew against human speed), `2026-11-01-toon-eyes.md` and `2026-10-31-neck.md`, and does not repeat them. Servo figures (PG001 stall 0.55/0.65 A, standby 8 mA, 428 °/s) are from `2026-10-31-electrical.md`.

Sources:
- [FH] Flash & Hogan 1985, J Neurosci 5:1688, minimum jerk. https://doi.org/10.1523/JNEUROSCI.05-07-01688.1985 [A]: only the abstract was readable; it confirms "bell-shaped tangential velocity profiles" from minimising squared jerk. The quintic below is the standard closed form; the numbers derived from it are mine.
- [SS] Singer & Seering, "Preshaping command inputs to reduce telerobotic system oscillations", NASA NTRS 19900020564 (full text, 1990). https://ntrs.nasa.gov/api/citations/19900020564/downloads/19900020564.pdf. The journal version (J Dyn Sys Meas Control 112:76, 1990, https://doi.org/10.1115/1.2894142) was not read.
- [Mo] Moriello, *Online Trajectory Planning for Vibration Suppression and Perfect Tracking*, PhD thesis, Bologna 2016, §2.2–2.3. https://amsdottorato.unibo.it/id/eprint/7432/1/PHD_Thesis_Moriello.pdf
- [BM] Biagiotti & Melchiorri 2012, "FIR filters for online trajectory planning…", Control Eng Pract 20:1385 [A]. Also their book *Trajectory Planning for Automatic Machines and Robots*, Springer 2008, https://doi.org/10.1007/978-3-540-85629-0 [A].
- [M5] Mitsubishi M51660L datasheet, "Servo motor control for radio control" (an analog servo IC). https://s1.dtsheet.com/store/data/000293928.pdf
- [HM] Hitec servo manual (2002), hosted at https://people.ece.cornell.edu/land/courses/ece4760/FinalProjects/f2012/jmv87/site/files/Servomanual.pdf
- [PM] Pololu Maestro servo controller user guide §4.b. https://www.pololu.com/docs/0J40/4.b
- [LEDC] ESP-IDF LEDC documentation for the ESP32-C3. https://docs.espressif.com/projects/esp-idf/en/stable/esp32c3/api-reference/peripherals/ledc.html
- [Dr] Drvárová et al. 2024, Acta Phys Pol A 146:810, damping of printed PLA, ABS and PETG. https://doi.org/10.12693/APhysPolA.146.810
- [PG] Bambu PG001 spec sheet, via `docs/research/2026-10-31-electrical.md` §1 and Clutch.
- [Ri] Riazi et al. 2017, IEEE TASE 14:646, peak power. https://doi.org/10.1109/TASE.2016.2641743 [A]

Symbols: D = move size, T = move time, τ = t/T, f = mode frequency, ΔT = half the damped period.

## 1. What a hobby servo does with a pulse stream

- **The analog loop:** each input pulse fires a one-shot. The servo compares the one-shot against the potentiometer, turns the difference into an error pulse, stretches it and drives the motor [M5 block diagram, pin notes]. A resistor sets the deadband; the datasheet gives a minimum of 1.5 µs (RDB 510 Ω, CS 0.1 µF), and its curve runs to about 10 µs [M5].
  - [I] The motor is driven only in response to a pulse, so without pulses the servo produces no torque. The datasheet's "protection circuit for continuous H level input" also cuts drive on a stuck-high input [M5].
- **Frame rate:** Hitec specifies a 50 Hz (20 ms) refresh. Its digital servos send motor drive "five times faster than analog servos", give "3 times" the standing torque and "consume tremendous amount of power" [HM].
  - The PG001's frame rate and deadband are not published. Over 500–2500 µs for 180° [PG], one degree is 11.1 µs, so a 1.5–10 µs deadband would be 0.14–0.9° [I].
- **When a new duty lands:** on the ESP32-C3, "the new LEDC parameters don't take effect until the next PWM cycle" [LEDC]. Duty resolution goes up to 14 bits [LEDC enum]. At 50 Hz that is 20 ms / 16384 = 1.2 µs, about 0.11° [I].
  - Setpoints written faster than every 20 ms are therefore lost; the last one in each frame wins [I].
  - With `duty_ns`, the command resolution sits below any plausible deadband [I].
- **Controller practice:** servo controllers limit the pulse stream's speed (units of 0.25 µs per 10 ms) and its acceleration (0.25 µs per 10 ms per 80 ms) to make an open-loop servo move smoothly [PM]. That is the same job as `glide`, plus an acceleration limit.
- **What this means for motion [I]:**
  - At 50 Hz every frame is a small step command.
  - At the 428 °/s slew a frame can ask for up to 8.6°. A step larger than the servo's proportional band saturates the drive: full voltage, so roughly stall current while it accelerates (servo.py `current()` at zero speed).
  - Moves whose per-frame increment is below the deadband do not move the servo until the accumulated error crosses the deadband. The servo then jumps one deadband at a time, so very slow drifts step visibly (≈0.5° per frame, 25 °/s, is the order where this starts).

## 2. Trajectory profiles

- **Minimum jerk** [FH]: x = D(10τ³ − 15τ⁴ + 6τ⁵).
  - Peak velocity 1.875·D/T at τ = 0.5 [I, arithmetic].
  - Peak acceleration 5.77·D/T² at τ = 0.211 and 0.789 [I].
  - Zero velocity and zero acceleration at both ends.
- **Trapezoid and double-S:** a cascade of moving-average FIR filters on a step yields trapezoidal, double-S and higher-order trajectories online. Each filter adds one order of continuity [BM abstract, A]. [I] A moving average of length T has spectral zeros at f = k/T. This is the frequency-domain link to input shaping.
- **Residual vibration of a single undamped mode,** after one move, as % of the move, by f·T [I: Fourier transform of each profile's velocity; script not kept]:

| profile | f·T = 1 | 1.5 | 2 | 3 | 5 |
|---|---|---|---|---|---|
| linear ramp (`glide` "") | 0 | 21 | 0 | 0 | 0, but up to 2/(π f T) between integers |
| ease "in" / "out" (f², velocity jump at one end) | 32 | 22 | 16 | 11 | 6 |
| smoothstep (`io`) | 30 | 3 | 8 | 3 | 1 |
| minimum jerk | 46 | 12 | 3 | 0.6 | 0.1 |

  - Minimum jerk is the only profile here whose residual falls off monotonically: under 3% once T ≥ 2 periods, and under 1% at 3.
  - The linear ramp is perfect only at whole periods and fragile between them.
  - The `in`/`out` eases end at full speed, so a heavy part keeps ringing.

## 3. Vibration: input shaping and the mode

- **ZV shaper:** two impulses, amplitudes 1/(1+K) and K/(1+K), at 0 and ΔT. K = exp(−ζπ/√(1−ζ²)) and ΔT = π/(ω√(1−ζ²)), half the damped period [Mo eq. 2.21–2.22].
- **ZVD shaper:** 1, 2K and K² over (1+K)², at 0, ΔT and 2ΔT [SS Fig. 3]. It is the ZV shaper applied twice (H_ZVD = H_ZV²) and lasts one full period [Mo §2.3].
  - At ζ ≈ 0 these are ½, ½ and ¼, ½, ¼ [I].
  - Applying the shaper means convolving any command with the impulses. The shaped command is close to the original, but the vibration cancels [SS].
- **Robustness:** ZV is "extremely sensitive" to frequency error. ZVD has zero slope at the design frequency [SS Fig. 2–3]. Undamped, at frequency errors of 5 / 10 / 20%, ZV leaves 7.8 / 15.6 / 30.9% residual and ZVD 0.6 / 2.4 / 9.5% [I, computed]. SS and many after them take under 5% as "settled".
- **Shaping at 50 Hz:** impulses must land on the sample grid. The error is about δt/(4ΔT) [SS], with δt = 20 ms:

| f | ZV length | ZVD length | grid error |
|---|---|---|---|
| 4 Hz | 125 ms | 250 ms | 4% |
| 6 Hz | 83 ms | 167 ms | 6% |
| 10 Hz | 50 ms | 100 ms | 10% |
| 15 Hz | 33 ms | 67 ms | 15% |

  - So frame-rounded shaping works for modes up to about 6–8 Hz [I].
  - Above that, SS solve an impulse sequence constrained to the grid [SS, "Sequences for Digital Systems"]. The simpler route there is a minimum-jerk T ≥ 2–3 periods (§2) [I].
  - In a multi-joint system one sequence serves every joint, and for linear systems shaping one axis does not disturb another [SS].
- **Damping:** printed material damping is tiny. PETG has ζ = 0.0037, PLA 0.0068 and ABS 0.0080, from log decrement on cantilever rods [Dr]. Undamped shaper values apply.
  - Joints, magnets and the gearbox add damping that no source sizes [I].
  - A light ζ also means ringing outlasts a gesture: at ζ = 0.004 the decay to 5% takes about 120 cycles [I].
- **Estimating the mode from the model [I]:**
  - f = (1/2π)·√(k/J), with k_head = k_servo/G². G is the linkage gain: 0.32 tilt and 0.47 pan in the stock neck (`2026-10-31-neck.md`).
  - The model's servo stiffness is KP = 11.2 N·m/rad (mjcf.py; inferred, full torque at 0.5°). For a 0.3 kg head at a 6 cm radius that gives 16 Hz direct, 35 Hz through pan and 51 Hz through tilt.
  - Those are servo-loop modes, and probably too high. Within the deadband and gear backlash the servo has no stiffness, so the real lowest mode is set by printed compliance (the neck column, the board tower in option (b)) and backlash, which the rigid MuJoCo model does not carry.
  - How to get it:
    - In MuJoCo, give the printed joints a compliant joint (stiffness from a beams.py section estimate), step the joint, and read the ring frequency from the residual.
    - On the built Mech, film a stop at 240 fps on a phone, count frames per cycle, and mark the result inferred (no calliper needed).

## 4. Peak current through motion

- **Stall budget [I from the published figures]:**
  - A step command saturates the drive. The PG001 then draws up to its stall current, 0.55 A at 4.8 V and 0.65 A at 6 V, until back-EMF builds.
  - All seven servos stepping at once: 3.9–4.6 A. That is over the 3 A that the shield maximum, the pack's continuous rating and the switch board each allow (model/electrical.py `CAP_A`).
- **Smooth moves draw far less [I, servo.py constants: kt ≈ 2 kgf·cm/A at 4.8 V; model ARMATURE 1e-4 kg·m²]:**
  - Example: a 30° minimum-jerk tilt in 0.3 s on a 0.3 kg, 6 cm head, through G = 0.32, with 1 cm CoM offset.
  - The servo needs ≈ 0.11 kgf·cm for head inertia, ≈ 0.10 for gravity and ≈ 0.11 for its own reflected rotor: about 0.16 A peak, roughly a third of a step's stall draw.
  - The reflected rotor inertia is as large as the head's, so even a light part needs an acceleration limit.
- **Staggering minimum-jerk moves:** summed inertial current of two identical moves started d·T apart, relative to one move [I, computed]:

| d | 0 | 0.2 | 0.3 | 0.5 | 0.8 | ≥1 |
|---|---|---|---|---|---|---|
| peak | 2.0× | 1.65× | 1.42× | 1.95× | 1.5× | 1.0× |

  - Half-offsets do not help: the acceleration and deceleration lobes then add.
  - Three moves offset by 0.25–0.5 T peak at 1.95–2.15×.
  - Peak power can also be cut by retiming alone, without changing the path: up to 60% on industrial robots [Ri, A].
- **Rule of thumb [I]:**
  - Never let more servos be in a saturating step than the budget allows (two per Core: 2 × 0.65 + Core and Wi-Fi ≈ 1.6 A).
  - Give every other move an acceleration cap: α_max = (I_budget·kt − T_gravity)/(J_reflected + J_load·G²), referred to the servo shaft.

## 5. Holding versus releasing

- **Published figures:** the only idle figure is standby 8 mA [PG]. No holding torque or holding current is published (`2026-10-31-electrical.md`).
- **Holding a load [I]:**
  - Holding against gravity costs ≈ T/kt: 0.16 A at the PG001's rated 0.32 kgf·cm, continuously. That is 20× standby, and it heats the motor.
  - A proportional loop also droops under load. Hitec credits its digital servos' faster refresh with both more holding power and a tighter deadband [HM].
- **Hunting at rest [I]:** a servo holding a load near the edge of its deadband, through gear backlash, alternately drives and lets go. That is the hum and hunting the deadband exists to suppress [M5: deadband set by resistor].
  - Cures, cheapest first:
    - a rest pose with near-zero gravity torque (CoM on the axis);
    - approach every rest target from the same side, so backlash is taken up the same way;
    - a light preload such as a spring.
- **Detaching PWM:** `deinit` stops pulses, and LEDC parks the pin at an idle level [LEDC `ledc_stop`]. An analog servo then has no drive [M5, I], and some controllers offer this as an explicit "Off" state [PM].
  - A gravity-loaded joint then back-drives and droops. eyes.py already notes this for the lids and eyes.
  - On re-attach, the first pulse commands the stored target from wherever the joint drooped to. Without feedback the program cannot ramp from the real position, so re-attach is a step: stall current plus a jolt [I].

## Practices for #51

1. Write a servo at most once per 20 ms frame (LEDC latches per period). Keep 50 Hz unless the PG001 is shown to take faster frames. [LEDC, HM]
2. Every head move (tilt, pan) and every eye-gimbal move uses minimum jerk with T ≥ 2 periods of the lowest mode (≥ 3 for under 1% residual). The `in`/`out` eases, which end at speed, stay for the lids only. [FH, §2 table]
3. Cap every servo's acceleration as well as its speed, like [PM]. Derive the cap from the current budget (§4): α_max = (I_budget·kt − T_gravity)/(J_reflected + J_load·G²).
4. Allow a saturating step (blink close, eureka pop) on at most two servos per Core at once. Stagger other moves by whole durations, not half (two simultaneous minimum-jerk moves peak at 2×, at 0.3 T apart 1.42×, sequential 1×).
5. Where a mode is ≤ 6–8 Hz, convolve head commands with a ZVD shaper rounded to 20 ms frames: ¼, ½, ¼ at 0, ΔT, 2ΔT, with ζ ≈ 0. Above that, lengthen T instead. One shaper serves every joint. [SS, Mo]
6. Find the mode: model compliant printed joints in MuJoCo and read the step ring, then confirm with 240 fps phone video on the build (inferred, no calliper).
7. Make every held pose gravity-neutral (CoM on the tilt and pan axes, within what the model shows). Then hold current falls towards the 8 mA standby and hunting goes away. [§5]
8. Approach every rest target from the same side (backlash).
9. Avoid moves slower than about one deadband per frame (~25 °/s at a 0.5° guess). Do slow drift as small saccade-like hops instead (they already exist), or measure the PG001 deadband first.
10. Release (`deinit`) only for long idles such as mute. Re-attach one servo at a time, about 100 ms apart, commanding the pose the joint falls to. Design the released pose to be the rest pose (rests on a stop, or is balanced).
11. The magnet check in #51 uses the gesture's real peak acceleration: 5.77·D/T² for a minimum-jerk move, and the servo's stall-limited acceleration for steps. It cannot use a nominal figure. [FH, I]

## Conflicts with #51

- **Head mass and the base layout (#51 candidates (a), boards in the head, and (b), a static tower).** #51 ranks on "servo torque (SF 2 incl. dynamic)" but says nothing about static torque at rest or the first mode.
  - Evidence: a held gravity load draws ≈ 20× standby continuously and invites hunting (§5). Printed parts are almost undamped (ζ ≈ 0.004–0.007 [Dr]), so a low mode rings through whole gestures (§3).
  - Proposed: add two ranking criteria after torque. (1) Gravity torque at the rest pose ≈ 0: in (a), place the boards behind the tilt axis as counterweight, not ahead. (2) A lowest mode high enough that T ≥ 2 periods fits the toon timings, e.g. ≥ 8 Hz for a 250 ms head move [I].
  - The tower in (b) must be checked for its own sway mode, since it carries no load but stands in the head's sweep.
- **Seven servos on one 3 A pack, with gestures that use steps** (eyes.py blink close and eureka pop, kept for #51 since "neck and jaw as built").
  - Evidence: 7 × 0.55–0.65 A of saturating steps is 3.9–4.6 A, over the 3 A shield, pack and switch figures (§4).
  - Proposed: a per-Core current budget (Practice 4), and minimum jerk with an acceleration cap for all neck-Core moves (tilt, pan, mouth). This sits inside the fixed limits and needs no hardware change.
- **"The model checks each part holds against … its peak gesture acceleration."** A step's peak acceleration is undefined in the model: the servo limits it, not the gesture.
  - Proposed: gestures declare their profile and T, and the check uses 5.77·D/T² for minimum-jerk moves and the servo's stall-torque-limited acceleration for steps (Practice 11).

Unverified: I read Flash & Hogan, Biagiotti & Melchiorri and Riazi as abstracts only. The SS robustness bands are read off figures. The PG001 deadband, frame-rate tolerance and holding behaviour are unpublished, and so are the head's mass, inertia and modes (the figures here are illustrative). Every number marked [I] is my arithmetic on the models named.
