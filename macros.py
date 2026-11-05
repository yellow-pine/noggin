"""The site's numbers from the code (docs/adr/0009, 0013): `python -m macros` writes them as JSON for the site
(site/src/macros.json, never committed), whose Markdown plugin (site/src/markdown.mjs) puts each where a doc says
`<!--{{ name }}-->`; GitHub, which hides HTML comments, shows the prose around it instead.
behaviour: the table of which event plays what (noggin/install_hooks.py, reactions/director.py, eyes/eyes.py), on the
landing page and docs/use/gestures.md.
pictures: docs/model-notes.md's picture sizes and colours (model/render/pictures.py and blender.py, geometry.py,
mjcf.py). themes: docs/face-design.md's Palettes, each Colour group's filament (geometry.py THEMES, #805, #819).
stage_views: each of the Mech's Stages in the viewer, from the side, isometric and apart (#898), motions: it
in motion, a viewer per motion (#839), and part_pictures: each of its parts alone in the viewer, on docs/pictures.md
(#649, #898), front_views: the front doors' three there.
front: the front doors' three on the landing page (model/render/pictures.py FRONT, #739); hero: its large Stage 3
viewer on the hero loop (#889).
published: the pictures and the GLBs the site serves, the Mech's alone (site/site.test.mjs,
src/pages/viewer.astro), and stages: the viewer's Stage switch, a button per Stage (#720), and its Skeleton shapes.
theme: the header's Theme bar, the Presets, and the viewer's mix of Shapes and Palettes (site/src/theme.mjs, #806,
#819); filaments: the buy list's, per Preset (docs/build/parts.md), shown, as every Preset's pictures and the Stages'
print tables, for the Preset picked.
stage_parts, stage_servos: each Stage's build guide (docs/build/stage-*.md), what it adds as the model has it
(model/stages.py, geometry.py STAGES and PRINTED, #721); shopping: docs/build/parts.md's buy list, the bought parts
each Stage adds (#900).
wiring: docs/build/wiring.md's servo ports, both Cores (geometry.py CHANNELS, eyes/eyes.py PORT_GPIO,
eyes/calibration.json, the Mech's neck for the neck Core: model/stages.py neck_sub).
moments: the web viewer's line under each gesture (site/src/viewer/viewer.mjs), the event that plays it.
workflows: docs/ci-cd.md's table of .github/workflows (scripts/workflow_table.py, #425).
coupon: docs/build/tests.md's clearance coupon, its fits (model/printed/coupon.py).
build, released: every page's footer and /version.json (site/src/components/Footer.astro, pages/version.json.js)."""

import ast
import json
import subprocess
from collections import Counter
from pathlib import Path

from model import geometry as g
from model import mjcf, stages, trajectories
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
    p = pictures
    lift = {"#000000": constant("model/render/blender.py", "BLACK_LIFT")}
    return "\n".join(
        [
            "| Pictures | Rendered | Served |",
            "|---|---|---|",
            f"| the front doors and the posters | {p.PANEL_WIDTH} wide, as tall as the tallest | WebP |",
            "",
            "| Palette | Colour group | Filament | Colour | Drawn by Blender | `just view` |",
            "|---|---|---|---|---|---|",
            *(
                f"| {value} | {group} | {line} {name} ({code}) | {c} | {lift.get(c, c)} | {mjcf.VIEW.get(c, c)} |"
                for _, values in palettes()
                for value, groups in values.items()
                for group, (line, name, code, c) in groups.items()
            ),
            f"| lines | | | | {constant('model/render/blender.py', 'INK')} | |",
            f"| background | | | | transparent | {mjcf.SKY} |",
        ]
    )


def palettes():
    """(category, {Palette: {Colour group: filament}}) per category (geometry.THEMES' palette axes, #819)."""
    return [(a.removesuffix(" palette"), v) for a, v in g.THEMES.items() if a.endswith(" palette")]


