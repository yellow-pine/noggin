"""The site's numbers from the code (docs/adr/0009, 0013): `python -m macros` writes them as JSON for the site
(site/src/macros.json, never committed), whose Markdown plugin (site/src/markdown.mjs) puts each where a doc says
`<!--{{ name }}-->`; GitHub, which hides HTML comments, shows the prose around it instead.
behaviour: the table of which event plays what (noggin/install_hooks.py, reactions/director.py, eyes/eyes.py), on the
landing page and docs/use/gestures.md.
pictures: docs/model-notes.md's picture sizes and colours (model/render/pictures.py and blender.py, geometry.py,
mjcf.py).
panels: the Stage panels' grid (model/render/pictures.py PANELS); next_panels: the next Mech's (geometry.py NEXT, #629).
Neither is on a page since #640 (docs/adr/0019).
stage_parts, stage_servos: each Stage's build guide (docs/build/stage-*.md), what it adds as the model has it
(model/stages.py, geometry.py PRINTED, CHANNELS and LIMITS).
wiring: docs/build/wiring.md's servo ports, both Cores (geometry.py CHANNELS, eyes/eyes.py PORT_GPIO,
eyes/calibration.json, LIMITS for the neck).
moments: the web viewer's line under each gesture (site/src/viewer/viewer.mjs), the event that plays it.
stages: the web viewer's Stages (site/src/pages/viewer.astro), one per geometry.STAGES, named as web/build.py's GLBs.
workflows: docs/ci-cd.md's table of .github/workflows (scripts/workflow_table.py, #425).
coupon: docs/build/tests.md's clearance coupon, its fits (model/printed/coupon.py).
explode: the viewer's exploded Stage 3 (site/src/viewer/viewer.mjs), each part's offset (render/pictures.py EXPLODE).
build, released: every page's footer and /version.json (site/src/components/Footer.astro, pages/version.json.js)."""

import ast
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from model import geometry as g
from model import mjcf, stages
from model.printed import coupon as clearance
from model.render import pictures
from noggin.core import VERSION
from noggin.service import CORES
from reactions.director import STALE_TURN_SECONDS, TIERS, Director
from scripts.workflow_table import table as workflows

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

