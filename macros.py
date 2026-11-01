"""The site's numbers from the code (docs/adr/0009, mkdocs-macros): `<!--{{ name }}-->` in a doc is filled here at
build time, and GitHub, which hides HTML comments, shows the prose around it instead (mkdocs.yml has the delimiters).
behaviour: the table of which event plays what (noggin/install_hooks.py, reactions/director.py, eyes/eyes.py), on the
landing page and docs/use/gestures.md.
pictures: docs/model-notes.md's picture sizes and colours (model/render/pictures.py and blender.py, geometry.py,
mjcf.py).
stage_parts, stage_servos: each Stage's build guide (docs/build/stage-*.md), what it adds as the model has it
(model/stages.py, geometry.py PRINTED, CHANNELS and LIMITS).
wiring: docs/build/wiring.md's servo ports, both Cores (geometry.py CHANNELS, eyes/eyes.py PORT_GPIO,
eyes/calibration.json, LIMITS for the neck).
stage_buttons: the web viewer's Stage buttons (web/viewer.md), one per geometry.STAGES, named as web/build.py's GLBs."""

import ast
import json
import re
from collections import Counter
from pathlib import Path

from model import geometry as g
from model import mjcf, stages
from model.render import pictures
from noggin.service import CORES
from reactions.director import STALE_TURN_SECONDS, TIERS, Director

ROOT = Path(__file__).resolve().parent
MECH = {  # what each gesture looks like, by the name the director sends
    "wink": "wink (hello)",
    "thinking": "thinking: lids low, gaze averted, micro-saccades, a blink every {blink}",
    "eureka": "eureka, sized by how long the turn took: under {small} small, under {normal} normal, longer big",
    "attention": "attention: half lids, a real left-right scan",
    "bored": "bored: drooping lids, heavy blinks, one long closure",
    "wince": "wince",
    "rest": "back to rest (also when the last turn ends {stale} after its prompt, whatever Triggers arrive)",
}


def constant(path, name):
    """A literal assigned at the top of a file that does not import here (a hooks script that writes settings on
    import, Blender's)."""
    tree = ast.parse((ROOT / path).read_text())
    assigns = (n for n in tree.body if isinstance(n, ast.Assign))
    return next(ast.literal_eval(n.value) for n in assigns if getattr(n.targets[0], "id", None) == name)


def duration(seconds):
    return f"{seconds // 60} min" if seconds % 60 == 0 else f"{seconds} s"


def behaviour():
    # shortcut: the blink gap read off its line, since eyes/eyes.py is the Core's program and imports machine (only
    # pytest stubs it); a module constant there if the line changes shape
    gap = r"self\.next_blink = now_ms \+ (\d+) \+ self\.rand % (\d+)"
    lo, spread = map(int, re.search(gap, (ROOT / "eyes/eyes.py").read_text()).groups())
    numbers = {
        "blink": f"{lo / 1000:g}-{(lo + spread) / 1000:g} s",
        "small": duration(TIERS[0][0]),
        "normal": duration(TIERS[1][0]),
        "stale": duration(STALE_TURN_SECONDS),
    }
    rows = ["| Claude Code event | Mech |", "|---|---|"]
    for event, matcher in constant("noggin/install_hooks.py", "EVENTS").items():
        for kind in matcher.split("|") if matcher else [None]:
            director = Director()
            if event != "UserPromptSubmit":  # a turn under way, so Stop and SessionEnd have one to end
                director.handle({"hook_event_name": "UserPromptSubmit", "session_id": "s"}, 0)
            sent = director.handle({"hook_event_name": event, "session_id": "s", "notification_type": kind}, 1)
            rows.append(f"| {event}{' ' + kind if kind else ''} | {MECH[sent[0].split()[0]].format(**numbers)} |")
    return "\n".join(rows)


