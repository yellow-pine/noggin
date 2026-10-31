import servo


def test_fit_reproduces_the_published_figures_at_6v():
    assert abs(servo.current(0, servo.RATE_DEG_S) - 0.060) < 1e-9  # no-load: running figure
    assert abs(servo.current(servo.STALL_KGFCM, 0) - 0.650) < 1e-9  # stall figure


def test_current_rises_with_torque_and_never_exceeds_stall():
    i = [servo.current(t / 10, 0) for t in range(0, 13)]
    assert all(a < b for a, b in zip(i, i[1:], strict=False))
    assert servo.current(5.0, 0) == servo.current(servo.STALL_KGFCM, 0)  # winding-limited


def test_4v8_figures_fit_too():
    assert abs(servo.current(0, servo.rate(4.8), volts=4.8) - 0.050) < 1e-9
    assert abs(servo.current(1.0, 0, volts=4.8) - 0.550) < 1e-9


def test_plant_reaches_a_60_deg_step_in_rated_time():
    s = servo.Plant(90)
    t, dt = 0.0, 0.005
    while True:
        s.step(150, dt)
        t += dt
        assert t < 1.0
        if s.holding:
            break
    assert abs(s.pos - 150) < 1e-6 and abs(t - 0.12) < 0.011
    s.step(150, dt)
    assert s.holding