def themed(presets):
    """The attribute that shows an element for those Presets alone, as the header's bar picks one
    (site/src/theme.mjs, #806, #819)."""
    return f' data-presets="{" ".join(map(g.slug, presets))}"'


def shaped(shape):
    """The Presets whose Skeleton shape is shape."""
    return [p for p, t in g.PRESETS.items() if t["Skeleton shape"] == shape]


def themes():
    """Each Palette's Colour groups, their parts so far and the filament each is printed in (geometry.THEMES and
    PRINTED, #805, #819)."""
    parts = {}
    for name, (group, _) in g.PRINTED.items():
        if not name.endswith(g.MECHANICAL):
            parts.setdefault(group, []).append(name)
    rows = ["| Category | Palette | Colour group | Parts | Filament | Hex |", "|---|---|---|---|---|---|"]
    for category, values in palettes():
        for value, groups in values.items():
            rows += [
                f"| {category} | {value} | {k} | {', '.join(parts.get(k, []))} | {line} {name} ({code}) | {c} |"
                for k, (line, name, code, c) in groups.items()
            ]
    return "\n".join(rows)


def filament(group):
    """The filament a Colour group prints in under each Preset, each shown for the Presets that print it alone (#806,
    #819)."""
    by = {}
    for p, theme in g.PRESETS.items():
        by.setdefault(g.filament(group, theme), []).append(p)
    return "".join(f"<span{themed(ps)}>{f[0]} {f[1]} ({f[2]})</span>" for f, ps in by.items())


def filaments():
    """The buy list's filaments (docs/build/parts.md): each Preset's by line, name and code, with the Colour groups
    each prints, one line per Preset, shown for the Preset picked (#806, #819)."""
    rows = []
    for p, theme in g.PRESETS.items():
        by = {}
        for axis, value in theme.items():
            for group, f in g.THEMES[axis][value].items() if axis.endswith(" palette") else ():
                by.setdefault(f, []).append(group)
        items = "; ".join(f"{', '.join(groups)} {f[0]} {f[1]} ({f[2]})" for f, groups in by.items())
        rows.append(f"<li{themed([p])}>{p}: {items}</li>")
    return f"<ul>{''.join(rows)}</ul>"


BONY = pictures.BONY  # the Stages in order, as Bones


def stage(doc):
    """A Stage document's name on a page, in any Shape, or a picture's (pictures.DRAWN) in any Preset: "Stage 2"."""
    doc = g.undressed(pictures.DRAWN.get(doc, (doc,))[0])
    return f"Stage {BONY.index(doc.removesuffix(g.SKELETON_SUFFIX[g.shape(doc)])) + 1}"


def viewers(cells):
    """[(doc, link, caption, presets)] as a grid of viewer embeds (embed), each over its caption, one for some Presets
    (presets) shown for them alone; in the Preset the header's bar picks, as every viewer (#819)."""
    figs = "".join(
        f"<figure{themed(ps) if ps else ''}>{embed(d, link)}<figcaption>{c}</figcaption></figure>"
        for d, link, c, ps in cells
    )
    return f'<div class="noggin-views not-content">{figs}</div>'


def stage_views():
    """Each Stage in the viewer (#898, for the panels and Explode's Parts level, #811): from the side, isometric and
    with every part apart."""
    how = (("view=side", ", from the side"), ("view=isometric", ""), ("explode=2", ", its parts apart"))
    return viewers([(d, link, stage(d) + label, None) for d in BONY for link, label in how])


def figures(labels, kind, links=None):
    """{picture: label} as a grid (site/src/styles/custom.css), each picture under its label, linking to its file or
    its links entry."""
    site, cells = "https://yellowpine.com/noggin/images/", []
    for f, label in labels.items():
        img = f'<img src="{site}{f}" alt="{label}" loading="lazy">'
        href = (links or {}).get(f, site + f)
        cells.append(f'<figure><a href="{href}">{img}</a><figcaption>{label}</figcaption></figure>')
    return f'<div class="noggin-{kind} not-content">{"".join(cells)}</div>'


