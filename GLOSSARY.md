# noggin

An animatronic eye mech on a desk that reacts when Claude Code finishes a response or needs attention. This glossary covers the physical mech, the board program, and the Mac-side process that connects them.

## Language

### Hardware

**Mech**:
The physical animatronic: two eyeballs, two eyelid pairs, the pan-tilt neck and the mouth, seven servos on two Cores, built from the designer's eyes, pan-and-tilt and mouth designs (README credits).
_Avoid_: robot, head, beast, eye mech

**Core**:
The controller board (ESP32-C3 running MicroPython) that drives the servos; the noggin service reaches it over its Link.
_Avoid_: board, receiver, controller, ESP

**Shield**:
The expansion board the Core sits on; carries the servo ports and the power input; one per Core.
_Avoid_: receiver, receiver shield, product codes

**Servo**:
One of the seven actuators, named by what it moves: left lid, left eye, right lid, right eye (eyes Core); tilt, mouth, pan (neck Core).
_Avoid_: channel, PWM, actuator, motor

**Link**:
The connection between the noggin service and one Core: Wi-Fi (UDP datagrams, found by the Core's beacon) first, the USB serial port as fallback. See docs/adr/0005.
_Avoid_: serial, REPL, cable, connection, relay

### Motion

**Pose**:
The angle of every servo at one instant.
_Avoid_: position, frame, state

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
The state when no session is mid-turn and no gesture is playing: lids at their rest level, eyes centred, servos holding so the mech is still.
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
(model/envelopes.py), placed by model/geometry.py; MuJoCo simulates them from one MJCF per document (model/mjcf.py,
docs/adr/0007), the old Python engine (model/engine, docs/adr/0006) runs beside it until #151 retires it, and Blender
renders the pictures from the engine's poses (MuJoCo's from #150).
_Avoid_: twin, digital twin, CAD, simulation

**Stage**:
A cumulative build state of the Mech, the Sub-assemblies placed at frames (geometry.STAGES): Stage 1 = base + eyes (the desk eye bracket's stem in the plate's slot), Stage 2 = base + stack + eyes on the tilt arm, Stage 3 = Stage 2 + mouth (the full Mech). Simulation, photos and reports run per Stage.
_Avoid_: part, module, phase, top assembly

**Web viewer**:
The public web page that shows each Stage in 3D, turned and zoomed by the reader, playing its gestures and the hero loop
from Blender's glTF (docs/adr/0008).
_Avoid_: twin viewer, web app, demo

**Hero**:
The Mech's showcase loop: Stage 3 talking, the README's lead picture and the web viewer's default between gestures.
_Avoid_: banner, idle loop

**Sub-assembly**:
An ownership unit that owns its parts exactly once (base, stack, eyes, mouth) and is placed into Stages at a frame (model/engine/stages.py).

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
A part we print, by our name (the designer's file names are history: README credits, docs/research):
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

**Pivot**:
A revolute axis between two parts; in the Model, a MuJoCo joint (model/mjcf.py) and a joint of the old engine's four-bar
solver (model/engine/linkage.py).
_Avoid_: hinge, axle

**Port**:
A named point on a connector where a cable plugs in.
_Avoid_: socket, header

**Corridor**:
A lead's route in the Model: a tube from one Port to the other through waypoints clipped to the parts that hold the
lead, so it rides pan and tilt. The engine checks its path length and its clearance from moving parts at every pose.
_Avoid_: harness, cable path, routing

**Trajectory**:
One Gesture (or the README hero) on one Stage as MuJoCo plays its servo commands through the servos' own dynamics:
every part's place in the world per 100 ms frame (model/trajectories.py, baked to model/build/trajectories). The one
source of motion every picture and GIF renders from (#150) and the web viewer will (#180).
_Avoid_: animation, recording, track, trace (the trace is the commands it plays)
