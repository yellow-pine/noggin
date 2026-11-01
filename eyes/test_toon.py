"""Toon timing (#258, docs/research/2026-11-01-toon-eyes.md): every gesture as the Core plays it under the real
eyes/calibration.json, judged on its servo timeline (replay.play): never faster than the servo slews, and the toon
shape (anticipation, ease-in close, holds, overshoot past the level and settle)."""

import json
import os

import pytest
import replay
import servo

CAL = json.load(open(os.path.join(os.path.dirname(__file__), "calibration.json")))
EYES = replay._eyes()
R_LID, L_LID, L_EYE = EYES.R_LID, EYES.L_LID, EYES.L_EYE
RATE = servo.rate(min(servo.SPEC))  # 428 deg/s: the slower rated slew, at the pack's low end (4.8 V)


def timeline(lines, pin):
    """[(ms, angle)] of one servo's writes, the last of any at the same ms, and the total ms."""
    log, total = replay.play(lines, CAL)
    ev = {}
    for t, p, a in log:
        if p == pin:
            ev[t] = a
    return sorted(ev.items()), total


def lid(f, pin=R_LID):
    """A lid level's servo degrees under the calibration (the right lid: open is the high end)."""
    e = EYES.Eyes()
    e.cal.update(CAL)
    return e._lid_angle(pin, f)


def ticks(e):
    for t in range(0, 60_000, 100):
        e.tick(t)


@pytest.mark.parametrize(
    "lines",
    [[f"{g} {i}"] for g in ("eureka", "attention", "bored", "wince", "wink") for i in (1, 2, 3)]
    + [["thinking", ticks], ["set think_trace 1", "thinking", ticks]],
    ids=str,
)
def test_no_write_asks_more_than_the_servo_slews(lines):
    """Each write is reached before the next write of that servo comes, at the rated slew (eyes/servo.py); the last
    one has the hold after the gesture."""
    for pin in EYES.NAME:
        ev, _ = timeline(["rest", *lines], pin)
        for (_, a0), (t, a), t_next in zip(ev, ev[1:], [t for t, _ in ev[2:]] + [float("inf")], strict=False):
            assert abs(a - a0) <= RATE * (t_next - t) / 1000 + 0.01, (lines, pin, t, a0, a, t_next)


def after_rest(*lines, pin=R_LID):
    """One servo's writes for lines played from rest, times from the end of the rest pose."""
    start = replay.play(["rest"], CAL)[1]
    ev, total = timeline(["rest", *lines], pin)
    return [(t - start, a) for t, a in ev if t >= start], total - start


def test_blink_lifts_eases_shut_holds_and_reopens_past_rest():
    """Target (#258): a tiny lift, ~150 ms slow-in close, ~80 ms hold, ~250 ms slow-out reopen a little past rest,
    settle. The right lid: open is the high end."""
    ev, _ = after_rest(lambda e: e.blink())
    rest, shut = lid(CAL["lid_rest"]), lid(CAL["lid_closed"])
    top = max(range(len(ev) // 3), key=lambda k: ev[k][1])  # the lift's peak, before the close
    closed = next(k for k, (_, a) in enumerate(ev) if a == pytest.approx(shut))
    assert rest < ev[top][1] < lid(CAL["lid_rest"] + 0.1)  # anticipation: up a touch first
    assert ev[closed][0] - ev[top][0] >= 140  # the close
    steps = [ev[k][1] - ev[k + 1][1] for k in range(top, closed)]
    assert steps[0] < steps[-1] / 3  # slow in: starts gently, lands fast
    assert ev[closed + 1][0] - ev[closed][0] >= 80  # held shut
    reopen = ev[closed + 1 :]
    peak = max(range(len(reopen)), key=lambda k: reopen[k][1])
    assert rest < reopen[peak][1] < lid(CAL["lid_rest"] + 0.1)  # overshoot, small
    assert reopen[peak][0] - ev[closed][0] >= 200 and reopen[-1][1] == pytest.approx(rest)  # slow out, settles


def test_wink_closes_fully_holds_and_the_other_lid_squints():
    """wink 2, the mech's right lid: ~200 ms close to lid_closed, held ~350 ms, the left lid squints 20% and stays
    open, the 8 deg glance held through it."""
    ev, _ = after_rest("wink 2")
    other, _ = after_rest("wink 2", pin=L_LID)
    eye, _ = after_rest("wink 2", pin=L_EYE)
    shut = lid(CAL["lid_closed"])
    closed = [t for t, a in ev if a == pytest.approx(shut)]
    assert len(closed) == 1  # one write at lid_closed, then held until the reopen
    t_shut = closed[0]
    t_open = next(t for t, _ in ev if t > t_shut)
    before = [(a, t) for t, a in ev if t < t_shut]
    start = max(before)[1]  # the lift's peak, where the close starts
    assert t_shut - start >= 180 and t_open - t_shut >= 350
    squint = max(a for _, a in other)  # the left servo is mirrored: closing is up
    assert squint == pytest.approx(lid(0.8 * CAL["lid_rest"], L_LID))
    glance = [a for t, a in eye if t <= start]
    assert abs(glance[-1] - (88 - 8)) < 0.01  # centre 88, 8 deg toward the right lid
    assert not [t for t, _ in eye if start < t <= t_open]  # and held through the wink


def test_spontaneous_blinks_vary_in_depth_most_shut():
    """Thinking's idle blinks: most close at lid_closed, a few stop a little short."""
    ev, _ = after_rest("thinking", ticks)  # a minute
    shut, short = lid(CAL["lid_closed"]), lid(CAL["lid_closed"] + 0.1)
    lows = [b for a, b, c in zip(ev, ev[1:], ev[2:], strict=False) if b[1] < a[1] and b[1] <= c[1] and b[1] < short]
    full = [t for t, a in lows if a == pytest.approx(shut)]
    assert len(lows) >= 6 and len(full) > len(lows) / 2 and len(full) < len(lows)


def test_eureka_squashes_before_the_take_and_settles_past_rest():
    """Anticipation: the lids narrow below rest before they pop wide; the end eases past rest (lower) and settles."""
    ev, _ = after_rest("eureka 2")
    rest = lid(CAL["lid_rest"])
    wide = next(k for k, (_, a) in enumerate(ev) if a > lid(CAL["lid_open"] - 0.01))
    assert min(a for _, a in ev[:wide]) < lid(CAL["lid_think"] + 0.01)
    last_blink = max(k for k, (_, a) in enumerate(ev) if a == pytest.approx(lid(CAL["lid_closed"])))
    tail = [a for _, a in ev[last_blink:]]
    settle = tail[max(range(len(tail)), key=lambda k: tail[k]) :]  # from the blink's reopen peak down to rest
    assert min(settle) < rest - 1 and settle[-1] == pytest.approx(rest)
