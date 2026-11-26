# The standard servo's band, frame rate and response (#978)

Researched 2026-11-26. Purpose: the sourced facts behind the standard servo's model in the sim. The Mech's tilt and
pan use the MG996R standard metal-gear servo (the buy list in `docs/build/parts.md` and
`docs/research/2026-11-04-standard-tilt-servo.md`, since #975). When this was written, `model/mjcf.py motor()` gave it
full torque at 0.5° of error (`kp` = stall / 0.5°), which is inferred. With 20 ms command steps that rang the
life-size head at about 41 Hz on tilt and 25 Hz on pan, and the hero failed its tip-over and face-magnet gates
([#978 comment](https://github.com/yellow-pine/noggin/issues/978#issuecomment-7201463422)). Facts only; no design
decision.

Builds on `2026-11-02-literature-motion-control.md` §1 (analog loop, Hitec frame rate, LEDC latching) and
`2026-11-02-literature-simulation.md` §1 (`dcmotor`, deadband, sysid). It does not repeat them.

Trust tags: [M] the servo's maker; [D] an IC maker's datasheet; [T] a measured study (thesis or journal) with its
method; [B] a hobbyist or vendor blog with measurements; [F] a forum post; [R] a reseller or database; [I] my inference
or arithmetic.

Sources:

- [TP] Tower Pro, MG996R product page (read 2026-11-26). https://towerpro.com.tw/product/mg996r/ [M]
- [RS] "MG996R High Torque Metal Gear Dual Ball Bearing Servo", an unsigned spec sheet (Word export, 2014) that
  resellers and course pages host, e.g.
  https://people.ece.cornell.edu/land/courses/ece4760/FinalProjects/f2017/kmv48_rp625/kmv48_rp625/kmv48_rp625/MG996RTowerPro.pdf [R]
- [SDB] ServoDatabase, TowerPro MG996R. https://servodatabase.com/servo/towerpro/mg996r [R]
- [HAD] Hackaday.io project 6748, "Reverse Engineering - Schematic", comment by rocketsmith (2018-10-15).
  https://hackaday.io/project/6748-127-towerpro-servos-one-i2c-interface/log/21421-reverse-engineering-schematic [F]
- [ARD] Arduino Forum, "Help identifying resistor/capacitor to replace on servo mg996r pcb" (2016-03-31).
  https://forum.arduino.cc/t/help-identifying-resistor-capacitor-to-replace-on-servo-mg996r-pcb/376200 [F]
- [AA] Agamem Microelectronics, AA51880 Servo Motor Controller, preliminary datasheet (2008-04-22), copy at
  https://mikrocontroller.net/attachment/534207/AA51880.pdf [D]
- [M5] Mitsubishi M51660L, Servo Motor Control for Radio Control, datasheet, copy at
  https://www.hobbielektronika.hu/forum/getfile.php?id=99335 [D]
- [ZN] GEC Plessey ZN409CE Precision Servo Integrated Circuit, DS3894 issue 2.0 (1993), copy at
  https://shop.griederbauteile.ch/info/z/ZN409CE.pdf [D]
- [PB] Pololu blog, "Servo control interface in detail" (Jan, 2011-02-09).
  https://www.pololu.com/blog/17/servo-control-interface-in-detail [B]
- [FR] Futaba 10CAG manual, receiver R6014HS/R6008HS modes. https://www.manualslib.com/manual/378230/Futaba-10cag.html?page=8 [M]
- [F4] Futaba T4PK 2.4 GHz manual, cautions. https://www.manualsdir.com/manuals/676275/futaba-4pk-24ghz.html?page=7 [M]
- [UMN] Lakshminarayan, *Model-based Fault Detection for Low-cost UAV Actuators*, MSc thesis, University of Minnesota,
  2016 (advisor P. Seiler), §3.
  https://conservancy.umn.edu/server/api/core/bitstreams/3e69ede4-bd7a-41fd-b2ed-301ddf43cd51/content [T]
- [DW] Dom Wilson, "Hobby Servo Motor Performance", encoder-measured, code at github.com/domw95/ServoTesting.
  https://domwil.co.uk/posts/servo-performance/ [B]
- [HWG] Hwang et al., Sensors 18(11):3856, 2018. https://doi.org/10.3390/s18113856 (full text via Europe PMC,
  PMC6263914) [T]
- [PSO] Chotikunnan et al., "Enhancing MG996R Servo Motor Performance Using PSO-Tuned PID and Feedforward Control",
  IJRCS 5(2), 2025. https://doi.org/10.31763/ijrcs.v5i2.1854 (abstract only; the full text was blocked) [T, A]
- [MPY] MicroPython ESP32 quick reference, PWM. https://docs.micropython.org/en/latest/esp32/quickref.html [M]
- [LEDC] ESP-IDF LEDC, ESP32-C3. https://docs.espressif.com/projects/esp-idf/en/stable/esp32c3/api-reference/peripherals/ledc.html [M]

## 1. Deadband, proportional band, analog or digital

**What the maker publishes.** "Dead band width: 1us" [TP]. Nothing else about the loop: no pulse range, frame rate,
or analog or digital. The page lists it under "X-Large Servo 50g+", with no analog or digital category. It calls
it "an upgraded version of MG995 servo". A staff reply on the page gives 0–159° travel [TP].

**Conflicts.**

- Deadband: the widely hosted spec sheet says "Dead band width: 5 µs" [RS]; the maker's page says 1 µs [TP]. Both
  stand.
- Analog or digital: the spec sheet says "MG996R Digital Servo" [RS], and ServoDatabase says "Digital" with "1 µs",
  "20 ms" and "50 Hz" [SDB]. Two hobbyists who opened MG995/MG996 units found an Agamem AA51880 [HAD, ARD]. The
  Arduino poster calls R3 "the dead band timing resistor" and replaces it [ARD]. Neither says whether the servo was
  genuine Tower Pro or a clone.

**The AA51880 is an analog servo IC** [AA]:

- A one-shot is compared with the pot; "the difference between the servo control signal and the feedback signal is
  the error signal".
- A pulse stretcher "stretch[es] the small error signal long enough and increases the duty cycle to the motor".
- A dead band is set by the resistor on the RDB pin.
- The H-bridge output "will be turned on or off with each input pulse".
- The datasheet gives no figure for the stretch, the band or the deadband.

**Figures from the same class of IC.** The M51660L, the IC behind the prior note's analog loop, gives a
"minimum dead band width" of 1.5 µs (RDB 510 Ω, CS 0.1 µF) and a curve to about 10 µs [M5]. The ZN409CE is the one
datasheet found that states the proportional band [ZN]:

| ZN409CE, VS 5 V | min | typ | max | conditions |
|---|---|---|---|---|
| Error pulse for full drive | 70 | 100 | 130 µs | 15 ms repetition rate, CE 0.47 µF, RE 180 kΩ |
| Minimum output pulse | 2.5 | 3.5 | 4.5 ms | CE 0.47 µF, RE 180 kΩ |
| Total deadband | ±3.5 | ±5 | ±6.5 µs | CD 1000 pF |

The pulse expansion "ensures that a stationary motor will start rotating without drawing full stall current" [ZN].
The M51660L feeds the motor's output back to its timing capacitor: "Also connect a feedback resistor from the output
here" [M5]. Its example circuit appears to use 560 kΩ, and the AA51880's 470 kΩ (read from the drawings' text, so
inferred) [M5, AA]. The ZN409CE: "Dynamic feedback can be used to reduce the width of the deadband" [ZN].

**In degrees [I].** The Core writes 488.8–2482.9 µs over 180° (`eyes/eyes.py _pulse_ns`), 11.1 µs per degree. If the
servo's 159° spans that range [TP], it is 12.5 µs per degree.

- Deadband: 1 µs is 0.08–0.09°; 5 µs is 0.40–0.45°.
- Full drive: the ZN409CE's 100 µs (70–130) at 15 ms is 8–9° (5.6–11.7°).

**How an analog servo shapes torque against error [I, from AA, ZN, PB].**

- Inside the deadband there is no drive.
- Just outside it, the drive is the minimum stretched pulse: 3.5 ms in a 20 ms frame, about 18% (12.5–22.5%) duty.
- Past that, duty grows with the error until the stretched pulse fills the frame. The stretch is about 15 ms /
  100 µs ≈ 150 times (115–214).
- In a 20 ms frame, full drive is at about 133 µs (93–173), roughly 11–12° (7.5–15.6°).
- The drive is full-voltage pulses, one per input pulse. The torque is their average over the frame, not a
  continuous P law.
- Pololu's scope traces show this on an analog servo (S148): its drive follows each command pulse. The drive's duty
  rises with the pulse rate ("at 100 Hz … pushing back almost 50% of the time even with a slight output resistance")
  and falls at 20 Hz. A digital servo's drive did not depend on the pulse rate [PB].

**A digital servo** drives its motor from a microcontroller at a rate far above the frame. The prior note cites
Hitec's "five times faster" [motion-control HM]. No source gives a digital MG996R's proportional band.

## 2. Frame rates

- Tower Pro publishes none [TP]. The spec sheet and ServoDatabase give a 20 ms cycle, 50 Hz [RS, SDB].
- Futaba: "Normal mode accepts any type of servos … as the frame rate of the output is 14ms"; "High Speed mode only
  accept the digital servos … The frame rate of the outputs is 7ms" [FR]. "When using analog servos, always switch …
  to the NORMAL mode. Operation in this mode will cause trouble of servo and other equipments" [F4].
- UMN's bench: "Most analog and digital servos have a maximum safe update rate of 50Hz". Near the limits they saw
  "uncontrolled motion in the form of sudden jerks and a high current consumption with overheating". Within the limit,
  a faster rate gave "higher servo bandwidth, tighter deadband, more holding power" [UMN].
- Pololu: "Most servos can handle substantially faster pulse rates"; "some special servos are designed to support
  pulse frequencies of several hundred hertz" [PB].
- No source says the MG996R accepts 100–333 Hz. If it is the AA51880 kind [I, from AA, ZN, PB]:
  - its band in µs shrinks with the frame period, so a faster frame makes it stiffer, not softer;
  - at 100 Hz full drive comes at about 67 µs (6°), and the minimum pulse is 35% duty;
  - above about 286 Hz the 3.5 ms minimum pulse outlasts the frame, so any error past the deadband is full drive.

**The Core can drive it.**

- MicroPython's PWM takes "1Hz to 40MHz" [MPY].
- The ESP32-C3 has 6 LEDC channels and 4 timers, so a Core runs at most 4 frequencies; its channels at one frequency
  share a timer [MPY, LEDC].
- The LEDC clock is 80 MHz APB, 40 MHz XTAL or about 20 MHz RC_FAST, with up to 14 bits of duty [LEDC].
- At 333 Hz, 14 bits need 333 × 16384 = 5.5 MHz, well under 80 MHz, so a step is 0.18 µs [I].
- "The new LEDC parameters don't take effect until the next PWM cycle" [LEDC].
- `eyes/eyes.py` (`FRAME = 20`, `PWM(Pin(gpio), freq=50)`), `noggin/service.py` (`FRAME = 0.02`) and
  `model/trajectories.py` (`PWM_MS = 20`) each fix the frame at 20 ms.

## 3. Measured response, damping, velocity limit

- **MG996R:** no published step or frequency response with figures. One journal paper fits a second-order
  discrete-time model to a stock MG996R through its own pot (96.94% fit). It runs a 10° step and a 2 rad/s sine, but
  its coefficients were not readable here [PSO]. Its only velocity figure is the rated speed: 0.19 s/60° at 4.8 V
  (316°/s) and 0.15 s/60° at 6 V [TP].
- **Velocity limiting:** none of the analog IC datasheets describes a speed limiter [AA, M5, ZN]. Full drive runs the
  motor along its torque-speed line [I]. The output feedback above adds damping that rises with speed [I, from M5, ZN].
- **Close equivalents, measured** [UMN]: unloaded servos (a gearless servo's pot as the sensor), a ±4° chirp from 1 to
  25 Hz, and 1000→1800 µs steps.

| servo | price | fitted command → angle | natural freq, damping [I] | bandwidth | rate limit | delay |
|---|---|---|---|---|---|---|
| Hitec HS-225BB | $18 | 122300 e^−0.004s / ((s+24.84)(s²+70.04s+4921)) | 11.2 Hz, ζ 0.50 | 4.5 Hz | 370°/s | 4 ms |
| Futaba S3151 | $30 | 654.1 / (s²+17.27s+654.1) | 4.1 Hz, ζ 0.34 | 5.8 rad/s as tabled | 265°/s | 10 ms |
| Futaba S9256 | $60 | 5.165e4 / (s²+579.3s+5.165e4) | two real poles (110, 469 rad/s) | 104.5 rad/s | 1263°/s | 10 ms |

  - UMN: "Cheap servos such as the HITEC HS-225BB and Futaba S3151 have poles that are oscillatory in nature", which
    it puts down to loose plastic gears [UMN].
- **Digital servos** (Corona DS919MG, Savox SV1232MG), encoder-measured at 100 Hz updates: about 8 Hz bandwidth (90°
  phase lag) at small amplitude, falling at larger amplitudes; one 10 ms sample of start delay [DW].
- **Load changes the response:** a GWS S03T's closed loop was identified from 0.1–10 Hz multisines with 200 g and
  450 g loads, and differed between them [HWG].

## 4. Hobby-servo models usable in MuJoCo

- The UMN transfer functions above are closed-loop, command to angle, unloaded. They describe a servo on its own,
  not a servo carrying a head [UMN, I].
- Hwang et al. identify an RC servo's closed loop per load inertia, with the controller unknown [HWG].
- No published hobby PWM servo model gives a deadband, a proportional band and a torque limit fitted from data. The
  prior note found none either (`2026-11-02-literature-simulation.md` §1).
- BAM (Rhoban) fits friction models from a pendulum and ships a MuJoCo binding, but only for Dynamixel and eRob
  servos (prior note).
- ElRobotSysId (Apache-2.0) fits Feetech ST3215 bus servos, not PWM ones: a P loop "with dead zone and duty cap" and
  about 80 ms of delay. https://github.com/robomotic/ElRobotSysId [B]
- The repo's own route for the micro servo is `model/servo_fit.py` (#625). It films the horn and fits stall torque,
  no-load speed, armature and delay with `mujoco.sysid`. Its docstring leaves kp inferred, because the half-degree
  band is "finer than a video reads". A band near 10° would not be [I].

## What this means for the sim's band and frame rate [I]

- The model's 0.5° matches the spec sheet's deadband (5 µs ≈ 0.4–0.45°), not a proportional band.
- The analog IC class reaches full drive near 100–130 µs of error, about 8–12° at the Core's scale. If the MG996R is
  that kind, its band is about 20 times the model's.
- The ring scales with the band as 1/√band at the same reflected inertia:
  - 4° (the issue's run that just passed): tilt about 14.5 Hz, pan about 8.8 Hz;
  - 12°: tilt about 8.4 Hz, pan about 5.1 Hz.
- The cheapest measured servos ring at 4–11 Hz unloaded [UMN], under the model's 41 and 25 Hz even before a head's
  inertia is on them.
- A wider band also changes the deadband's share: drive starts at the minimum pulse (about 18% duty at 50 Hz), not at
  zero.
- A faster frame is not a softer servo for an analog MG996R. The band in µs scales with the frame period. Rates past
  50 Hz have no source for this servo. Futaba allows 14 ms (71 Hz) for "any type of servos", and UMN saw analog servos
  misbehave near their limits.
- The Core's LEDC can make any of these rates, but three places in the code fix 20 ms.

## Still unknown

- Whether bought MG996Rs are analog (AA51880) or digital. That decides whether the frame changes the band.
- The MG996R's real deadband (1 or 5 µs) and the stretch values behind its band. Only class figures exist.
- Its µs per degree: Tower Pro gives 159° of travel but no pulse range.
- Any measured MG996R step or frequency response with numbers, and how it changes with a head-sized load.
- Bench steps of a few sizes on the existing filmed-horn rig (`model/servo_take.py`, `model/servo_fit.py`) would read
  a band of several degrees. The jump from a still horn to full speed between small and large steps shows where the
  band ends.
