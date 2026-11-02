# noggin

An animatronic eye mech on a desk that reacts when Claude Code finishes a response or needs attention. This glossary covers the physical mech, the board program, and the Mac-side process that connects them.

## Language

### Hardware

**Mech**:
The physical animatronic: two eyeballs, two eyelid pairs, the pan-tilt neck and the mouth, seven servos on two Cores, built from the designer's eyes, pan-and-tilt and mouth designs (the site's Credits page, docs/credits.md).
_Avoid_: robot, head, beast, eye mech

**Next Mech**:
The Mech being designed to follow today's (#51): our own design on the Cores, Shields and servos we own, a Skeleton
that wears a Character. Today's Mech stays the supported build until the next one is built.
_Avoid_: Mech 2, new Mech

**Skeleton**:
The next Mech's structural parts, the same under every Character: the eye gimbal, the jaw, the neck, the Torso and the
electronics mount, in black PETG.
_Avoid_: frame, chassis, core

**Torso**:
The next Mech's base: the Skeleton's compact body in the shirt and collar under the neck, holding the pack lying low and
the neck mount with the pan servo; its bottom is the foot the Mech stands on.
_Avoid_: base plate (today's Mech's part), body, stand

**Base candidate**:
One way to carry the next Mech's boards and pack, ranked against the other before Cansin picks: (a) the boards on a
board tray riding the head behind and below the tilt Pivot, (b) the boards on a static board tower rising on the pan
axis into the cranium. In both the pack lies low in the Torso.
_Avoid_: option, variant, layout

**Eye gimbal**:
The Skeleton's linked eyes: each eyeball core turns up/down inside a yoke that turns left/right, one servo turns both
yokes through a tie-bar, one turns both cores through push-rods, and each lid turns about the up/down axis on a servo
of its own. The eyeball caps (Shells) sit on the cores.
_Avoid_: eye mech, eye frame, linked eyes (as a part name)

**Shell**:
One cosmetic part a Character puts on the Skeleton (the head, an eyeball cap, a pupil, a lid cover, the collar), in
PLA Pure, held on by magnets.
_Avoid_: skin, cover, cosmetic

**Shell set**:
Every Shell of one Character, pulled off and pressed on together to swap Characters.
_Avoid_: kit, costume

**Character**:
Who the next Mech looks like, Morty or Bart: its Shell set and its gaze speed, picked in the noggin service's settings.
_Avoid_: face, persona, theme

**Core**:
The controller board (ESP32-C3 running MicroPython) that drives the servos; the noggin service reaches it over its Link.
_Avoid_: board, receiver, controller, ESP

**Shield**:
The expansion board the Core sits on; carries the servo ports and the power input; one per Core.
_Avoid_: receiver, receiver shield, product codes

