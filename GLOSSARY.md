# noggin

An animatronic eye mech on a desk that reacts when Claude Code finishes a response or needs attention. This glossary covers the physical mech, the board program, and the Mac-side process that connects them.

## Language

### Hardware

**Mech**:
The physical animatronic, our own design (#51), being designed and not built yet: two linked eyes with an upper and a
lower lid each, the pan-and-tilt neck and the mouth, seven servos on two Cores, a Skeleton that wears a Skin.
Today's Mech, the one on Cansin's desk built from another designer's parts, runs the eye program until it is built.
_Avoid_: robot, head, beast, eye mech

**Next Mech**:
The Mech, by the name the Model, the pictures and the Web viewer give it (`next-`) while today's Mech still stands on
the desk.
_Avoid_: Mech 2, new Mech

**Skeleton**:
The next Mech's structural parts, the same under every Skin: the eye gimbal, the jaw, the neck, the Torso and the
electronics mount, in PETG. A Theme category: realistic, every part drawn as Bones, or mechanical, every part in boxes
and cylinders (docs/adr/0022).
_Avoid_: frame, chassis, core

**Bone**:
A Skeleton link between two joints drawn organic: thick at the joints, waisted mid-span, rounded in section, its
joints kept exact. Each Skeleton part is drawn both as Bones and mechanical, the same interfaces in both
(docs/adr/0020).
_Avoid_: strut, organic bar

**Test stand**:
The box the Next Mech's eye block stands on in Stage 1, screwed under the gimbal frame where the head mount goes later,
the eyes Core against its back; not part of the whole Mech.
_Avoid_: base, desk stand, jig

**Torso**:
The next Mech's base: the Skeleton's compact body in the shirt and collar under the neck, holding the pack lying low and
the neck mount with the pan servo; its bottom is the foot the Mech stands on.
_Avoid_: base plate (today's Mech's part), body, stand

**Head variant**:
One way to place the next Mech's boards in its compact head, ranked against any others. Cansin picked Back, the
boards upright in the back of the head behind the eye gimbal, and it is the one variant today; the pack lies low in the
Torso.
_Avoid_: Base candidate (the two it replaced, #642), option, layout

**Eye gimbal**:
The Skeleton's linked eyes: each eyeball core turns up/down inside a yoke that turns left/right, one servo turns both
yokes through a tie-bar, one turns both cores through push-rods, and each eye's upper and lower lid turn against each
other about the up/down axis on that eye's own servo, between the eyes: the upper lid through the lid bar, the lower
through a link off it. The eyeball caps (Shells) sit on the cores.
_Avoid_: eye mech, eye frame, linked eyes (as a part name)

**Shell**:
One cosmetic part a Skin puts on the Skeleton (the head, an eyeball cap, a pupil, a lid cover, the collar), in PLA,
held on by magnets.
_Avoid_: cover, cosmetic

**Skin**:
Every Shell of one Character, pulled off and pressed on together to swap Characters; a Theme category: morty or bart.
_Avoid_: shell set, character shells, kit, costume

**Character**:
Who the next Mech looks like, Morty or Bart: its Skin and its gaze speed, picked in the noggin service's settings.
_Avoid_: persona, theme

**Theme**:
One value of each Theme category, today a Skeleton and a Skin, which together choose the next Mech's look in the
Model, the Web viewer and every picture; realistic and morty unless one is picked (docs/adr/0022).
_Avoid_: look (Blender's style B is the look), style

**Colour group**:
The parts of one Theme category printed in one filament: the Skeleton's Bones, Joints, Linkages and Mounts, a Skin's
face, hair, shirt and collar, eye whites, pupils; each Theme value names its filament per group.
_Avoid_: spool, colour (for the group)

**Face**:
A Skin's flesh-coloured Colour group: the head, the ears, the nose and the lid covers (Bart's spikes too).
_Avoid_: skin (for the colour), flesh

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
One of the seven actuators, named by what it moves: yaw (both eyes left and right), pitch (both eyes up and down), left
lid, right lid (eyes Core); tilt, mouth, pan (neck Core). Today's Mech's eye program drives its own four: left lid,
left eye, right lid, right eye.
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
The Next Mech as code: our CadQuery parts (model/printed) and hardware Envelopes (model/envelopes.py), placed into
documents by model/stages.py; MuJoCo simulates them from one MJCF per document (model/mjcf.py, docs/adr/0007), and
Blender renders the pictures from MuJoCo's Trajectories. Today's Mech left it (#720); its git history keeps it.
_Avoid_: twin, digital twin, CAD, simulation

**Stage**:
A cumulative build state of the Mech, each complete on the desk: Stage 1 the eye block on its Test stand with the eyes
Core, Stage 2 the eye block on the Torso's neck under the head mount with the boards and the neck Core, Stage 3 Stage 2
with the jaw (the whole Mech); each in every Skeleton. The build guides go Stage by Stage.
_Avoid_: part, module, phase, top assembly

**Web viewer**:
The page that shows a document of the Mech in 3D from Blender's glTF, turned and zoomed by the reader
(docs/adr/0008): the Mech Stage by Stage, playing its gestures and the Tour, whole or exploded.
_Avoid_: twin viewer, web app, demo

**Site**:
The project's public web site, built by Astro Starlight from the repo's Markdown where it stands (the `site/` package,
docs/adr/0013): a landing page at its root, the build guide, how to use the Mech, the Model and the reference docs
(docs/adr/0009); pictures and the Web viewer of the Next Mech alone, never of today's (docs/adr/0019). The README is
for contributors and stays on GitHub.
_Avoid_: docs site, homepage, Pages (the host)

**Numbers from the code**:
The values a doc shows that the code owns (the behaviour table, the wiring, the picture sizes and colours): `macros.py` derives them, and the Site puts each where the doc's hidden `<!--{{ name }}-->` marker
stands; GitHub shows a link to the Site's table instead (docs/adr/0009, 0013).
_Avoid_: generated docs

**Release**:
One version of the whole repo, noggin vX.Y.Z: the Core program, the noggin service, the Model and the Site together,
tagged vX.Y.Z on main, its notes on its GitHub release (docs/adr/0010, 0017).
_Avoid_: build, drop, version of one part

**Docs version**:
A Release's own copy of the Site's docs, once at /noggin/vX.Y/; retired (docs/adr/0021). The Site has one set of docs,
main's, labelled with the newest Release's tag, and an old version's URL lands on the same page there.
_Avoid_: docs snapshot, archived docs

**Bot App**:
The repo's own GitHub App, which the workflows act as when they open a PR or tag a Release, so its
checks, review or Release Assets run as they would for a person's (docs/adr/0010, 0017).
_Avoid_: release App, bot token

**Hero**:
The Mech's showcase loop: talking, glancing aside and nodding, the first clip of the Tour.
_Avoid_: banner, idle loop

**Tour**:
The web viewer's default: every clip of the document in turn, the Hero first, round and round;
a gesture picked plays once, then the Tour goes on.
_Avoid_: hero (for the viewer's default), demo, autoplay

**Sub-assembly**:
An ownership unit that owns its parts exactly once (the Mech's eyes, neck, jaw, base, boards' carrier and Test
stand) and is placed into a document at a frame (model/stages.py).

**Envelope**:
Our simple CadQuery stand-in for a piece of bought hardware (servo, Horn, Shield, Core, switch board, battery): its interfaces at the STEP's numbers, its body a few boxes and plates (model/envelopes.py).
_Avoid_: proxy, dummy, placeholder

**Horn**:
The printed arm on a servo spline; the driven link of every chain.
_Avoid_: arm, lever

**Bar**:
A rigid link between two Pivots: tie-bar, pitch bar, lid bar, pan bar, tilt bar, jaw bar, and the push-rods and lid
links.
_Avoid_: rod, linkage

**Crank**:
The lever on a turning part that a Bar drives: the yaw yoke's, each upper lid's.

**Printed part**:
A part we print, by our name (model/printed); the Skeleton's:
- gimbal frame: the eye block's plate, carrying the eyes' pivots and the four eye servos;
- yaw yoke: one per eye, turning left and right in the frame; tie-bar: joins both yokes to the yaw Horn;
- eyeball core: turns up and down in its yoke, its eyeball cap (a Shell) on it;
- bail, push-rod, pitch bar: turn both cores up and down from the pitch Horn;
- upper lid, lower lid: an eye's two lids; lid bar: the upper lid's Bar from its lid Horn; lid link: the lower lid's,
  off the lid bar;
- test stand: the Test stand;
- torso: the Torso; neck mount: on the Torso, the pan servo on it; pan yoke: turns on it for pan; pan bar: the pan
  Horn to the yoke;
- head mount: turns on the yoke's cheeks for tilt, the gimbal frame on it; tilt bar: the tilt Horn to the head mount;
- board rack: both Cores and the switch board, upright behind the eyes;
- jaw: turns on the head mount's lugs; jaw bar: the jaw Horn to the jaw.
_Avoid_: the designer's file names, version suffixes, today's Mech's part names (git history)

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

**Flexing span**:
The stretch of the next Mech's leads that crosses a moving Pivot (pan or tilt), clamped at its two ends only and bent
no tighter than ten times the thickest lead's diameter.
_Avoid_: service loop, cable loop, slack

**Trajectory**:
One Gesture, Rest or the Hero on one document as MuJoCo plays its servo commands through the servos' own dynamics:
every part's place in the world per 100 ms frame (model/trajectories.py, baked to model/build/trajectories). The one
source of motion every picture and the web viewer's GLBs render from (#150, #182).
_Avoid_: animation, recording, track, trace (the trace is the commands it plays)
