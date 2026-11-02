"""The site's numbers from the code (docs/adr/0009, 0013): `python -m macros` writes them as JSON for the site
(site/src/macros.json, never committed), whose Markdown plugin (site/src/markdown.mjs) puts each where a doc says
`<!--{{ name }}-->`; GitHub, which hides HTML comments, shows the prose around it instead.
behaviour: the table of which event plays what (noggin/install_hooks.py, reactions/director.py, eyes/eyes.py), on the
landing page and docs/use/gestures.md.
pictures: docs/model-notes.md's picture sizes and colours (model/render/pictures.py and blender.py, geometry.py,
mjcf.py).
next_panels: the next Mech's panels' grid (model/render/pictures.py PANELS, geometry.py NEXT, #629), next_motions: its
eye gimbal in motion (#656) and next_parts: a picture of each of its parts, on docs/pictures.md (#649).
published: the pictures and the GLB the site serves, the next Mech's alone (site/site.test.mjs, src/pages/viewer.astro),
and variants: the viewer's button per head variant, in the ranking's order (#686).
wiring: docs/build/wiring.md's servo ports, both Cores (geometry.py CHANNELS, eyes/eyes.py PORT_GPIO,
eyes/calibration.json, the next Mech's neck for the neck Core: model/stages.py next_neck).
moments: the web viewer's line under each gesture (site/src/viewer/viewer.mjs), the event that plays it.
workflows: docs/ci-cd.md's table of .github/workflows (scripts/workflow_table.py, #425).
coupon: docs/build/tests.md's clearance coupon, its fits (model/printed/coupon.py).
explode: the viewer's exploded next Mech (site/src/viewer/viewer.mjs), each part's offset (render/pictures.py EXPLODE).
build, released: every page's footer and /version.json (site/src/components/Footer.astro, pages/version.json.js)."""

import ast
import json
import subprocess
from pathlib import Path

from model import geometry as g
from model import mjcf, stages
from model.printed import coupon as clearance
from model.render import pictures, scene
from noggin.core import VERSION
from noggin.service import CORES
from reactions.director import STALE_TURN_SECONDS, TIERS, Director
from scripts.workflow_table import table as workflows
from web import build as viewer

ROOT = Path(__file__).resolve().parent
MECH = {  # what each gesture looks like, by the name the director sends
    "wink": "wink (hello)",
    "thinking": "thinking: lids low, gaze averted, micro-saccades, a blink every {blink}",
    "eureka": "eureka, sized by how long the turn took: under {small} small, under {normal} normal, longer big",
    "attention": "attention: half lids, a real left-right scan",
    "bored": "bored: drooping lids, heavy blinks, one long closure",
    "wince": "wince",
    "rest": "back to rest: still but for a blink every {rest_blink} (also when the last turn ends {stale} after its"
    " prompt, whatever Triggers arrive)",
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


def seconds(lo, spread):
    """A gap of lo + up to spread ms, in seconds: (5000, 3000) -> 5-8 s."""
    return f"{lo / 1000:g}-{(lo + spread) / 1000:g} s"


def behaviour():
    gap = {k: constant("eyes/eyes.py", k) for k in ("THINK_BLINK", "REST_BLINK")}  # it imports machine: read, not run
    numbers = {
        "blink": seconds(*gap["THINK_BLINK"]),
        "rest_blink": seconds(*gap["REST_BLINK"]),
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
            f"| panels | {p.PANEL_WIDTH} wide, as tall as the tallest | WebP |",
            f"| the next Mech's parts | {size(*p.PART_SIZE)} | WebP |",
            f"| the next Mech in motion | {size(*p.MOTION_SIZE)} | {p.HERO_FPS} fps, looping |",
            "",
            "| Spool (PLA) | Colour | Drawn by Blender | `just view` |",
            "|---|---|---|---|",
            *(f"| {n} | {c} | {lift.get(c, c)} | {mjcf.VIEW.get(c, c)} |" for n, c in g.SPOOLS.items()),
            f"| lines | | {constant('model/render/blender.py', 'INK')} | |",
            f"| background | | transparent | {mjcf.SKY} |",
        ]
    )


def panels(labels):
    """The documents labelled as a grid of their panels (model/render/pictures.py PANELS), a column per document and a
    row per view, each picture linking to its file; stacked by document on a phone (site/src/styles/custom.css).
    Pictures' (#470)."""
    site, views = "https://yellowpine.com/noggin/images/", list(pictures.VIEWS)
    cells = ["<span></span>", *(f"<span>{v.capitalize()}</span>" for v in views)]
    for doc, label in labels.items():
        cells.append(f"<strong>{label}</strong>")
        for v in views:
            f = f"{site}{pictures.picture(doc, v)}"
            cells.append(f'<a href="{f}"><img src="{f}" alt="{label}, {v}" loading="lazy"></a>')
    return f'<div class="noggin-panels not-content" style="--views: {len(views)}">{"".join(cells)}</div>'


def next_panels():
    """The next Mech's panels (#629), framed among themselves: Pictures' alone."""
    # a head variant each, in both its Skeleton's styles (#704)
    return panels({doc: f"Next Mech ({doc.removeprefix('next-mech-').replace('-', ' ')})" for doc in g.NEXT})