def front():
    """The front doors' three (model/render/pictures.py FRONT, #739), the default Preset's mechanism bare (#843), side
    by side under their captions, each linking to its Stage in the viewer (#839), the exploded one opened exploded: the
    site's home (the README's top is a copy, test_site.py)."""
    viewer = "https://yellowpine.com/noggin/viewer/?stage="
    one, three = (f"{viewer}{BONY.index(d) + 1}" for d in (pictures.STAGE1, pictures.STAGE3))
    links = dict(zip(pictures.FRONT, [one, three, f"{three}&amp;explode=1"], strict=True))
    return figures(front_labels(), "front", links)


def front_labels():
    one, three = stage(pictures.STAGE1), stage(pictures.STAGE3)
    return dict(zip(pictures.FRONT, [f"{one}, from the front", three, f"{three}, exploded"], strict=True))


def front_views():
    """The front doors' three (model/render/pictures.py FRONT, #739), beside the viewers on Pictures."""
    return figures(front_labels(), "views")


def motions():
    """The Mech in motion (#839): a web viewer of Stage 1, the eye block, per motion it plays
    (model/trajectories.py motions: its gestures and Rest), each repeating it (its data-link,
    site/src/viewer/viewer.mjs), with no control (#883), in the Preset the header's bar picks; its still until it is
    scrolled into view, the Stage's poster (model/render/pictures.py POSTERS)."""
    doc, site = pictures.STAGE1, "https://yellowpine.com/noggin/images/"
    still = f'<img src="{site}{pictures.picture(doc, "isometric")}" alt="{stage(doc)}" loading="lazy">'
    cells = [embed(doc, f"gesture={m}", still) for m in trajectories.motions(doc)]
    return f'<div class="noggin-motions not-content">{"".join(cells)}</div>'


def embed(doc, link="", still="", kind=""):
    """A web viewer of the Stage document doc (as Bones) in a page (site/src/viewer/viewer.mjs, ADR 0008): its link
    (gesture=, explode=, view=, part=), its still until it loads, and a plain link to it in the viewer page, which
    GitHub shows and the viewer replaces."""
    glb, n = viewer.PUBLIC[doc].removesuffix(".glb"), BONY.index(doc) + 1
    href = f"https://yellowpine.com/noggin/viewer/?stage={n}" + (f"&amp;{link.replace('&', '&amp;')}" if link else "")
    poster = f"<figure>{still}</figure>" if still else ""
    return (
        f'<div class="noggin-viewer{f" {kind}" if kind else ""}" data-stage="{glb}" data-link="{link}">{poster}'
        f'<p class="noggin-open"><a href="{href}">Open {stage(doc)} in the viewer</a></p></div>'
    )


def hero():
    """The home's top (#889): a large viewer of Stage 3 playing its hero loop in the Default build, with no control but
    its reset, its poster the front doors' Stage 3 still from the same view (model/render/pictures.py FRONT); on a phone
    it loads on a tap (data-tap, site/src/viewer/viewer.mjs)."""
    still = next(f for f, (d, *_) in pictures.FRONT.items() if d == pictures.STAGE3)
    src = f"https://yellowpine.com/noggin/images/{still}"
    img = f'<img src="{src}" alt="{stage(pictures.STAGE3)}" fetchpriority="high">'
    return embed(pictures.STAGE3, "view=isometric", img, "hero").replace(" data-link", " data-tap data-link", 1)


