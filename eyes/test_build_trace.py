from build_trace import resample, saccades

def rows(spec):
    """spec: list of (ms, x or 'nan', lab)."""
    return [{"n": str(t), "x": str(x), "val": "4" if x == "nan" else "0", "lab": str(lab)} for t, x, lab in spec]

def test_resample_scales_clamps_holds_and_finds_blinks():
    spec = [(t, 5.0, 1) for t in range(0, 200)] + [(t, "nan", -1) for t in range(200, 300)] + [(t, 30.0, 1) for t in range(300, 400)]
    x, blinks = resample(rows(spec), hz=25, gain=1.6, max_deg=24.0, min_blink_ms=50)
    assert len(x) == 10 and x[0] == 8.0 and x[-1] == 24.0 and x[5] == 8.0
    assert blinks == [5]

def test_short_gaps_are_not_blinks():
    spec = [(t, 0.0, 1) for t in range(0, 100)] + [(t, "nan", -1) for t in range(100, 120)] + [(t, 0.0, 1) for t in range(120, 200)]
    assert resample(rows(spec))[1] == []

def test_saccade_profile_runs_from_zero_to_about_one():
    # a 20 deg saccade over 60 ms with a 5% undershoot corrected at 120 ms, then steady
    spec = [(t, 0.0, 1) for t in range(0, 100)]
    spec += [(100 + k, 19.0 * k / 60, 2) for k in range(0, 61)]
    spec += [(161 + k, 19.0, 1) for k in range(0, 59)] + [(220 + k, 20.0, 1) for k in range(0, 300)]
    prof = saccades(rows(spec), amps=(20,))[20]
    assert len(prof) == 16 and prof[0] == 0.0 and 0.9 <= prof[6] <= 1.0 and abs(prof[-1] - 1.0) < 0.06
