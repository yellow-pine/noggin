# Electrical engineering for the Mech (#51)

Researched 2026-11-02. Purpose: the one-pack power budget, brownout, joint wiring, Wi-Fi in the cranium and a pack-voltage reading for the Mech, inside #51's fixed parts.

Builds on `2026-10-31-electrical.md` (part figures), `2026-10-31-radio.md` and `model/electrical.py` (DC worst case: 5.34 A from the pack with every servo at stall; servo rail 3.65 V at a 5.8 V pack). None of that is repeated here.

Sources:
- [DS] Espressif, ESP32-C3 Series Datasheet v2.4. https://documentation.espressif.com/esp32-c3_datasheet_en.pdf
- [HDG] Espressif, ESP Hardware Design Guidelines, ESP32-C3: schematic checklist https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c3/schematic-checklist.html and PCB layout https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c3/pcb-layout-design.html
- [KC] ESP-IDF v5.4, `components/esp_system/port/soc/esp32c3/Kconfig.system`. https://github.com/espressif/esp-idf/blob/v5.4/components/esp_system/port/soc/esp32c3/Kconfig.system
- [MP] MicroPython v1.23.0, `ports/esp32/modmachine.c`. https://github.com/micropython/micropython/blob/v1.23.0/ports/esp32/modmachine.c
- [CB] CyberBrick_Controller_Core: `src/app_rc/bbl/servos.py`, `motors.py`, `app/rc_main.py`. https://github.com/CyberBrick-Official/CyberBrick_Controller_Core
- [C] Chen & Rincón-Mora 2006, IEEE Trans. Energy Conversion 21(2):504. https://doi.org/10.1109/TEC.2006.874229, author's PDF https://rincon-mora.gatech.edu/publicat/jrnls/tec05_batt_mdl.pdf
- [BQ] TI BQ2970 datasheet, a 1-cell protector used as an example: the pack's own protector IC is not named. https://www.ti.com/lit/ds/symlink/bq2970.pdf
- [TI] Kinnaird, TI SLVAFT0 (2024), Bulk Capacitor Sizing for DC Motor Drive Applications. https://www.ti.com/lit/pdf/slvaft0
- [MC] Condit, Microchip AN905 (DS00905B, 2010), Brushed DC Motor Fundamentals. https://ww1.microchip.com/downloads/en/AppNotes/00905B.pdf
- [PG] Bambu B-PG001 spec sheet, as quoted in `2026-10-31-electrical.md`.
- [N] NASA-STD-8739.4A (2016), Crimping, Interconnecting Cables, Harnesses, and Wiring. https://nepp.nasa.gov/files/27631/nstd87394a.pdf
- [IPC] IPC-TM-650 2.4.3.1C (1991), Flexural Fatigue and Ductility. https://www.electronics.org/sites/default/files/test_methods_docs/2.4.3.1c.pdf
- [L] Liang et al. 2024, Sensors 24(4):1109, an FE study of moving cables. https://doi.org/10.3390/s24041109 (PMC10893113)
- [CA] Castro et al. 2026, J. Microwaves Optoelectron. Electromagn. Appl. 25(2). https://doi.org/10.1590/2179-10742026v25i2298896
- Paywalled, not read: IEC 61960-3 (AC vs DC internal resistance), IEC 62133-2, IPC/WHMA-A-620 [A].

## 1. The pack under servo pulses

- **Two parts to the sag.** A Li-ion step response is an instant drop across R_series, plus two RC terms with short and long time constants [C].
  - Fit for an 850 mAh polymer cell [C eq. 3–6]: τ_S = 0.047 Ω × 704 F ≈ 33 s and τ_L ≈ 0.050 Ω × 4475 F ≈ 220 s (computed from the fit).
  - A 20–200 ms servo start therefore sees only R_series [I].
- **Resistance rises near empty.** Every parameter is "approximately constant over 20–100% SOC and change[s] exponentially within 0–20% SOC" [C].
  - R_series = 0.1562·e^(−24.37·SOC) + 0.0745 Ω: 75 mΩ from mid charge down to 10%, 231 mΩ at empty [C eq. 3].
  - For our 2S pack at empty: 2 × 0.23 + 0.04 ≈ 0.50 Ω [I]. `model/electrical.py` uses a constant 0.21 Ω, built from a 1 kHz AC figure.
