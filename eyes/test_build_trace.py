from build_trace import resample, saccades


def rows(spec):
    """spec: list of (ms, x or 'nan', lab)."""
    return [{"n": str(t), "x": str(x), "val": "4" if x == "nan" else "0", "lab": str(lab)} for t, x, lab in spec]


def test_resample_scales_clamps_holds_and_finds_blinks():
    spec = (
        [(t, 5.0, 1) for t in range(0, 200)]
        + [(t, "nan", -1) for t in range(200, 300)]
        + [(t, 30.0, 1) for t in range(300, 400)]
    )
    x, blinks = resample(rows(spec), hz=25, gain=1.6, max_deg=24.0, min_blink_ms=50)
    assert len(x) == 10 and x[0] == 8.0 and x[-1] == 24.0 and x[5] == 8.0
    assert blinks == [5]


def test_short_gaps_are_not_blinks():
    spec = (
        [(t, 0.0, 1) for t in range(0, 100)]
        + [(t, "nan", -1) for t in range(100, 120)]
        + [(t, 0.0, 1) for t in range(120, 200)]
    )
    assert resample(rows(spec))[1] == []


def test_saccade_profile_runs_from_zero_to_about_one():
    # a 20 deg saccade over 60 ms with a 5% undershoot corrected at 120 ms, then steady
    spec = [(t, 0.0, 1) for t in range(0, 100)]
    spec += [(100 + k, 19.0 * k / 60, 2) for k in range(0, 61)]
    spec += [(161 + k, 19.0, 1) for k in range(0, 59)] + [(220 + k, 20.0, 1) for k in range(0, 300)]
    prof = saccades(rows(spec), amps=(20,))[20]
    assert len(prof) == 16 and prof[0] == 0.0 and 0.9 <= prof[6] <= 1.0 and abs(prof[-1] - 1.0) < 0.06


def test_calmest_window_finds_the_flat_part():
    from build_trace import calmest

    xs = [((i % 7) - 3) * 4.0 for i in range(0, 250)] + [1.0] * 200 + [((i % 5) - 2) * 6.0 for i in range(0, 250)]
    assert 250 <= calmest(xs, hz=25, dur_s=6) <= 275


def test_clamp_rate_limits_every_step_and_counts_them():
    from build_trace import clamp_rate

    xs, n = clamp_rate([0.0, 30.0, 30.0, -10.0], dt_s=0.04, rate=500)  # 20 deg per 40 ms sample
    assert xs == [0.0, 20.0, 30.0, 10.0] and n == 2


def test_generated_traces_never_exceed_the_rated_servo_slew():
    import gaze_trace
    import servo
    from build_trace import HZ

    for name in ("THINK", "SCAN", "CALM"):
        xs = [((b - 256) if b > 127 else b) / 2 for b in getattr(gaze_trace, name)]
        assert max(abs(a - b) for a, b in zip(xs, xs[1:], strict=False)) * HZ <= servo.RATE_DEG_S + 0.5 * HZ, (
            name
        )  # half-degree rounding
    for amp, prof in gaze_trace.SACCADE.items():
        assert (
            max(abs(a - b) for a, b in zip(prof, prof[1:], strict=False)) * amp * 100
            <= servo.RATE_DEG_S + 0.005 * amp * 100
        ), amp  # 0.01 rounding
