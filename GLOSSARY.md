# robohead

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
The USB serial connection between the Core and the Mac.
_Avoid_: serial, REPL, cable, connection

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

**Rest**:
The state between gestures: lids open, eyes centred, servos released so the mech is silent and still.
_Avoid_: idle, sleep, neutral, home

### Control

**Trigger**:
A request for a gesture arriving at the Daemon, normally from a Claude Code hook.
_Avoid_: hook, event, signal, poke

**Daemon**:
The always-running Mac process that owns the Link and turns Triggers into gesture commands for the Core.
_Avoid_: service, server, agent, bridge, puppeteer

**Busy**:
The Daemon's state while a gesture is playing; any Trigger arriving while Busy is dropped.
_Avoid_: cooldown, debounce, lock

**Program**:
The MicroPython files on the Core's filesystem. The stock program is Bambu's remote-control app; the eye program is ours and replaces it.
_Avoid_: firmware, app, code, sketch

**Firmware**:
The MicroPython image flashed into the Core by Bambu's tools. Never modified by this project.
_Avoid_: program, image, OS
