"""Play Core-program command lines on the Mac with a simulated clock (Mac only: stubs `machine`).
play() gives the servo timeline; near_stop_holds() is the stall-time check (docs/build-notes.md: the clutch
servos slip when driven into a stop)."""

import importlib.util
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
_mod = None


def _eyes():
    global _mod
    if _mod is None:
        if "machine" not in sys.modules:
            m = types.ModuleType("machine")
            m.Pin = type("Pin", (), {"__init__": lambda self, n: None})  # pyright: ignore[reportAttributeAccessIssue]
            m.PWM = type(  # pyright: ignore[reportAttributeAccessIssue]
                "PWM",
                (),
                {
                    "__init__": lambda self, pin, freq=50: None,
                    "duty_ns": lambda self, ns: None,
                    "deinit": lambda self: None,
                },
            )
            sys.modules["machine"] = m
        if HERE not in sys.path:
            sys.path.insert(0, HERE)  # eyes.py imports gaze_trace
        spec = importlib.util.spec_from_file_location(
            "eyes_program", os.path.join(HERE, "eyes.py")
        )  # by path: model/ has its own `eyes`
        assert spec and spec.loader
        _mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_mod)
    return _mod


def play(lines, cal=None):
    """Run command lines; returns ([(ms, pin, angle), ...] in order, total ms)."""
    mod = _eyes()
    clock = [0]
    mod.sleep_ms = lambda ms: clock.__setitem__(0, clock[0] + ms)  # pyright: ignore[reportAttributeAccessIssue]
    e = mod.Eyes()
    e.cal.update(cal or {})
    log, orig = [], e.set

    def logged(targets):
        orig(targets)
        log.extend((clock[0], p, e.pos[p]) for p in targets)

    e.set = logged
    for line in lines:
        e.handle_line(line)
    return log, clock[0]


def shared_frame(cal):
    """calibration.json in the shared lid frame (#213). The shape before it (each lid's ends in its own servo's degrees,
    `<lid>_flip` 1 where the low end is open) is converted: the MIRRORED servo's degrees become 180 - a, lo the closed
    end, hi the open end, and the rest point goes on the old straight line at lid_rest, so the Mech moves as before."""
    mod, cal = _eyes(), dict(cal)
    for pin in mod.LIDS:
        name = mod.NAME[pin]
        if name + "_flip" not in cal:
            continue
        lo, hi = cal[name + "_lo"], cal[name + "_hi"]
        closed, opened = (mod.mirror(pin, a) for a in ((hi, lo) if cal.pop(name + "_flip") else (lo, hi)))
        rest = closed + (opened - closed) * cal.get("lid_rest", mod.DEFAULT_CAL["lid_rest"])
        cal.update({name + "_lo": closed, name + "_rest": round(rest, 2), name + "_hi": opened})
    return cal


def ranges(cal=None):
    mod = _eyes()
    e = mod.Eyes()
    e.cal.update(cal or {})
    return {pin: e.range(pin) for pin in mod.NAME}


def hold_ms(log, total_ms, ranges, margin_deg):
    """Per pin, the longest continuous time spent within margin_deg of a range end."""
    out = {}
    for pin, (lo, hi) in ranges.items():
        ev = [(t, a) for t, p, a in log if p == pin]
        best = run = 0
        for (t, a), t_next in zip(ev, [t for t, _ in ev[1:]] + [total_ms], strict=False):
            run = run + (t_next - t) if a <= lo + margin_deg or a >= hi - margin_deg else 0
            best = max(best, run)
        out[pin] = best
    return out


def near_stop_holds(lines, cal=None, margin_deg=10):
    log, total = play(lines, cal)
    return hold_ms(log, total, ranges(cal), margin_deg)
