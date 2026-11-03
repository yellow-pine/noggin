"""The site's numbers from the code (docs/adr/0009, 0013): `python -m macros` writes them as JSON for the site
(site/src/macros.json, never committed), whose Markdown plugin (site/src/markdown.mjs) puts each where a doc says
`<!--{{ name }}-->`; GitHub, which hides HTML comments, shows the prose around it instead.
behaviour: the table of which event plays what (noggin/install_hooks.py, reactions/director.py, eyes/eyes.py), on the
landing page and docs/use/gestures.md.
pictures: docs/model-notes.md's picture sizes and colours (model/render/pictures.py and blender.py, geometry.py,
mjcf.py). themes: docs/face-design.md's Themes, each Colour group's filament (geometry.py THEMES, #805).
next_panels: the next Mech's panels' grid, each of its Stages in every Skeleton (model/render/pictures.py PANELS,
geometry.py STAGES, #629, #720), next_motions: its eye gimbal in motion (#656) and next_parts: a picture of each of its
parts, on docs/pictures.md (#649), next_front: the front doors' own two there and next_exploded: each Stage with every
part apart (#811).
front: the front doors' three on the landing page (model/render/pictures.py FRONT, #739).
published: the pictures and the GLBs the site serves, the next Mech's alone (site/site.test.mjs,
src/pages/viewer.astro), and stages: the viewer's Stage switch, a button per Stage (#720), and its Skeletons (#805).
theme: the header's Theme bar, each category's values (site/src/theme.mjs, #806); filaments: the buy list's, per
value (docs/build/parts.md), shown, as every themed picture and the Stages' print tables, in the Theme picked.
stage_parts, stage_servos: each Stage's build guide (docs/build/stage-*.md), what it adds as the model has it
(model/stages.py, geometry.py STAGES and PRINTED, #721).
wiring: docs/build/wiring.md's servo ports, both Cores (geometry.py CHANNELS, eyes/eyes.py PORT_GPIO,
eyes/calibration.json, the next Mech's neck for the neck Core: model/stages.py next_neck).
moments: the web viewer's line under each gesture (site/src/viewer/viewer.mjs), the event that plays it.
workflows: docs/ci-cd.md's table of .github/workflows (scripts/workflow_table.py, #425).
coupon: docs/build/tests.md's clearance coupon, its fits (model/printed/coupon.py).
build, released: every page's footer and /version.json (site/src/components/Footer.astro, pages/version.json.js)."""

import ast
import json
import subprocess
from collections import Counter
from itertools import batched
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
    lift = {"#000000": constant("model/render/blender.py", "BLACK_LIFT")}
    return "\n".join(
        [
            "| Pictures | Rendered | Served |",
            "|---|---|---|",
            f"| panels | {p.PANEL_WIDTH} wide, as tall as the tallest | WebP |",
            f"| the next Mech's parts | {size(*p.PART_SIZE)} | WebP |",
            f"| the next Mech in motion | {size(*p.MOTION_SIZE)} | {p.HERO_FPS} fps, looping |",
            "",
            "| Theme | Colour group | Filament | Colour | Drawn by Blender | `just view` |",
            "|---|---|---|---|---|---|",
            *(
                f"| {value} | {group} | {line} {name} ({code}) | {c} | {lift.get(c, c)} | {mjcf.VIEW.get(c, c)} |"
                for values in g.THEMES.values()
                for value, groups in values.items()
                for group, (line, name, code, c) in groups.items()
            ),
            f"| lines | | | | {constant('model/render/blender.py', 'INK')} | |",
            f"| background | | | | transparent | {mjcf.SKY} |",
        ]
    )


def themed(category, value):
    """The attribute that shows an element in that Theme value alone, as the header's bar picks it
    (site/src/theme.mjs, #806)."""
    return f' data-{category.lower()}="{value}"'


