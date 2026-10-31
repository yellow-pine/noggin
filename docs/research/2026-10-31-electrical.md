# Electrical facts (primary sources; fetched 2026-10-31)

Abbrevs: SERVO = https://uk.store.bambulab.com/products/9g-servo-motor-with-clutch-protection (Product Specifications table); SHIELD = https://uk.store.bambulab.com/products/remote-control-receiver-shield-1pcs and its spec PDF https://store.bblcdn.com/s1/default/fe6984b2ca8845929a2b6984eea619aa/Remote_Control_Receiver_Shield_-_XA004.pdf; MAN = Receiver XA003-XA004 User's Manual (https://store.bblcdn.com/s1/default/c0fddf0bd28040b8857083efc56e64fc/Remote_Control_Receiver-XA003-XA004_User_Manual.zip); CORE = https://us.store.bambulab.com/products/multi-function-controller-core-1pcs; BAT = https://us.store.bambulab.com/products/14500-7-4v-800mah-li-ion-battery-1pcs (same figures in https://store.bblcdn.com/s2/default/ea2b2a3f6cbd44ce940642d1c1f9d3e0/14500_7.4v_800mah_li-ion_battery_1pcs-pc003.pdf).

## 1. Servo PG001/PG002 (SERVO)
- Operating voltage 4.8-6 V DC. Pulse 500-2500 us, PG001 180+10 deg; CCW for 1000->2000 us.
- No-load speed <=0.14 s/60 deg @4.8 V, <=0.12 s/60 deg @6.0 V.
- No-load current <=50 mA @4.8 V, <=60 mA @6.0 V. Stall current <=550 mA @4.8 V, <=650 mA @6.0 V. Standby 8 mA @6.0 V (this is the only idle figure; no separate holding current published).
- Stall torque >=1.0 kgf.cm @4.8 V; weight 16 g.
- Lead length and connector: NOT published as text (only a "Servo Ports Pin Definition" image). Shield side is a 3-pin header (MAN).

## 2. Receiver shield XA004 (SHIELD, MAN)
- Input 7.4-12.6 V DC (2S-3S) via XH2.54 2-pin. Standby 60 mA, working 200-300 mA, max 3 A (whole shield).
- Outputs: 4 servo ports S1-S4, 2 DC motor, 2 WS2812. Servo ports "universal 5V servo", so a regulator exists, but its type and servo-rail current limit are NOT published. Do not assume 3 A reaches servos.
- GPIOs are not in the store docs; from CyberBrick's servos.py: S1..S4 = GPIO 3,2,1,0, PWM 50 Hz (quoted in docs/research/2026-10-31-hooks-serial-launchd.md B1, source github.com/CyberBrick-Official/CyberBrick_Controller_Core src/app_rc/bbl/servos.py).
- Battery-voltage ADC/sense: none documented (no mention in SHIELD, MAN, CORE). Unknown.

## 3. Battery PC003 (BAT)
- 7.4 V 800 mAh; max continuous discharge 3 A (about 3.75 C).
- Protection: overcurrent 20 A +-3 A; over-discharge cutoff 5.8 V +-0.08 V; overcharge 8.4 V +-0.05 V; short-circuit protection. Charge 160 mA std, 800 mA max.

## 4. PurpleShark three-part mech
- Two Cores + two shields, one transmitter (03-mouth/page.md Q&A "Two receivers pair to one transmitter"; 02-pan-tilt/page.md "a second Core / second shield"). 7 servos: 4 eyes, 2 pan-tilt, 1 mouth.
- Receiver 1 (remote-config-eyes-pandt-jaw.json, PWM1-4): L lid, L eye, R lid, R eye (range 75-120, 60-120, 70-120, 75-120).
- Receiver 2: PWM1 tilt (20-150), PWM2 mouth (0-180), PWM3 pan "rotate" (40-160). Pan-tilt PDF: tilt (left) servo top-left, pan (right) top-right; PandT-only JSON has no mouth. Mouth PDF: "3rd position on the second receiver" (port numbering by the JSON, PWM2 vs PDF "3rd" differ; check).
- Single battery: a Y adapter (hand-soldered, battery box XA012 + XH2.54 leads) powers both shields; a second battery is optional (02-pan-tilt PDF p1, step 2). Designer notes servos get "sluggish when the battery is low."

## 5. Core (CORE, MAN)
- Type-C input DC 5 V; separate VBAT input 3.7-12.6 V (via shield). Docs never say USB reaches the servo rail; the Core/shield split implies it does not, matching docs/build-notes.md, but this is inference plus the board's observed behaviour, not a stated primary fact.
- LEDC: ESP32-C3 has 6 channels, 4 timers (MicroPython esp32 quickref, quoted in research B4). Four servos at 50 Hz fit.
## Clutch
Source: Bambu spec sheet, model B-PG001 (https://cdn.shopify.com/s/files/1/0611/4036/9460/files/9g_Servo_Motor_with_Clutch_Protection.pdf, fetched 2026-10-31), items 5, 7, 28:
- Clutch Protection: ">=0.9 kgf.cm at 4.8V" (about 88 mN.m). This is the only slip figure published. No 6.0 V value.
- Rated torque: >=0.32 kgf.cm at 4.8 V, >=0.4 kgf.cm at 6.0 V.
- Stall torque: >=1.0 kgf.cm at 4.8 V, >=1.2 kgf.cm at 6.0 V.
- Current protection: power cut after 5 s continuous stall (Chinese text only).
- Not published: holding torque, and any statement on whether the clutch protects against external back-driving. The sheet gives the clutch only as a torque number. Reading it as a gear-train overload limit that applies in both directions is inference.
- Not checked: the store page text (JS-rendered, WebFetch returned 402), the Bambu wiki and the MakerWorld listing.

## SPICE inputs (#152, fetched 2026-10-31)
- Pack internal resistance: not in the PC003 sheet. A 14500 800 mAh cell datasheet gives internal impedance <= 85 mohm
  (AC 1 kHz; https://www.dnkpower.com/wp-content/uploads/2022/08/14500-battery-datasheet.pdf); the pack's own cells
  are not named, so model/electrical.py takes 2 x 85 + 40 mohm (protection MOSFETs) as inferred.
- Switch board XA007 (SW101): max input 12.6 V, XH2.54 2P, 3 A permissible (spec table on
  https://us.store.bambulab.com/en/products/power-switch-module-with-2pin-xh2-54-connector-1pcs). No contact resistance published.
- Shield XA004 servo ports: "universal 5V servo" only; Core XA003: VBAT 3.7-12.6 V. Neither regulator is named.
- ESP32-C3 supply: VDD 3.0-3.6 V recommended (ESP32-C3 datasheet, https://documentation.espressif.com/esp32-c3_datasheet_en.pdf).
  Brownout reset: ESP-IDF default level 7, "2.51V", with the note that the levels are estimates
  (https://github.com/espressif/esp-idf/blob/v5.4/components/esp_system/port/soc/esp32c3/Kconfig.system); MicroPython's
  ports/esp32/boards/sdkconfig.base does not change it. CyberBrick's firmware config is not published.
- PySpice 1.5 loads `libngspice{}.dylib` / `libngspice{}.so` by bare name, overridden by NGSPICE_LIBRARY_PATH
  (PySpice/Spice/NgSpice/Shared.py; FAQ https://pyspice.fabrice-salvaire.fr/releases/v1.5/faq.html). Ubuntu's
  libngspice0 ships only libngspice.so.0; libngspice0-dev adds libngspice.so
  (https://packages.ubuntu.com/noble/amd64/libngspice0-dev/filelist). Homebrew's libngspice is in /opt/homebrew/lib.