def part_pictures():
    """Each part of the Mech in the viewer (#898): one per mesh, in the first Stage it is in, that part at full
    look and the rest ghosted (part=), isometric, under its name; one only some Presets draw (the skull's bones, a
    Skin's Shells, #813) shown for them alone (#806, #819)."""
    cells, seen = [], set()
    for d in BONY:
        drawn = {
            p: g.dressed(d + g.SKELETON_SUFFIX[t["Skeleton shape"]], t["Skin shape"]) for p, t in g.PRESETS.items()
        }
        for doc in dict.fromkeys([d, *drawn.values()]):
            for name, p in stages.STAGES[doc].parts.items():
                stem = stages.stem(p.file).removesuffix(g.MECHANICAL)
                if stem in seen:
                    continue
                seen.add(stem)
                presets = [ps for ps, dd in drawn.items() if name in stages.STAGES[dd].parts]
                part = name.rsplit(":", 1)[0].replace(" ", "+")
                label = HARDWARE.get(stem, stem)
                cells.append((d, f"part={part}&view=isometric", label, presets if len(presets) < len(drawn) else None))
    return viewers(cells)


HARDWARE = {
    "receiver": "Shield",
    "core": "Core",
    "switch": "switch board",
    "battery": "battery pack",
    "horn": "servo horn",
    "hub": "USB-C hub",
    "power": "power-path board",
    "capacitor": "bulk capacitor",
    "standard servo": "standard servo",
    "standard horn": "standard servo horn",
    "pan bearing": "pan bearing",
}


def stage_guides():
    """Per Stage ("1" to "3", the Bony documents): the parts it adds to the Stage before it (and any it takes off), each
    printed in its Colour group's filament under each Preset, shown for the Preset picked (#806, #819), or bought, and
    its new servos with their Core (the eyes Core's are the eye gimbal's horns, model/stages.py eyes_sub) and the
    model's range from each servo's travel midpoint as wiring() gives them."""
    made = {name: f"{group}: {filament(group)}" for name, (group, _) in g.PRINTED.items()}
    eyes = set(stages.SUBS["eyes"]().horns)
    parts, servos, before, horns = {}, {}, Counter(), set()
    for n, doc in enumerate(BONY, 1):
        d = stages.STAGES[doc]
        now = Counter(stages.stem(p.file) for p in d.parts.values())
        added = [(HARDWARE.get(s, s), k, made.get(s, "bought")) for s, k in (now - before).items()]
        rows = ["| Part | Count | Printed in |", "|---|---|---|"]
        rows += [f"| {name} | {k} | {m} |" for name, k, m in sorted(added, key=lambda r: r[0].lower())]
        gone = sorted(s for s in before - now)
        parts[str(n)] = "\n".join(rows + ([f"\nIt takes off: {', '.join(gone)}."] if gone else []))
        rows = ["| Core | Servo | The model's range |", "|---|---|---|"]
        for name, horn in d.horns.items():
            if name not in horns:
                servo = name.removesuffix(" horn")
                neutral = mjcf.electrical.servo.profile(servo)["travel_deg"] / 2
                lo, hi = (round(neutral + a, 1) for a in horn.limits)
                rows.append(f"| {'eyes' if name in eyes else 'neck'} | {servo} | {lo:g}..{hi:g} |")
        servos[str(n)], before, horns = "\n".join(rows), now, set(d.horns)
    return parts, servos


def shopping():
    """The buy list per Stage (docs/build/parts.md, #900): how many of each bought part (not in geometry.PRINTED) each
    Stage adds to the one before, as stage_guides() counts them."""
    rows, before = {}, Counter()
    for n, doc in enumerate(BONY):
        now = Counter(stages.stem(p.file) for p in stages.STAGES[doc].parts.values())
        for s, k in (now - before).items():
            if s not in g.PRINTED:
                rows.setdefault(HARDWARE.get(s, s), [""] * len(BONY))[n] = str(k)
        before = now
    head = [
        "| Part | " + " | ".join(f"Stage {n}" for n in range(1, len(BONY) + 1)) + " |",
        "|---" * (len(BONY) + 1) + "|",
    ]
    return "\n".join(
        head + [f"| {p} | {' | '.join(ks)} |" for p, ks in sorted(rows.items(), key=lambda r: r[0].lower())]
    )


