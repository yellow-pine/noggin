"""Toon timing (#258, docs/research/2026-11-01-toon-eyes.md): every gesture as the Core plays it under the real
eyes/calibration.json, judged on its servo timeline (replay.play): never faster than the servo slews, and the toon
shape (anticipation, ease-in close, holds, overshoot past the level and settle)."""

import json
import math
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
    [[f"{g} {i}"] for g in EYES.Eyes.GESTURES for i in (1, 2, 3)]
    + [[ticks], ["thinking", ticks], ["set think_trace 1", "thinking", ticks]],
    ids=lambda lines: " ".join(x if isinstance(x, str) else "ticks" for x in lines),  # stable across xdist workers
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


def clocked_ticks(e):
    """A minute of tick() with the simulated clock running between them, as boot.py's loop has it."""
    for t in range(0, 60_000, 100):
        e.tick(t)
        EYES.sleep_ms(100)


@pytest.mark.parametrize(
    "lines",
    [[f"{g} {i}"] for g in EYES.Eyes.GESTURES for i in (1, 2, 3)]
    + [[clocked_ticks], ["thinking", clocked_ticks], ["set think_trace 1", "thinking", clocked_ticks]]
    + [["exercise 1", clocked_ticks]],
    ids=lambda lines: " ".join(x if isinstance(x, str) else "ticks" for x in lines),
)
def test_a_servo_is_written_at_most_once_a_frame(lines):
    """#619: the ESP32-C3's LEDC takes a new duty only at the next 20 ms PWM period, so a second write within one
    is lost (docs/research/2026-11-02-literature-motion-control.md 1)."""
    log, _ = replay.play(["rest", *lines], CAL)
    last = {}
    for t, pin, _ in log:
        assert t - last.get(pin, -20) >= 20, (lines, pin, t, last.get(pin))
        last[pin] = t


def jumps(lines):
    """[(start ms, end ms, pin)] of every jump (a write made by Eyes.step, at the servo's full slew): it draws stall
    current from its write until the servo arrives at the rated slew."""
    out, clock, inside = [], [0], [False]

    def hook(e):
        sleep, step, put = EYES.sleep_ms, e.step, e.set
        EYES.sleep_ms = lambda ms: (clock.__setitem__(0, clock[0] + ms), sleep(ms))  # pyright: ignore[reportAttributeAccessIssue]

        def stepping(targets):
            inside[0] = True
            step(targets)
            inside[0] = False

        def setting(targets):
            before = dict(e.pos)
            put(targets)
            if inside[0]:
                out.extend((clock[0], clock[0] + abs(e.pos[p] - before[p]) * 1000 / RATE, p) for p in targets)

        e.step, e.set = stepping, setting

    replay.play([hook, "rest", *lines], CAL)
    return out


def most_at_once(js):
    """The most servos ever mid-jump together: at each jump's start, the pins whose latest jump has not arrived."""
    most = 0
    for s, _, _ in js:
        latest = {p: end for start, end, p in js if start <= s}
        most = max(most, sum(end > s for end in latest.values()))
    return most


@pytest.mark.parametrize(
    "lines",
    [[f"{g} {i}"] for g in EYES.Eyes.GESTURES for i in (1, 2, 3)]
    + [["thinking", clocked_ticks], ["set think_trace 1", "thinking", clocked_ticks]],
    ids=lambda lines: " ".join(x if isinstance(x, str) else "ticks" for x in lines),
)
def test_at_most_two_servos_jump_at_once(lines):
    """#620's start budget: a jump draws stall current (0.55-0.65 A) until the servo arrives, so a Core lets at most two
    servos jump at once (docs/research/2026-11-02-literature-motion-control.md 4, Practice 4)."""
    js = jumps(lines)
    assert js and most_at_once(js) <= 2, lines


def test_a_jump_past_the_budget_waits_a_whole_move():
    """All four servos asked to jump at once: the first two go, the other two start once one of them arrived, on a
    frame (stagger by whole move durations: two minimum-jerk moves together peak at 2.0x, 0.3 T apart at 1.42x)."""
    lids_open = {R_LID: lid(CAL["lid_open"]), L_LID: lid(CAL["lid_open"], L_LID)}
    js = jumps([lambda e: e.step({**lids_open, L_EYE: 108, EYES.R_EYE: 108})])
    starts = {p: s for s, _, p in js}
    first = min(end for s, end, p in js if p in lids_open)
    assert starts[R_LID] == starts[L_LID] and most_at_once(js) == 2
    assert starts[L_EYE] == starts[EYES.R_EYE] >= first and (starts[L_EYE] - starts[R_LID]) % 20 == 0