**Pack cut**:
The battery pack's protection switching the pack off under a load it can no longer carry (near empty), so every Core
and servo goes dark at once. The noggin service knows one by both Cores restarting together without a reboot it sent;
the cure is to charge the pack.
_Avoid_: brownout (the Core's own reset, which a pack cut comes before), power loss, crash

**Servo**:
One of the seven actuators, named by what it moves: left lid, left eye, right lid, right eye (eyes Core); tilt, mouth, pan (neck Core).
_Avoid_: channel, PWM, actuator, motor

**Link**:
The connection between the noggin service and one Core: Wi-Fi (UDP datagrams, found by the Core's beacon) first, the USB serial port as fallback. See docs/adr/0005.
_Avoid_: serial, REPL, cable, connection, relay

**Mech stand-in**:
The Core's own program on its MicroPython's unix port, with small machine, network and socket stubs, beside the real noggin service: CI's stand-in for the Mech in the Link's live checks (mech/, `just mech`).
_Avoid_: emulator, simulator, fake Core

### Motion

**Pose**:
The angle of every servo at one instant.
_Avoid_: position, frame, state

**Start budget**:
How many servos one Core lets jump at full speed at once (two): a jump draws stall current until the servo arrives, so any further jump waits for one to finish.
_Avoid_: stall budget, current limit, power budget

**Gesture**:
A named, timed sequence of poses the Core plays to completion, such as eureka or attention.
_Avoid_: animation, routine, effect, cue, sequence

**Eureka**:
The gesture for "Claude just thought of something great": played when Claude Code finishes a response.

**Attention**:
The gesture for "Claude needs you": played when Claude Code is waiting on the user.

**Bored**:
The gesture for "you walked away": played when Claude Code has been waiting on the user for a while.

**Wince**:
The gesture for "something went wrong": played when a Claude Code turn fails with an error.

**Thinking**:
The background state while any session is mid-turn: half lids, slow eye drifts, occasional blinks. Not a gesture; gestures interrupt it.
_Avoid_: working, busy, idle animation

**Rest**:
The state when no session is mid-turn and no gesture is playing: lids at their rest level, eyes centred, servos holding, the mech still but for an occasional blink (one every few seconds: a face held still reads as lifeless).
_Avoid_: idle, sleep, neutral, home

**Intensity**:
How big a gesture plays, 1 to 3. For eureka it follows the Tier of the turn that ended.

**Tier**:
The size class of a turn by how long Claude worked on it: small under 20 s, normal up to 3 min, big beyond.
_Avoid_: length, level, duration class

### Control

**Trigger**:
A request for a gesture arriving at the noggin service, normally from a Claude Code hook.
_Avoid_: hook, event, signal, poke

**Noggin service**:
The always-running Mac process that owns the Link and turns Triggers into gesture commands for the Core. Just "noggin" in commands.
_Avoid_: daemon, server, agent, bridge, puppeteer

**Busy**:
The noggin service's state while a gesture is playing; any Trigger arriving while Busy is dropped.
_Avoid_: cooldown, debounce, lock

**Turn**:
One session's work from the user's prompt to Claude's answer, timed by the noggin service to pick a Tier.
_Avoid_: request, response, round

**Mute**:
The noggin service setting that drops every Trigger until switched back on.
_Avoid_: pause, disable, sleep mode

**Program**:
The MicroPython files on the Core's filesystem. The stock program is the vendor's remote-control app; the eye program is ours and replaces it.
_Avoid_: firmware, app, code, sketch

**Firmware**:
The MicroPython image flashed into the Core by the vendor's tools. Never modified by this project.
_Avoid_: program, image, OS

### Model

**Model**:
The Mech as code, 1:1 with the physical Mech: our CadQuery parts (model/printed) and hardware Envelopes
(model/envelopes.py), placed by model/geometry.py and model/stages.py; MuJoCo simulates them from one MJCF per
document (model/mjcf.py, docs/adr/0007), and Blender renders the pictures from MuJoCo's Trajectories.
_Avoid_: twin, digital twin, CAD, simulation

**Stage**:
A cumulative build state of the Mech, the Sub-assemblies placed at frames (geometry.STAGES): Stage 1 = base + eyes (the desk eye bracket's stem in the plate's slot), Stage 2 = base + stack + eyes on the tilt arm, Stage 3 = Stage 2 + mouth (the full Mech). Simulation, photos and reports run per Stage.
_Avoid_: part, module, phase, top assembly

**Web viewer**:
The page that shows a document of the Mech in 3D from Blender's glTF, turned and zoomed by the reader
(docs/adr/0008): on the Site the Next Mech alone (docs/adr/0019); locally also each Stage, playing its gestures and
the Tour, Stage 3 exploded.
_Avoid_: twin viewer, web app, demo

**Site**:
The project's public web site, built by Astro Starlight from the repo's Markdown where it stands (the `site/` package,
docs/adr/0013): a landing page at its root, the build guide, how to use the Mech, the Model and the reference docs
(docs/adr/0009); pictures and the Web viewer of the Next Mech alone, never of today's (docs/adr/0019). The README is
for contributors and stays on GitHub.
_Avoid_: docs site, homepage, Pages (the host)

**Numbers from the code**:
The values a doc shows that the code owns (the behaviour table, each Stage's parts and servos, the wiring, the picture
sizes and colours): `macros.py` derives them, and the Site puts each where the doc's hidden `<!--{{ name }}-->` marker
stands; GitHub shows a link to the Site's table instead (docs/adr/0009, 0013).
_Avoid_: generated docs

**Release**:
One version of the whole repo, noggin vX.Y.Z: the Core program, the noggin service, the Model and the Site together,
tagged vX.Y.Z on main, its notes on its GitHub release (docs/adr/0010, 0017).
_Avoid_: build, drop, version of one part

**Docs version**:
The Site's docs as one Release had them, built from its tag under /noggin/vX.Y/ (the newest patch of each minor) and
kept as a release asset; **latest** is main's, at /noggin/. The header's switcher lists them from /noggin/versions.json.
The sim reports are the live Site's in every version (docs/adr/0014).
_Avoid_: docs snapshot, archived docs

**Bot App**:
The repo's own GitHub App, which the workflows act as when they open a PR or tag a Release, so its
checks, review or Release Assets run as they would for a person's (docs/adr/0010, 0017).
_Avoid_: release App, bot token

**Hero**:
The Mech's showcase loop: Stage 3 talking, the first clip of the Tour (shown nowhere until the clean-room Mech).
_Avoid_: banner, idle loop

**Tour**:
The web viewer's default: every clip of the Stage in turn, the Hero first where the Stage has one, round and round;
a gesture picked plays once, then the Tour goes on.
_Avoid_: hero (for the viewer's default), demo, autoplay

**Sub-assembly**:
An ownership unit that owns its parts exactly once (base, stack, eyes, mouth) and is placed into Stages at a frame (model/stages.py).

**Envelope**:
Our simple CadQuery stand-in for a piece of bought hardware (servo, Horn, Shield, Core, switch board, battery): its interfaces at the STEP's numbers, its body a few boxes and plates (model/envelopes.py).
_Avoid_: proxy, dummy, placeholder

**Horn**:
The printed arm on a servo spline; the driven link of every chain.
_Avoid_: arm, lever

**Bar**:
A straight link between two Pivots: eyeball bar, lid bar, tilt bar, pan bar, jaw bar.
_Avoid_: rod, linkage

**Crank**:
The lid crank: the lid bar with its lid end stepped 3 mm, turning Horn rotation into upper lid rotation.

**Printed part**:
A part we print, by our name (the designer's file names are history: docs/credits.md, docs/research):
- eye bracket: the frame the eye mech hangs on (eyeball forks, lid pins, servo bracket feet, the jaw rail) and its stem;
  desk eye bracket: Stage 1's, without the jaw rail, its stem 5 mm shorter;
- L / R servo bracket: one side's lid servo and eye servo, its feet on the eye bracket;
- L / R eyeball: turns in the eye bracket's fork; pupil: the disc on its front;
- upper lid, lower lid: the two lid shells of an eye on the eye bracket's lid pins, the upper one nested inside;
- eyeball bar, lid bar, lid crank: the eye mech's Bars from the Horns to the eyeball, the lower lid and the upper lid;
- wire keeper: holds the eye servo leads down on the base plate's cable holder posts;
- base plate: carries the pan pivot, the pan servo mounts, the Shields' standoffs, the battery box and the switch board holder;
- bearing block: the ring the pan turntable turns on in the base plate's recess;
- pan turntable: turns on the pan axis and carries the tilt servo tower and the upright;
- upright: the post carrying the tilt pivot, its lever driven by the pan bar;
- tilt arm: turns on the tilt pivot, the eye bracket's stem clamped in its window, its lever driven by the tilt bar;
- pan servo lead mount, pan servo tail mount: the pan servo's two mounts, the lead mount at the shaft end arched to let the
  servo lead out;
- wire holder: holds the leads down on the base plate's two wire holder posts;
- top jaw (screwed under the eye bracket, the jaw hinge pins), bottom jaw (turns on them), jaw servo mount (on the eye
  bracket's rail), jaw bar (the jaw Horn to the bottom jaw's lug).
_Avoid_: the designer's file names, version suffixes, plain / cutout / regular

**Coupon**:
A test piece we print to find a fit on our printer and filament before a Printed part relies on it, such as the
clearance coupon's pins and magnet pockets; not part of the Mech.
_Avoid_: test part, calibration print, sample

**Take**:
One filmed run of a servo through the servo test's moves at one known load, and the record made of it: when each
command was written and where the marked Horn was at each frame. The servo's values in the Model are fitted to Takes.
_Avoid_: clip, recording, trial, run

**Pivot**:
A revolute axis between two parts; in the Model, a MuJoCo joint (model/mjcf.py) and a joint of the four-bar
kinematics that pose a horn angle without simulating (model/linkage.py).
_Avoid_: hinge, axle

**Singularity margin**:
How far a four-bar is from its toggle over its Horn's range: the smallest singular value of the loop's constraint
Jacobian over its free Pivots, in mm of pin per radian; zero at the toggle, where a Bar and its lever line up.
_Avoid_: dead point margin, condition number

**Port**:
A named point on a connector where a cable plugs in.
_Avoid_: socket, header

**Corridor**:
A lead's route in the Model: a polyline from one Port to the other through waypoints clipped to the parts that hold the
lead, so it rides pan and tilt (model/cables.py). MuJoCo carries it as a tendon no longer than the lead.
_Avoid_: harness, cable path, routing

**Flexing span**:
The stretch of the next Mech's leads that crosses a moving Pivot (pan or tilt), clamped at its two ends only and bent
no tighter than ten times the thickest lead's diameter.
_Avoid_: service loop, cable loop, slack

**Trajectory**:
One Gesture (or the README hero) on one Stage as MuJoCo plays its servo commands through the servos' own dynamics:
every part's place in the world per 100 ms frame (model/trajectories.py, baked to model/build/trajectories). The one
source of motion every picture and the web viewer's GLBs render from (#150, #182).
_Avoid_: animation, recording, track, trace (the trace is the commands it plays)