def wiring():
    """Each Core's ports: the Shield's GPIO, the servo, its range and rest; the eyes' as calibrated (the lids in the
    shared lid frame, the eyes resting centred between their ends), the neck's the Mech's neck's limits (its horns
    from each servo's travel midpoint) and that neutral."""
    gpio, cal = constant("eyes/eyes.py", "PORT_GPIO"), json.loads((ROOT / "eyes/calibration.json").read_text())
    neck = stages.neck_sub().horns | stages.jaw_sub().horns
    rows = ["| Core | Port | GPIO | Servo | Range | Rest |", "|---|---|---|---|---|---|"]
    for n, (name, (core, ports)) in enumerate(zip(CORES, g.CHANNELS.items(), strict=True), 1):
        for port, servo in ports.items():
            if core == "core1":
                lo, hi = cal[servo + "_lo"], cal[servo + "_hi"]
                rest = cal.get(servo + "_rest", (lo + hi) / 2)
            else:  # the pan servo's horn goes by "rotate" (model/render/scene.py HORNS)
                horn = neck[scene.HORNS["rotate" if servo == "pan" else servo]]
                rest = mjcf.electrical.servo.profile(servo)["travel_deg"] / 2
                lo, hi = (round(rest + d, 1) for d in horn.limits)
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


RANKING = ROOT / "model" / "build" / "reports" / "mech-ranking.json"  # just sim's (model/report.py, base.rank)


def stage_switch():
    """The viewer page's Stage switch (#720): a button per Stage by its GLB as Bones, "1" to "3" (the Skeleton shape
    adds its suffix), the head variant's Stage marked with the gates and marks it fails in RANKING (#705), when just
    sim ranked today's variants: its mechanical document's, the one physics runs on (#809); the Skeleton shapes
    (#805, #819), each its GLB's suffix (the Preset picks one, or the viewer's mix); and the Skin shapes', where a
    Stage has their GLB: none's bare (#876), each other drawn one's dressed (#813)."""
    ranking = json.loads(RANKING.read_text()) if RANKING.exists() else {}
    ranked = set(ranking.get("order", [])) == {d for d in g.MECH if d in g.SIMULATED}
    buttons = []
    for n, doc in enumerate(BONY, 1):
        mechanical = doc + g.SKELETON_SUFFIX["mechanical"]
        fails = ranking["variants"][mechanical]["fails"] if ranked and mechanical in g.MECH else []
        buttons.append(
            {
                "glb": viewer.PUBLIC[doc].removesuffix(".glb"),
                "label": f"{n}" + (f": {', '.join(fails)}" if fails else ""),
            }
        )
    skins = {g.SKINLESS: viewer.BARE} | {s: f"-{s}" for s in list(g.SKINS)[1:]}  # Morty's the documents' own (#813)
    return {"buttons": buttons, "skeletons": g.SKELETON_SUFFIX, "skins": skins}


def theme():
    """The header's Theme bar and the viewer's mix (site/src/theme.mjs, #806, #819), by their keys in an address: the
    Presets by slug, each its label and its value on each axis, the default first; each axis' values; each Palette's
    filament hex per Colour group, which the viewer paints a GLB's Colour groups in, black as the GLB's look has it."""

    def key(a):
        return a.lower().replace(" ", "-")

    return {
        "presets": {g.slug(p): {"label": p} | {key(a): v for a, v in t.items()} for p, t in g.PRESETS.items()},
        "axes": {key(a): list(v) for a, v in g.THEMES.items()},
        "palettes": {
            key(f"{c} palette"): {v: {k: f[3] for k, f in groups.items()} for v, groups in values.items()}
            for c, values in palettes()
        },
    }


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
        "theme": theme(),  # the header's bar and the viewer's mix (#806, #819)
        "stage_views": stage_views(),
        "front_views": front_views(),
        "front": front(),
        "motions": motions(),
        "hero": hero(),
        "part_pictures": part_pictures(),
        "published": {"images": pictures.published(), "viewer": list(viewer.PUBLIC.values()), "stages": stage_switch()},
        "stage_parts": (guides := stage_guides())[0],
        "stage_servos": guides[1],
        "shopping": shopping(),
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