def test_a_glide_is_minimum_jerk_at_rest_at_both_ends():
    """#619: a move between keyframes follows minimum jerk, x = D(10t^3 - 15t^4 + 6t^5) (Flash & Hogan 1985): it
    starts and lands at rest, where the old eases landed at full speed; a quarter of the time in it is 10.35% of the
    way, half the time in half the way."""
    ev, _ = after_rest(lambda e: e.lids(CAL["lid_open"] - 0.15, 400))
    a0, a1 = lid(CAL["lid_rest"]), lid(CAL["lid_open"] - 0.15)
    way = [(a - a0) / (a1 - a0) for _, a in ev]
    assert [t for t, _ in ev] == list(range(0, 400, 20))  # one write a frame, over the 400 ms asked
    assert way[4] == pytest.approx(0.1035, abs=1e-3) and way[9] == pytest.approx(0.5) and way[-1] == pytest.approx(1)
    steps = [b - a for a, b in zip([0, *way], way, strict=False)]
    assert max(steps[0], steps[-1]) < max(steps) / 50


def test_a_short_move_stretches_to_the_acceleration_cap():
    """#619: a 4 deg eye move asked in one frame takes two. Minimum jerk peaks at 5.77 D/T^2, so at the cap (half the
    stall torque at 4.8 V on the rotor's inertia through the gears, 28,094 deg/s^2) it needs T = 29 ms, where the slew
    alone (1.875 D/T at 428 deg/s) allows 18."""
    ev, _ = after_rest(lambda e: e.eyes(EYES.EYE_CENTER + 4, 20), pin=L_EYE)
    assert len(ev) == 2


def test_the_cap_is_half_the_stall_torque_on_the_rotor():
    """The Core's copy of the cap (eyes.py cannot import eyes/servo.py) against its source."""
    stall_nm = servo.SPEC[4.8]["stall_kgfcm"] * 0.0980665
    assert EYES.ACCEL == pytest.approx(math.degrees(stall_nm / 2 / servo.ARMATURE), abs=1)


def test_blink_lifts_closes_holds_and_reopens_past_rest():
    """Target (#258): a tiny lift, ~150 ms close, ~80 ms hold, ~250 ms reopen a little past rest,
    settle. The right lid: open is the high end."""
    ev, _ = after_rest(lambda e: e.blink())
    rest, shut = lid(CAL["lid_rest"]), lid(CAL["lid_closed"])
    top = max(range(len(ev) // 3), key=lambda k: ev[k][1])  # the lift's peak, before the close
    closed = next(k for k, (_, a) in enumerate(ev) if a == pytest.approx(shut))
    assert rest < ev[top][1] < lid(CAL["lid_rest"] + 0.1)  # anticipation: up a touch first
    assert ev[closed][0] - ev[top][0] >= 140  # the close
    steps = [ev[k][1] - ev[k + 1][1] for k in range(top, closed)]
    assert max(steps[0], steps[-1]) < max(steps) / 3  # minimum jerk (#619): starts and lands at rest
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
    reopen = [a for t, a in ev if t >= t_open]
    assert max(reopen) > lid(CAL["lid_rest"]) and reopen[-1] == pytest.approx(lid(CAL["lid_rest"]))  # overshoot
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


def closures(lines):
    """When the right lid reaches lid_closed: each blink's shut moment, times from the end of the rest pose."""
    ev, _ = after_rest(*lines)
    shut = lid(CAL["lid_closed"])
    return [b[0] for a, b in zip(ev, ev[1:], strict=False) if b[1] == pytest.approx(shut) != a[1]]


def test_rest_blinks_every_3_to_6_s():
    """#621: a face held still reads as lifeless after ~1.7 s (docs/research/2026-11-02-literature-perception.md), so at
    Rest the lids blink once every 3-6 s, at random within that (a blink takes ~0.5 s), and nothing else moves."""
    shut = closures([clocked_ticks])  # a minute at rest
    gaps = [b - a for a, b in zip(shut, shut[1:], strict=False)]
    assert 9 <= len(shut) <= 20 and min(gaps) >= 3000 and max(gaps) <= 6600, gaps
    assert max(gaps) - min(gaps) > 1000  # random, not a metronome
    eye, _ = after_rest(clocked_ticks, pin=L_EYE)
    assert not eye  # the eyes stay centred


def test_a_gesture_restarts_the_rest_blink_gap():
    """A gesture that ends on a blink (attention) is not followed at once by a rest blink that fell due while it
    played: the next one comes a whole gap after it."""
    _, end = after_rest(lambda e: e.tick(0), "attention 2")
    assert not [t for t in closures([lambda e: e.tick(0), "attention 2", lambda e: e.tick(60_000)]) if t >= end]


@pytest.mark.parametrize("still", ["pose lids 0.5", "release"])
def test_a_held_pose_or_a_release_never_blinks(still):
    """The noggin service holds a pose with `rest` then `pose ...` (tuning), and `release` unpowers the servos while
    muted: a rest blink would move the pose being tuned or re-power a slumped Mech."""
    ev, _ = after_rest(still, clocked_ticks)
    assert all(t < 1000 for t, _ in ev)  # only the pose's own glide, then nothing


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
