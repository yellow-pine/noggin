"""Calibration replay for the model (#20): the five gestures plus thinking recorded from the eye program on CPython
(machine stubbed by the root conftest, a virtual clock instead of sleeping) as horn joint degrees per 100 ms frame,
then played in Fusion by twin/replay.py (one call per gesture, front-view screenshots) and assembled into one GIF
per gesture in twin/build with ffmpeg. `python twin/traces.py` does all three (Fusion open with its MCP)."""
import importlib.util, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(HERE, "build")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


if "machine" not in sys.modules:                                       # under pytest the root conftest has done this
    _load("conftest", os.path.join(REPO, "conftest.py"))                 # stubs `machine`, puts eyes/ on sys.path
sim = _load("sim", os.path.join(HERE, "sim.py"))
import eyes as mod   # noqa: E402  the Core's eye program

CAL = json.load(open(os.path.join(REPO, "eyes", "calibration.json")))
GESTURES = {"eureka": "eureka 2", "attention": "attention 2", "bored": "bored 2", "wince": "wince 2", "wink": "wink 1", "thinking": "thinking"}
SERVOS = ("l_lid", "l_eye", "r_lid", "r_eye")
FRAME_MS, THINK_MS = 100, 6000


def record(gesture):
    """Joint degrees per servo at each 100 ms frame of the gesture, from rest, per the current calibration."""
    clock, log = [0], []                               # virtual time; (ms, servo, angle) after every write
    mod.sleep_ms = lambda ms: clock.__setitem__(0, clock[0] + ms)
    e = mod.Eyes(); e.cal.update(CAL)
    original = e.set
    def set_and_log(targets):
        original(targets); log.extend((clock[0], mod.NAME[p], a) for p, a in e.pos.items())
    e.set = set_and_log
    e.handle_line("rest")
    start = clock[0]                                   # every servo has a position from here on
    if gesture == "thinking":
        e.handle_line("thinking")
        for t in range(clock[0], clock[0] + THINK_MS, FRAME_MS):
            clock[0] = t; e.tick(t)
    else:
        e.handle_line(GESTURES[gesture])
    frames, pos, i = [], {}, 0
    for t in range(start, clock[0] + 1, FRAME_MS):
        while i < len(log) and log[i][0] <= t:
            pos[log[i][1]] = log[i][2]; i += 1
        frames.append({s: round(sim.joint_deg(s, pos[s], CAL), 2) for s in SERVOS})
    return frames


def main():
    sys.path.insert(0, os.path.join(REPO, "scripts")); import fusion_run
    os.makedirs(OUT, exist_ok=True)
    traces = {g: record(g) for g in GESTURES}
    json.dump(traces, open(os.path.join(OUT, "traces.json"), "w"))
    replay = open(os.path.join(HERE, "replay.py")).read()
    for g in GESTURES:
        print(fusion_run.run_script(replay.replace("GESTURE = None", f"GESTURE = {g!r}"))["message"], end="")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "10", "-i", os.path.join(OUT, "replay", g, "%03d.png"),
                        "-vf", "scale=800:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse", os.path.join(OUT, f"{g}.gif")], check=True)
        print(f"  {g}.gif: {len(traces[g])} frames")


if __name__ == "__main__":
    main()