MOMENT = {  # each event the hooks take, as the reader lives it (Claude Code's hooks reference)
    "SessionStart": "a session starts",
    "UserPromptSubmit": "you send a prompt",
    "Stop": "Claude finishes a turn",
    "StopFailure": "a turn fails",
    "SessionEnd": "the session ends",
    "Notification permission_prompt": "Claude asks for your permission",
    "Notification idle_prompt": "Claude waits for your input",
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
    rows += [f"| {event} | {MECH[sent].format(**numbers)} |" for event, sent in plays()]
    return "\n".join(rows)


def plays():
    """Each Claude Code event the hooks take (a Notification by its kind) and what the director sends for it."""
    for event, matcher in constant("noggin/install_hooks.py", "EVENTS").items():
        for kind in matcher.split("|") if matcher else [None]:
            director = Director()
            if event != "UserPromptSubmit":  # a turn under way, so Stop and SessionEnd have one to end
                director.handle({"hook_event_name": "UserPromptSubmit", "session_id": "s"}, 0)
            sent = director.handle({"hook_event_name": event, "session_id": "s", "notification_type": kind}, 1)
            yield f"{event}{' ' + kind if kind else ''}", sent[0].split()[0]


def moments():
    """The viewer's line under each gesture: the Claude Code moment that plays it, with its event (site/src/viewer)."""
    out = {}
    for event, sent in plays():
        if sent != "rest":  # a gesture two events play names both
            out[sent] = " or ".join(filter(None, [out.get(sent), f"{MOMENT[event]} ({event})"]))
    return out


def picture_numbers():
    p, size = pictures, "{}x{}".format
    lift = {g.SPOOLS["Absolute Black"]: constant("model/render/blender.py", "BLACK_LIFT")}
    return "\n".join(
        [
            "| Pictures | Rendered | Served |",
            "|---|---|---|",
            f"| Stage panels | {p.PANEL_WIDTH} wide, as tall as the tallest | WebP |",
            f"| hero | {size(*p.HERO_SIZE)} | {p.HERO_FPS} fps, at most {p.HERO_MAX_BYTES / 1e6:g} MB |",
            f"| favicon | {size(*p.FAVICON_SIZE)} | PNG |",
            "",
            "| Spool (PLA) | Colour | Drawn by Blender | `just view` |",
            "|---|---|---|---|",
            *(f"| {n} | {c} | {lift.get(c, c)} | {mjcf.VIEW.get(c, c)} |" for n, c in g.SPOOLS.items()),
            f"| lines | | {constant('model/render/blender.py', 'INK')} | |",
            f"| background | | transparent | {mjcf.SKY} |",
        ]
    )


def panels(labels=None):
    """The Stage panels (model/render/pictures.py PANELS), or the documents labelled, as a grid, a column per document
    and a row per view, each picture linking to its file; stacked by document on a phone (site/src/styles/custom.css).
    The landing page's and Pictures' (#470)."""
    site, views = "https://yellowpine.com/noggin/images/", list(pictures.VIEWS)
    cells = ["<span></span>", *(f"<span>{v.capitalize()}</span>" for v in views)]
    for doc, label in (labels or {doc: f"Stage {n}" for n, doc in enumerate(g.STAGES, 1)}).items():
        cells.append(f"<strong>{label}</strong>")
        for v in views:
            f = f"{site}{doc.removeprefix('noggin-')}-{v}.webp"
            cells.append(f'<a href="{f}"><img src="{f}" alt="{label}, {v}" loading="lazy"></a>')
    return f'<div class="noggin-panels not-content" style="--views: {len(views)}">{"".join(cells)}</div>'


def next_panels():
    """The next Mech's panels (#629), framed among themselves: Pictures' alone."""
    return panels(dict.fromkeys(g.NEXT, "Next Mech"))


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


def coupon():
    """The clearance coupon's fits by place from the notch (model/printed/coupon.py): each pin's clearance and hole,
    each magnet pocket's clearance and diameter."""
    rows = ["| From the notch | Pin clearance | Hole | Pocket clearance | Pocket |", "|---|---|---|---|---|"]
    for n, pin in enumerate(clearance.PINS):
        pocket = (
            f"{clearance.POCKETS[n]:.2f} mm | {clearance.DISC[0] + 2 * clearance.POCKETS[n]:.2f} mm"
            if n < len(clearance.POCKETS)
            else "|"
        )
        rows.append(f"| {n + 1} | {pin:.2f} mm | {clearance.PIN_D + 2 * pin:.2f} mm | {pocket} |")
    return "\n".join(rows)


def explode():
    """Each part of Stage 3 by its sub-assembly's EXPLODE offset, in glTF's metres and Y-up, by its GLB node's name."""
    subs = pictures.EXPLODE.items()
    return {"stage3": {n: [x / 1000, z / 1000, -y / 1000] for sub, (x, y, z) in subs for n in stages.SUBS[sub]().parts}}


def build():
    """The one version (the git tag, docs/adr/0017) and the commit built, the one Site Deploy deploys (#292)."""
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
    return {"version": VERSION, "commit": head.stdout.strip()}


def released(v):
    """Whether v has its GitHub release: git describe's bare X.Y.Z, on the tag itself (noggin/core.py)."""
    return "-" not in v


def numbers():
    parts, servos = stage_guides()
    return {
        "behaviour": behaviour(),
        "pictures": picture_numbers(),
        "panels": panels(),
        "next_panels": next_panels(),
        "stage_parts": parts,
        "stage_servos": servos,
        "wiring": wiring(),
        "coupon": coupon(),
        "workflows": workflows(),
        "stages": [doc.removeprefix("noggin-") for doc in g.STAGES],
        "moments": moments(),
        "explode": explode(),
        "build": (b := build()),
        "released": released(b["version"]),
    }


if __name__ == "__main__":
    import sys

    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "site" / "src" / "macros.json")
    out.write_text(json.dumps(numbers(), indent=1))