def panels(labels):
    """The documents labelled as a grid of their panels (model/render/pictures.py PANELS), a column per document and a
    row per view, each picture linking to its file, each document's shown in its Skeleton alone (#806); stacked by
    document on a phone (site/src/styles/custom.css). Pictures' (#470)."""
    site, views = "https://yellowpine.com/noggin/images/", list(pictures.VIEWS)
    cells = ["<span></span>", *(f"<span>{v.capitalize()}</span>" for v in views)]
    for doc, label in labels.items():
        mark = themed("Skeleton", g.theme(doc)["Skeleton"])
        cells.append(f"<strong{mark}>{label}</strong>")
        for v in views:
            f = f"{site}{pictures.picture(doc, v)}"
            cells.append(f'<a href="{f}"{mark}><img src="{f}" alt="{label}, {v}" loading="lazy"></a>')
    return f'<div class="noggin-panels not-content" style="--views: {len(views)}">{"".join(cells)}</div>'


def themes():
    """Each Theme value's Colour groups, their parts so far and the filament each is printed in (geometry.THEMES and
    PRINTED, #805)."""
    parts = {}
    for name, (group, _) in g.PRINTED.items():
        if not name.endswith(g.MECHANICAL):
            parts.setdefault(group, []).append(name.removeprefix("next "))
    rows = ["| Category | Value | Colour group | Parts | Filament | Hex |", "|---|---|---|---|---|---|"]
    for category, values in g.THEMES.items():
        for value, groups in values.items():
            rows += [
                f"| {category} | {value} | {k} | {', '.join(parts.get(k, []))} | {line} {name} ({code}) | {c} |"
                for k, (line, name, code, c) in groups.items()
            ]
    return "\n".join(rows)


def filament(group):
    """The filament a Colour group prints in under each value of its Theme category, each shown in that value alone
    (#806)."""
    return "".join(
        f"<span{themed(c, v)}>{f[0]} {f[1]} ({f[2]})</span>"
        for c, values in g.THEMES.items()
        for v, groups in values.items()
        if (f := groups.get(group))
    )


def filaments():
    """The buy list's filaments (docs/build/parts.md): each Theme value's, its Colour groups' by line, name and code,
    one line per value, shown for the value picked (#806)."""
    rows = [
        f"<li{themed(c, v)}>{c} {v}: "
        + ", ".join(f"{group} {line} {name} ({code})" for group, (line, name, code, _) in groups.items())
        + "</li>"
        for c, values in g.THEMES.items()
        for v, groups in values.items()
    ]
    return f"<ul>{''.join(rows)}</ul>"


BONY = [doc for doc in g.STAGES if g.theme(doc) == g.THEME]  # the Stages in order, realistic (as Bones)


def stage(doc):
    """A Stage document's name on a page, in any Skeleton: "Stage 2"."""
    bony = doc.removesuffix(g.SKELETON_SUFFIX[g.theme(doc)["Skeleton"]])
    return f"Stage {BONY.index(bony) + 1}"


def next_panels():
    """The next Mech's panels (#629), each Stage in every Skeleton (#720, #805), framed among themselves: Pictures'
    alone."""
    return panels({doc: stage(doc) for doc in g.STAGES})


def figures(labels, kind="parts", links=None, skeletons=None):
    """{picture: label} as a grid, each picture under its label, linking to its file or its links entry, one drawn in
    a Skeleton (skeletons) shown in it alone (site/src/styles/custom.css)."""
    site, cells = "https://yellowpine.com/noggin/images/", []
    for f, label in labels.items():
        img = f'<img src="{site}{f}" alt="{label}" loading="lazy">'
        href = (links or {}).get(f, site + f)
        mark = themed("Skeleton", s) if (s := (skeletons or {}).get(f)) else ""
        cells.append(f'<figure{mark}><a href="{href}">{img}</a><figcaption>{label}</figcaption></figure>')
    return f'<div class="noggin-{kind} not-content">{"".join(cells)}</div>'