def picture_numbers():
    p, gif = pictures, "{} wide, {} fps, {} colours, at most {:g} MB".format
    gestures = gif(p.GIF_WIDTH, p.GIF_FPS, p.GIF_COLOURS, p.GIF_MAX_BYTES / 1e6)
    hero = gif(p.HERO_WIDTH, p.GIF_FPS, p.HERO_COLOURS, p.HERO_MAX_BYTES / 1e6)
    size = "{}x{}".format
    lift = {g.SPOOLS["Absolute Black"]: constant("model/render/blender.py", "BLACK_LIFT")}
    return "\n".join(
        [
            "| Pictures | Rendered | GIF |",
            "|---|---|---|",
            f"| views and the exploded stage 3 | {size(*p.VIEW_SIZE)} | |",
            f"| the Stage strip, per panel | {size(*p.STRIP_PANEL)} | |",
            f"| gestures | {size(*p.GIF_SIZE)} | {gestures} |",
            f"| hero | {size(*p.HERO_SIZE)} | {hero} |",
            "",
            "| Spool (PLA) | Colour | Drawn by Blender | `make view` |",
            "|---|---|---|---|",
            *(f"| {n} | {c} | {lift.get(c, c)} | {mjcf.VIEW.get(c, c)} |" for n, c in g.SPOOLS.items()),
            f"| background | | {constant('model/render/blender.py', 'BG')} | {mjcf.SKY} |",
        ]
    )


HARDWARE = {
    "receiver": "Shield",
    "core": "Core",
    "switch": "switch board",
    "battery": "battery pack",
    "horn": "servo horn",
}


def stage_guides():
    """Per Stage (1, 2, 3): the parts it adds to the Stage before it (and any it swaps out), and its new servos with
    their Core, port and the model's range."""
    spool = {
        name.split(" (")[0]: s + (" (inferred)" if "inferred" in name else "") for name, (s, _) in g.PRINTED.items()
    }
    port = {servo: (core, n) for core, ports in g.CHANNELS.items() for n, servo in ports.items()}
    servo_of = {label: key for key, label in g.SERVO_LABEL.items()}
    parts, servos, before, horns = {}, {}, Counter(), set()
    for n, doc in enumerate(g.STAGES, 1):
        d = stages.STAGES[doc]
        now = Counter(stages.stem(p.file) for p in d.parts.values())
        rows = ["| Part | Count | Printed in |", "|---|---|---|"]
        added = [(HARDWARE.get(s, s), k, spool.get(s, "bought")) for s, k in (now - before).items()]
        rows += [f"| {name} | {k} | {made} |" for name, k, made in sorted(added, key=lambda r: r[0].lower())]
        gone = before - now
        parts[n] = "\n".join(rows + ([f"\nIt takes off: {', '.join(sorted(gone))}."] if gone else []))
        rows = ["| Core | Port | Servo | The model's range | Why |", "|---|---|---|---|---|"]
        for h in [h for h in d.horns if h not in horns]:
            key = servo_of[h.removesuffix(" horn")]
            core, n_port = port[key]
            (lo, hi), why = g.LIMITS["rotate" if key == "pan" else key]  # the pan servo's limits go by "rotate"
            rows.append(f"| {core.removeprefix('core')} | {n_port} | {key} | {lo:g}..{hi:g} | {why} |")
        servos[n], before, horns = "\n".join(rows), now, set(d.horns)
    return parts, servos


def wiring():
    """Each Core's ports: the Shield's GPIO, the servo, its range and rest; the eyes' as calibrated (the lids in the
    shared lid frame, the eyes resting centred between their ends), the neck's the model's limits and its
    neutral."""
    gpio, cal = constant("eyes/eyes.py", "PORT_GPIO"), json.loads((ROOT / "eyes/calibration.json").read_text())
    rows = ["| Core | Port | GPIO | Servo | Range | Rest |", "|---|---|---|---|---|---|"]
    for n, (name, (core, ports)) in enumerate(zip(CORES, g.CHANNELS.items(), strict=True), 1):
        for port, servo in ports.items():
            if core == "core1":
                lo, hi = cal[servo + "_lo"], cal[servo + "_hi"]
                rest = cal.get(servo + "_rest", (lo + hi) / 2)
            else:
                (lo, hi), rest = g.HORN_LIMITS["rotate" if servo == "pan" else servo], 90  # pan's limits go by "rotate"
            row = f"{n} ({name}) | {port} | {gpio[str(port)]} | {g.SERVO_LABEL[servo]} | {lo:g}..{hi:g} | {rest:g}"
            rows.append(f"| {row} |")
    return "\n".join(rows)


def stage_buttons():
    return "\n".join(
        f'<button class="md-button" data-stage="{doc.removeprefix("noggin-")}">Stage {n}</button>'
        for n, doc in enumerate(g.STAGES, 1)
    )


def define_env(env):
    env.variables["behaviour"], env.variables["pictures"] = behaviour(), picture_numbers()
    env.variables["stage_parts"], env.variables["stage_servos"] = stage_guides()
    env.variables["wiring"], env.variables["stage_buttons"] = wiring(), stage_buttons()