- **Open-circuit voltage knee.** OCV falls steeply only below about 10% SOC [C eq. 2]: per cell about 3.68 V at 10%, 3.52 V at 5% and 2.65 V at 0% (computed from the fit).
- **The protector trips on loaded voltage, after a delay.**
  - A typical protector's over-discharge delay is factory-set at 20, 96, 125 or 144 ms, ±20% [BQ]. The pack's own figure is unpublished.
  - Near empty, a start of several servos (0.5 Ω × amps) pulls the cells under the 5.8 V cutoff for longer than that delay. The whole Mech then goes dark mid-gesture before the open-circuit voltage reaches 5.8 V [I].
- **Brownout.**
  - ESP-IDF resets the C3 at level 7 = "2.51V" by default (levels 2.51–3.27 V, "estimates") [KC].
  - The chip wants 3.0–3.6 V at ≥0.5 A cumulative [DS Table 5-2], and Wi-Fi transmit peaks at 335 mA [DS Table 5-7].
  - Espressif suggests a supervisor at about 3.0 V for slow or unstable supplies [HDG].
  - The Core runs off VBAT through a regulator. VBAT stays above 3.3 V plus dropout until the pack's protection opens, so the pack cut comes before an ESP brownout [I].
  - MicroPython 1.23 maps `ESP_RST_BROWNOUT` to `PWRON_RESET` [MP], so a Core cannot tell a brownout from a power-on.

## 2. Servo current

- **Start current is stall current.** In a permanent-magnet DC motor, current is linear in torque [MC].
  - At start (no back-EMF yet) the motor draws I = V/R, the stall current: about 0.57 A at 5 V, interpolated between 0.55 A at 4.8 V and 0.65 A at 6 V [PG].
  - It decays toward the 50–60 mA running figure as speed builds [I].
  - A held load draws in proportion to its torque, up to stall. The servo cuts power after 5 s of continuous stall [PG].
- **Bulk capacitance cannot carry a start.**
  - The guideline is C > k·ΔI·T/ΔV, with k ≈ 3 for real ESR [TI eq. 6], meant for PWM ripple. A rule of thumb is 1–4 µF per watt [TI §2].
  - Carrying one 0.57 A start for 20 ms with a 0.3 V sag needs about 40 mF [I].
  - So a capacitor smooths the servos' internal PWM ripple and lead inductance. Only firmware can limit the starts, and a new capacitor is outside #51's parts anyway.
- **Each Core's budget is shared.** Both Shields hang off one pack and one switch, so the starts of both Cores add on the pack's R. Per Core: 60 mA shield standby plus up to 335 mA transmit burst [model inputs].

## 3. Signals and grounds

- **Servo ports.** They are GPIO 3, 2, 1, 0 [CB servos.py], ADC1 channels 3–0 [DS pin table]. GPIO 4/5 drive the Shield's motor-driver inputs [CB motors.py]. On the RC transmitter, GPIO 0–5 are the stick ADCs [CB rc_main.py].
- **No signal crosses between boards.** The Cores talk over Wi-Fi (ADR 0005), and the only shared conductor is the pack's negative.
  - A servo's signal is referenced to its own lead's ground, which also carries its return. 0.57 A in 250 mm of 26 AWG drops about 19 mV, which is negligible against 3.3 V logic thresholds [I].
  - A ground loop forms only if both Cores are on USB to the Mac at once [I].
- **Lead length.** At 250 mm and 50 Hz, a pulse-width signal is insensitive to edge ringing. Servos read pulse width at µs resolution [I]. I found no primary source specific to servo leads.

## 4. Leads through pan and tilt