def front():
    """The front doors' three (model/render/pictures.py FRONT, #739) in each Skeleton, shown in it alone (#806), side by
    side under their captions, Stage 1's linking to Pictures, Stage 3's to it in the viewer in that Skeleton, the
    exploded one opened exploded: the site's home (the README's top is a copy of the default's, test_site.py)."""
    site, links = "https://yellowpine.com/noggin/", {}
    for (skeleton, s), fs in zip(g.SKELETON_SUFFIX.items(), batched(pictures.FRONT, 3, strict=True), strict=True):
        viewer = f"{site}viewer/?stage={BONY.index(pictures.STAGE3) + 1}" + (s and f"&amp;skeleton={skeleton}")
        links |= dict(zip(fs, [f"{site}docs/pictures/", viewer, f"{viewer}&amp;explode=1"], strict=True))
    return figures(front_labels(), "front", links, front_skeletons())


def front_labels():
    one, three = stage(pictures.STAGE1), stage(pictures.STAGE3)
    labels = [f"{one}, from the front", three, f"{three}, exploded"] * len(g.SKELETON_SUFFIX)
    return dict(zip(pictures.FRONT, labels, strict=True))


def front_skeletons():
    """{front door's picture: the Skeleton it is drawn in}, FRONT's three per Skeleton."""
    return {f: s for s, fs in zip(g.SKELETON_SUFFIX, batched(pictures.FRONT, 3, strict=True), strict=True) for f in fs}


def next_front():
    """The front doors' own pictures (model/render/pictures.py FRONT, #739), beside the panels on Pictures."""
    own = {f: label for f, label in front_labels().items() if pictures.FRONT[f]}
    return figures(own, "views", skeletons=front_skeletons())


def next_exploded():
    """Each Stage in every Skeleton at Explode's Parts level (model/render/pictures.py parts_exploded, #811), each shown
    in its Skeleton alone (#806)."""
    labels = {pictures.parts_exploded(doc): f"{stage(doc)}, its parts apart" for doc in g.STAGES}
    skeletons = {pictures.parts_exploded(doc): g.theme(doc)["Skeleton"] for doc in g.STAGES}
    return figures(labels, "views", skeletons=skeletons)


def next_motions():
    """The next Mech's eye gimbal in motion (model/render/pictures.py NEXT_MOTIONS, #656), in each Skeleton (#806)."""
    moving = {(m, s): pictures.next_motion(m, s) for s in g.SKELETON_SUFFIX for m in pictures.NEXT_MOTIONS}
    labels = {f: f"Eye gimbal, {m}" for (m, _), f in moving.items()}
    return figures(labels, "motions", skeletons={f: s for (_, s), f in moving.items()})


def next_parts():
    """The next Mech's parts (model/render/pictures.py next_parts), each picture under its name, a Skeleton part's
    shown in the Skeleton it is drawn in alone (#806)."""
    labels, skeletons, bones = {}, {}, g.THEMES["Skeleton"][g.THEME["Skeleton"]]
    for f, (doc, name) in pictures.next_parts().items():
        stem = stages.stem(stages.STAGES[doc].parts[name].file)
        labels[f] = HARDWARE.get(stem, stem.removeprefix("next ").removesuffix(g.MECHANICAL))
        if g.PRINTED.get(stem, (None,))[0] in bones:
            skeletons[f] = g.theme(doc)["Skeleton"]
    return figures(labels, skeletons=skeletons)


HARDWARE = {
    "receiver": "Shield",
    "core": "Core",
    "switch": "switch board",
    "battery": "battery pack",
    "horn": "servo horn",
}


