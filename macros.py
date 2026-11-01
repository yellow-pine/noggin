"""The site's numbers from the code (docs/adr/0009, mkdocs-macros): `<!--{{ name }}-->` in a doc is filled here at
build time, and GitHub, which hides HTML comments, shows the prose around it instead (mkdocs.yml has the delimiters).
behaviour: the README's table, which event plays what (noggin/install_hooks.py, reactions/director.py, eyes/eyes.py).
pictures: docs/model-notes.md's picture sizes and colours (model/render/pictures.py and blender.py, geometry.py,
mjcf.py)."""

import ast
import inspect
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
    """A literal assigned at the top of a file that does not import here (the Core's program, a hooks script that
    writes settings on import, Blender's)."""
    tree = ast.parse((ROOT / path).read_text())
    assigns = (n for n in tree.body if isinstance(n, ast.Assign))
    return next(ast.literal_eval(n.value) for n in assigns if getattr(n.targets[0], "id", None) == name)


def duration(seconds):
    return f"{seconds // 60} min" if seconds % 60 == 0 else f"{seconds} s"


def behaviour():
    lo, hi = constant("eyes/eyes.py", "THINK_BLINK_MS")
    numbers = {
        "blink": f"{lo / 1000:g}-{hi / 1000:g} s",
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
    encode = inspect.signature(pictures.encode).parameters
    gif = f"{encode['width'].default} wide, {pictures.GIF_FPS} fps, {encode['colours'].default} colours"
    hero = f"{pictures.HERO_GIF[0]} wide, {trajectories.FPS} fps, {pictures.HERO_GIF[2]} colours"
    size = "{}x{}".format
    lift = {g.SPOOLS["Absolute Black"]: constant("model/render/blender.py", "BLACK_LIFT")}
    return "\n".join(
        [
            "| Pictures | Rendered | GIF |",
            "|---|---|---|",
            f"| views and the exploded stage 3 | {size(*pictures.VIEW_SIZE)} | |",
            f"| the Stage strip, per panel | {size(*pictures.STRIP_PANEL)} | |",
            f"| gestures | {size(*pictures.GIF_SIZE)} | {gif}, at most {pictures.GIF_MAX_BYTES / 1e6:g} MB |",
            f"| hero | {size(*pictures.HERO_SIZE)} | {hero}, at most {pictures.HERO_GIF[1] / 1e6:g} MB |",
            "",
            "| Spool (PLA) | Colour | Drawn by Blender | `make view` |",
            "|---|---|---|---|",
            *(f"| {n} | {c} | {lift.get(c, c)} | {mjcf.VIEW.get(c, c)} |" for n, c in g.SPOOLS.items()),
            f"| background | | {constant('model/render/blender.py', 'BG')} | {mjcf.SKY} |",
        ]
    )


def define_env(env):
    env.variables["behaviour"], env.variables["pictures"] = behaviour(), picture_numbers()
