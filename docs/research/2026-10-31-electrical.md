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