def stage_guides():
    """Per Stage ("1" to "3", the Bony documents): the parts it adds to the Stage before it (and any it takes off), each
    printed in its Colour group's filament under each Theme value, shown for the value picked (#806), or bought, and
    its new servos with their Core (the eyes Core's are the eye gimbal's horns, model/stages.py next_eyes) and the
    model's range, from neutral 90 as wiring() gives them."""
    made = {name: f"{group}: {filament(group)}" for name, (group, _) in g.PRINTED.items()}
    eyes = set(stages.SUBS["next-eyes"]().horns)
    parts, servos, before, horns = {}, {}, Counter(), set()
    for n, doc in enumerate(BONY, 1):
        d = stages.STAGES[doc]
        now = Counter(stages.stem(p.file) for p in d.parts.values())
        added = [
            (HARDWARE.get(s, s.removeprefix("next ")), k, made.get(s, "bought")) for s, k in (now - before).items()
        ]
        rows = ["| Part | Count | Printed in |", "|---|---|---|"]
        rows += [f"| {name} | {k} | {m} |" for name, k, m in sorted(added, key=lambda r: r[0].lower())]
        gone = sorted(s.removeprefix("next ") for s in before - now)
        parts[str(n)] = "\n".join(rows + ([f"\nIt takes off: {', '.join(gone)}."] if gone else []))
        rows = ["| Core | Servo | The model's range |", "|---|---|---|"]
        for name, horn in d.horns.items():
            if name not in horns:
                lo, hi = (round(90 + a, 1) for a in horn.limits)
                servo = name.removeprefix("next ").removesuffix(" horn")
                rows.append(f"| {'eyes' if name in eyes else 'neck'} | {servo} | {lo:g}..{hi:g} |")
        servos[str(n)], before, horns = "\n".join(rows), now, set(d.horns)
    return parts, servos


def wiring():
    """Each Core's ports: the Shield's GPIO, the servo, its range and rest; the eyes' as calibrated (the lids in the
    shared lid frame, the eyes resting centred between their ends), the neck's the next Mech's neck's limits (its horns
    from neutral, 90) and that neutral."""
    gpio, cal = constant("eyes/eyes.py", "PORT_GPIO"), json.loads((ROOT / "eyes/calibration.json").read_text())
    neck = stages.next_neck().horns | stages.next_jaw().horns
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


RANKING = ROOT / "model" / "build" / "reports" / "next-mech-ranking.json"  # just sim's (model/report.py, base.rank)


def stage_switch():
    """The viewer page's Stage switch (#720): a button per Stage by its GLB as Bones, "1" to "3" (the header's Theme
    bar's Skeleton adds its suffix), the head variant's Stage marked with the gates and marks it fails in RANKING
    (#705), when just sim ranked today's variants: its mechanical document's, the one physics runs on (#809); and the
    Skeletons (#805), each its GLB's suffix (the header's bar picks one, #806)."""
    ranking = json.loads(RANKING.read_text()) if RANKING.exists() else {}
    ranked = set(ranking.get("order", [])) == {d for d in g.NEXT if d in g.SIMULATED}
    buttons = []
    for n, doc in enumerate(BONY, 1):
        mechanical = doc + g.SKELETON_SUFFIX["mechanical"]
        fails = ranking["variants"][mechanical]["fails"] if ranked and mechanical in g.NEXT else []
        buttons.append(
            {
                "glb": viewer.PUBLIC[doc].removesuffix(".glb"),
                "label": f"{n}" + (f": {', '.join(fails)}" if fails else ""),
            }
        )
    return {"buttons": buttons, "skeletons": g.SKELETON_SUFFIX}


def build():
    """The one version (the git tag, docs/adr/0017) and the commit built, the one Checks' Deploy deploys (#292)."""
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
    return {"version": VERSION, "commit": head.stdout.strip()}


def released(v):
    """Whether v has its GitHub release: git describe's bare X.Y.Z, on the tag itself (noggin/core.py)."""
    return "-" not in v


def numbers():
    return {
        "behaviour": behaviour(),
        "pictures": picture_numbers(),
        "themes": themes(),
        "filaments": filaments(),
        "theme": {c.lower(): list(values) for c, values in g.THEMES.items()},  # the header's bar (#806)
        "next_panels": next_panels(),
        "next_front": next_front(),
        "next_exploded": next_exploded(),
        "front": front(),
        "next_motions": next_motions(),
        "next_parts": next_parts(),
        "published": {"images": pictures.published(), "viewer": list(viewer.PUBLIC.values()), "stages": stage_switch()},
        "stage_parts": (guides := stage_guides())[0],
        "stage_servos": guides[1],
        "wiring": wiring(),
        "coupon": coupon(),
        "workflows": workflows(),
        "moments": moments(),
        "build": (b := build()),
        "released": released(b["version"]),
    }


if __name__ == "__main__":
    import sys

    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "site" / "src" / "macros.json")
    out.write_text(json.dumps(numbers(), indent=1))