- **Static rules** [N]:
  - Bend radius for a completed harness without coax: optimum 10 × OD, minimum 3 × OD (Table 7-1).
  - "Wires exiting from connectors shall be stress relieved" (7.2.20).
  - No splices "where flexing may occur" (7.2.36).
  - Solder-wicked strands are rigid up to the wick line, and "wire movement concentrates stress at the point where wicking stops" (13.3.1).
  - Supports keep flexing off sharp edges (7.2.11, 7.2.30).
  - AWG 24 and larger is preferred, high-strength alloy at 24 and below (7.2.8–9). The servo leads are thinner [I].
- **Fatigue.**
  - Copper strands fail by strain-life (Manson-Coffin). "Larger mandrel diameters result in longer cyclic life and smaller diameters in shorter life" [IPC 2.4.3.1 §5.2.1, §5.3].
  - Surface strain per strand is about r/(R + r): a 0.08 mm strand sees 0.8% at R = 5 mm and 0.2% at R = 20 mm [I]. The servo lead's strand count is unpublished.
- **Fixing points.** In an FE study of moving cables, more fixing points in the moving span add bending moments; the optimum was two, one at each end [L].
- **Service loop or slip ring.** For limited rotation (pan and tilt under ±90°), a loop or a twist spread along the axis does the job [I]. A slip ring is for continuous rotation, adds contacts, and is a new part [I].

## 5. Wi-Fi from a Core inside the cranium

- **Clearance.** Espressif asks for "a clearance of at least 15 mm … in all directions" between the antenna and the housing [HDG layout]. Keep the antenna away from radiating parts and lines [HDG layout], and test the end product's throughput and range [HDG layout].
  - The Core's antenna type (PCB trace or chip) is not published [I]. Check it on the board.
- **Plastic walls cost little.** At 3.5 GHz, fully printed PETG measures εr 2.69, tan δ 0.0070; PLA εr 2.89, tan δ 0.0110; a carbon-filled filament εr 3.54, tan δ 0.020 [CA].
  - A 2 mm PLA wall attenuates about 0.01 dB at 2.4 GHz [I, from CA].
  - The risk is detuning by material inside the 15 mm zone, and metal: servo motors, the pack, lead bundles and the NdFeB magnets (nickel-plated, conductive) [I].
  - The pigment in black PETG is unpublished. If it is carbon black, expect losses toward the carbon-filled figure [I, CA].

## 6. Reading the pack voltage

- **The ADC.** ADC1 is GPIO 0–4 and ADC2 is GPIO 5 [DS]. Use ADC1: "ADC2 is not factory-calibrated, and ADC2 of some chip revisions is not operable" [HDG].
  - Range at ATTEN3 (11 dB) is 0–2500 mV with ±35 mV total error after calibration [DS Table 5-6].
  - The linearity figures are measured with a 100 nF cap at the pin and Wi-Fi off [DS Table 5-5]; average several samples [DS note]. "Add a 0.1 µF filter capacitor" at the ADC pin [HDG].
- **What the build has.**
  - The Shield has no voltage sense (`2026-10-31-electrical.md`).
  - The eyes Core uses all four ADC1 servo pins. The neck Core's port 4 (GPIO0, ADC1_CH0) is free. GPIO4 (ADC1_CH4) is tied to the Shield's motor driver [CB].
  - Reading the 8.4 V pack needs a divider ≤ 2.5/8.4. For example, 100 k / 39 k from VBAT after the switch: 2.36 V at 8.4 V, 1.63 V at 5.8 V, ±0.13 V at the pack, 60 µA drawn only while switched on [I].
  - **That is two resistors and a capacitor: parts #51 does not own.**
  - The 5 V servo rail on the port's + pin is regulated, so it says nothing until VBAT falls into dropout [I].

## Practices for #51

1. **Budget servo starts, not stalls.**
   - Start at most N servos per 20 ms frame across both Cores. Stagger the rest by one frame each, where a frame is the 50 Hz period on which commands already land.
   - Size N in `model/electrical.py` so that, on an empty pack (R ≈ 0.5 Ω), the loaded voltage stays above 5.8 V plus margin, counting the Cores' standby and transmit current.
   - The noggin service offsets the two Cores' gesture starts by a frame [§1, §2].