def figures(labels, kind="parts"):
    """{picture: label} as a grid, each picture under its label, linking to its file (site/src/styles/custom.css)."""
    site, cells = "https://yellowpine.com/noggin/images/", []
    for f, label in labels.items():
        img = f'<img src="{site}{f}" alt="{label}" loading="lazy">'
        cells.append(f'<figure><a href="{site}{f}">{img}</a><figcaption>{label}</figcaption></figure>')
    return f'<div class="noggin-{kind} not-content">{"".join(cells)}</div>'


def next_motions():
    """The next Mech's eye gimbal in motion (model/render/pictures.py NEXT_MOTIONS, #656)."""
    return figures({pictures.next_motion(m): f"Eye gimbal, {m}" for m in pictures.NEXT_MOTIONS}, "motions")


def next_parts():
    """The next Mech's parts (model/render/pictures.py next_parts), each picture under its name."""
    labels = {}
    for f, (doc, name) in pictures.next_parts().items():
        stem = stages.stem(stages.STAGES[doc].parts[name].file)
        labels[f] = HARDWARE.get(stem, stem.removeprefix("next "))
    return figures(labels)


HARDWARE = {
    "receiver": "Shield",
    "core": "Core",
    "switch": "switch board",
    "battery": "battery pack",
    "horn": "servo horn",
}


def wiring():
    """Each Core's ports: the Shield's GPIO, the servo, its range and rest; the eyes' as calibrated (the lids in the
    shared lid frame, the eyes resting centred between their ends), the neck's the next Mech's neck's limits (its horns
    from neutral, 90) and that neutral."""
    gpio, cal = constant("eyes/eyes.py", "PORT_GPIO"), json.loads((ROOT / "eyes/calibration.json").read_text())
    neck = stages.next_neck().horns
    rows = ["| Core | Port | GPIO | Servo | Range | Rest |", "|---|---|---|---|---|---|"]
    for n, (name, (core, ports)) in enumerate(zip(CORES, g.CHANNELS.items(), strict=True), 1):
        for port, servo in ports.items():
            if core == "core1":
                lo, hi = cal[servo + "_lo"], cal[servo + "_hi"]
                rest = cal.get(servo + "_rest", (lo + hi) / 2)
            else:  # the pan servo's horn goes by "rotate" (model/render/scene.py HORNS)
                horn = neck[scene.HORNS["rotate" if servo == "pan" else servo]]
                (lo, hi), rest = (round(90 + d, 1) for d in horn.limits), 90
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
    """Each part of the next Mech's documents by its sub-assembly's EXPLODE offset, in glTF's metres and Y-up, by its
    GLB node's name, under the document's GLB name (web/build.py PUBLIC)."""
    glb = {doc: f.removesuffix(".glb") for doc, f in viewer.PUBLIC.items()}
    xyz = {sub: [x / 1000, z / 1000, -y / 1000] for sub, (x, y, z) in pictures.EXPLODE.items()}
    return {glb[doc]: {n: xyz[sub] for sub in subs for n in stages.SUBS[sub]().parts} for doc, subs in g.NEXT.items()}


RANKING = ROOT / "model" / "build" / "reports" / "next-mech-ranking.json"  # just sim's (model/report.py, base.rank)


def variants():
    """The viewer page's button per head variant (#664, #686), by its GLB: in RANKING's order when it ranks today's
    variants, each marked with the gates and marks it fails, else in geometry.NEXT's unmarked; its name from its
    document (next-mech-back, "Back") and a line on where its boards go, from what carries them (each carrier's
    sub-assembly's docstring in model/stages.py, "next-back: <the line>; ...")."""
    ranking = json.loads(RANKING.read_text()) if RANKING.exists() else {}
    ranked = set(ranking.get("order", [])) == set(g.NEXT)
    buttons = []
    for doc in ranking["order"] if ranked else g.NEXT:
        fails = ranking["variants"][doc]["fails"] if ranked else []
        carriers = [s for s in g.NEXT[doc] if s not in ("next-neck", "next-eyes", "next-base")]
        about = [" ".join(stages.SUBS[s].__doc__.split()).split(": ", 1)[1].split(";")[0] for s in carriers]
        name = doc.removeprefix("next-mech-").replace("-", " ").capitalize()  # next-mech-back-plain: "Back plain"
        label = name + (f": {', '.join(fails)}" if fails else "")
        buttons.append({"glb": viewer.PUBLIC[doc].removesuffix(".glb"), "label": label, "about": " and ".join(about)})
    return {"ranked": ranked, "buttons": buttons}


def build():
    """The one version (the git tag, docs/adr/0017) and the commit built, the one Site Deploy deploys (#292)."""
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
    return {"version": VERSION, "commit": head.stdout.strip()}


def released(v):
    """Whether v has its GitHub release: git describe's bare X.Y.Z, on the tag itself (noggin/core.py)."""
    return "-" not in v


def numbers():
    return {
        "behaviour": behaviour(),
        "pictures": picture_numbers(),
        "next_panels": next_panels(),
        "next_motions": next_motions(),
        "next_parts": next_parts(),
        "published": {"images": pictures.published(), "viewer": list(viewer.PUBLIC.values()), "variants": variants()},
        "wiring": wiring(),
        "coupon": coupon(),
        "workflows": workflows(),
        "moments": moments(),
        "explode": explode(),
        "build": (b := build()),
        "released": released(b["version"]),
    }


if __name__ == "__main__":
    import sys

    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "site" / "src" / "macros.json")
    out.write_text(json.dumps(numbers(), indent=1))
