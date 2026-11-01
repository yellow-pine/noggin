"""The site's numbers from the code (docs/adr/0009, mkdocs-macros): `<!--{{ name }}-->` in a doc is filled here at
build time, and GitHub, which hides HTML comments, shows the prose around it instead (mkdocs.yml has the delimiters).
behaviour: the README's table, which event plays what (noggin/install_hooks.py, reactions/director.py, eyes/eyes.py).
pictures: docs/model-notes.md's picture sizes and colours (model/render/pictures.py and blender.py, geometry.py,
mjcf.py)."""

import ast
import re
from pathlib import Path

from model import geometry as g
from model import mjcf, trajectories
from model.render import pictures
from reactions.director import STALE_TURN_SECONDS, TIERS, Director

ROOT = Path(__file__).resolve().parent
MECH = {  # what each gesture looks like, by the name the director sends
    "wink": "wink (hello)",
    "thinking": "thinking: lids low, gaze averted, micro-saccades, a blink every {blink}",
    "eureka": "eureka, sized by how long the turn took: under {small} small, under {normal} normal, longer big",
    "attention": "attention: half lids, a real left-right scan",
    "bored": "bored: drooping lids, heavy blinks, one long closure",
    "wince": "wince",
    "rest": "back to rest (a turn with no events for {stale} also returns to rest)",
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
    # shortcut: the blink gap read off its line, since eyes/eyes.py is a sim-report input (an edit there means
    # make sim); a named constant once #229 takes the reports out of git
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
    hero = gif(p.HERO_WIDTH, trajectories.FPS, p.HERO_COLOURS, p.HERO_MAX_BYTES / 1e6)
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


def define_env(env):
    env.variables["behaviour"], env.variables["pictures"] = behaviour(), picture_numbers()