2. **Rest short of every hard stop, and balance static loads.**
   - A servo at rest should draw its 8 mA standby. One held against a lid bind or the big head's weight draws up to 0.57 A, and the 5 s stall cut drops it [PG, MC].
   - Put the head's centre of mass over the tilt axis for current as well as torque.
3. **Model the pack honestly** [C, BQ]:
   - R_series as a function of SOC (Chen's fit, scaled to 2S plus 40 mΩ).
   - Cutoff as a loaded-voltage event: open-circuit voltage minus I·R(SOC) under 5.8 V for longer than the protector's delay. A 5.8 V source is not the right model.
4. **Detect pack cuts within the fixed parts.**
   - Both Cores' beacon uptimes resetting together, with no `reboot` sent, means a pack cut.
   - The noggin service logs it and `noggin status` shows it. `reset_cause()` cannot tell a brownout from a power-on [MP].
5. **If a divider is allowed (Conflict 1):**
   - Neck Core port 4 signal pin (GPIO0/ADC1_CH0): 100 k/39 k from switched VBAT, 100 nF at the pin, 11 dB attenuation.
   - Sample many times while no servo moves. Park on the resting voltage with hysteresis. Never use ADC2 [DS, HDG].
6. **Cross the joints with the fewest conductors.**
   - Split the Y lead after the joint, so one pair crosses.
   - Keep solder joints (the hand-soldered Y), splices and crimps out of the flexing span.
   - Clamp each flexing span at its two ends only, with strain relief at each connector exit [N 7.2.20, 7.2.36, 13.3.1; L].
   - Counting conductors favours candidate (a), boards in the head: one power pair plus the pan (and possibly tilt) servo lead cross. Candidate (b) has five servo leads (15 conductors) crossing both axes [I, from #51's servo map].
7. **Flex geometry.**
   - Bend radius at least 10 × lead OD (static optimum [N Table 7-1]; flexing wants more [IPC]).
   - Pan: run the leads along the pan axis, so rotation becomes twist spread over the longest free length.
   - Tilt: a loop around the tilt axis whose radius breathes, never a bend at a clamp edge.
   - No slip ring [I].
8. **Antenna.**
   - Keep the Core's antenna end 15 mm clear of the shell, servos, magnets, the pack and lead bundles [HDG], pointing up or back into the cranium's empty volume.
   - Keep the skeleton's black PETG out of that zone if its pigment is carbon [CA, I].
   - Check RSSI with the shell on [HDG].
9. **One USB cable at a time** when both Cores are on the pack [§3].

## Conflicts with #51

1. **Low-battery park vs "the one new purchase: magnets".**
   - #51 parks only "if a Core can read the pack voltage". No Core can: the Shield has no sense, and the ADC tops out at 2.5 V [DS, HDG, §6].
   - Proposed: allow a two-resistor divider plus 100 nF (cents) on the neck Core's free port 4. Otherwise drop the park and keep only Practice 4's cut detection.
2. **"Runs to the pack's 5.8 V cutoff."**
   - Near empty, the pack's internal resistance about triples [C]. A multi-servo start then trips the protector on loaded voltage within 20–144 ms [BQ], so the Mech dies mid-gesture before the open-circuit voltage reaches 5.8 V. The 5 V servo rail falls under the servos' 4.8 V minimum even earlier (3.65 V at cutoff in `model/electrical.py`; the designer's "sluggish when the battery is low").
   - Proposed: run to the resting voltage at which Practice 1 still allows one start above 5.8 V. Park there with Conflict 1's divider; otherwise accept the hard cut.
3. **Not #51, but its sources.**
   - `docs/build/wiring.md` still calls one pack per Shield a planned edit ("2 × 2.6 A > 3 A"). #51 drops it. One pack holds only under Practice 1's start budget.
   - `model/electrical.py`'s constant 0.21 Ω pack resistance understates the empty pack by about 2.4× [C].

Unverified: the pack's cells and protector IC, the Shield's regulator type, the Core's antenna type, the servo lead's strand count, and the black PETG's pigment. Chen's fit is for an 850 mAh polymer cell, not our 14500 cells. I found no peer-reviewed open study of hobby servo current or of flex life for thin PVC leads.
