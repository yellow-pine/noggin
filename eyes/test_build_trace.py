from build_trace import resample

def rows(spec):
    """spec: list of (ms, x or 'nan')."""
    return [{"n": str(t), "x": str(x), "val": "4" if x == "nan" else "0"} for t, x in spec]

def test_resample_scales_clamps_and_finds_blinks():
    spec = [(t, 5.0) for t in range(0, 200)] + [(t, "nan") for t in range(200, 300)] + [(t, 30.0) for t in range(300, 400)]
    x, blinks = resample(rows(spec), hz=25, gain=1.6, max_deg=24.0, min_blink_ms=50)
    assert len(x) == 10                       # 400 ms at 25 Hz
    assert x[0] == 8.0 and x[-1] == 24.0      # gain, then clamp
    assert x[5] == 8.0                        # held through the blink gap
    assert blinks == [5]                      # gap of 100 ms starting at sample 5

def test_short_gaps_are_not_blinks():
    spec = [(t, 0.0) for t in range(0, 100)] + [(t, "nan") for t in range(100, 120)] + [(t, 0.0) for t in range(120, 200)]
    assert resample(rows(spec))[1] == []
