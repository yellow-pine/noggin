# noggin

An animatronic eye mech on a desk that reacts when Claude Code finishes a response or needs attention. This glossary covers the physical mech, the board program, and the Mac-side process that connects them.

## Language

### Hardware

**Mech**:
The physical animatronic: two eyeballs, two eyelid pairs, four servos and the boards, built from PurpleShark's CyberBrick Eyes design.
_Avoid_: robot, head, beast, eye mech

**Core**:
The CyberBrick controller board (ESP32-C3 running MicroPython) that drives the servos and talks to the Mac over USB.
_Avoid_: board, receiver, controller, ESP

**Shield**:
The CyberBrick X11 expansion board the Core sits on; carries the four servo ports and the power input.
_Avoid_: receiver, receiver shield, X11

**Servo**:
One of the four actuators, named by what it moves: left lid, left eye, right lid, right eye.
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
The MicroPython files on the Core's filesystem. The stock program is Bambu's remote-control app; the eye program is ours and replaces it.
_Avoid_: firmware, app, code, sketch

**Firmware**:
The MicroPython image flashed into the Core by Bambu's tools. Never modified by this project.
_Avoid_: program, image, OS

### Model

**Model**:
The Fusion 360 assembly of every stage and every piece of hardware, 1:1 with the physical Mech.
_Avoid_: model, CAD, simulation

**Stage**:
One of the designer's three builds, eyes, pan-tilt or mouth, each its own Fusion design.
_Avoid_: part, module, phase

**Sub-assembly**:
One of the four Fusion designs that own the parts once (noggin-base, noggin-stack, noggin-eyes, noggin-mouth), inserted by
reference into the Stage documents noggin-stage1 (base + eyes, the desk build), stage2 (+ stack) and stage3 (+ mouth).

**Horn**:
The printed arm on a servo spline; the driven link of every chain.
_Avoid_: arm, lever

**Bar**:
A straight link between two Pivots: eyeball bar, eyelid bar, connector bar.
_Avoid_: rod, linkage

**Crank**:
The bent eyelid bar that turns Horn rotation into lid rotation.

**Pivot**:
A revolute axis between two parts; in the Model, a Fusion joint.
_Avoid_: hinge, axle

**Port**:
A named point on a connector where a cable plugs in.
_Avoid_: socket, header
