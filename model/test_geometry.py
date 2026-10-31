"""Seam: model/geometry.py public data and functions. Expected values are literals from docs/research/2026-10-31-model.md."""

from model import geometry as g


def test_bracket_stem_centre_maps_to_tilt_window():
    assert g.eyes_to_pt((29.5, -45.6, 15.5)) == (0.0, -13.0, 35.9)


def test_transform_round_trips():
    for p in [(0, 0, 0), (59, 0, 0), (29.5, -45.6, 15.5), (-14.8, -25.6, 51)]:
        back = g.pt_to_eyes(g.eyes_to_pt(p))
        assert all(abs(a - b) < 1e-9 for a, b in zip(back, p))


def test_mirror_x_maps_left_eye_to_right():
    assert g.mirror_x(g.EYE_L) == g.EYE_R


def test_horn_limits_match_designer_config():
    assert g.HORN_LIMITS == {
        "l_lid": (70, 120),
        "l_eye": (70, 110),
        "r_lid": (70, 120),
        "r_eye": (70, 110),
        "tilt": (20, 150),
        "rotate": (40, 160),
        "mouth": (50, 90),  # mouth: opening side only (config says 0..180), see geometry.py
    }


def test_bars_are_measured_pivot_spacings():
    assert g.BARS == {
        "eyelid_bar": 41.0,
        "eyelid_crank": 41.0,
        "tilt_bar": 20.0,
        "pan_bar": 15.0,
        "connector_bar": 31.4,
        "eyeball_bar": 27.0,
    }


def _dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def test_servo_tab_holes_are_27_8_apart():
    assert g.SERVO_TAB_SPACING == 27.8
    assert set(g.SERVOS) == {"l_lid", "r_lid", "l_eye", "r_eye", "tilt", "pan", "jaw"}
    for s in g.SERVOS.values():
        a, b = s["tab_holes"]
        # shortcut: 0.25 mm tolerance, the lid (27.70) and tilt (27.58) pairs are mesh-measured; tighten once re-measured
        assert abs(_dist(a, b) - 27.8) < 0.25


def test_receiver_standoffs_form_23_by_24_rectangle():
    sets = [
        g.STANDOFFS["eyes_base"]["receiver"],
        g.STANDOFFS["pt_base"]["receiver_1"],
        g.STANDOFFS["pt_base"]["receiver_2"],
    ]
    for pts in sets:
        assert len(pts) == 4
        extents = sorted(round(max(c) - min(c), 6) for c in zip(*pts))
        assert extents == [0, 23, 24]


def test_pivots_name_frame_axis_and_inferred_shafts():
    assert set(g.PIVOTS) == {
        "l_lid",
        "r_lid",
        "l_eye",
        "r_eye",
        "l_lid_horn",
        "r_lid_horn",
        "l_eye_horn",
        "r_eye_horn",
        "jaw_hinge",
        "jaw_horn",
        "pan",
        "tilt",
        "tilt_horn",
        "pan_horn",
    }
    assert g.PIVOTS["tilt"] == {"point": (0.0, -13.0, 33.4), "axis": (1, 0, 0), "frame": "pt"}
    assert g.PIVOTS["jaw_hinge"] == {"point": (29.5, -49.6, 8.0), "axis": (1, 0, 0), "frame": "eyes"}
    assert g.PIVOTS["r_eye"]["point"] == g.mirror_x(g.PIVOTS["l_eye"]["point"])
    for name, p in g.PIVOTS.items():
        assert p["frame"] in ("eyes", "pt")
        assert name.endswith("_horn") == bool(p.get("inferred"))


def test_servo_frame_puts_tab_holes_on_the_measured_holes_and_shaft_toward_the_horn():
    for key, shaft_dir in [("l_lid", (-1, 0, 0)), ("r_lid", (1, 0, 0)), ("l_eye", (0, 1, 0)), ("r_eye", (0, 1, 0))]:
        origin, tab_x, shaft = g.servo_frame(key)
        assert shaft == shaft_dir
        shaft_x = g.SERVO_STEP["shaft"][0]
        placed = [[o + (h[0] - shaft_x) * u for o, u in zip(origin, tab_x)] for h in g.SERVO_STEP["tab_holes"]]
        for hole in g.SERVOS[key]["tab_holes"]:
            # shortcut: 0.5 mm, the horn pivots are inferred to +-4 mm; tighten when the shafts are measured
            assert min(_dist(p, hole) for p in placed) < 0.5, (key, placed, hole)


def test_pan_tilt_servo_frames_put_tab_holes_on_the_measured_holes():
    for key, shaft_dir in [("tilt", (-1, 0, 0)), ("pan", (0, 0, 1))]:
        origin, tab_x, shaft = g.servo_frame(key)
        assert shaft == shaft_dir
        shaft_x = g.SERVO_STEP["shaft"][0]
        placed = [[o + (h[0] - shaft_x) * u for o, u in zip(origin, tab_x)] for h in g.SERVO_STEP["tab_holes"]]
        for hole in g.SERVOS[key]["tab_holes"]:
            assert min(_dist(p, hole) for p in placed) < 0.5, (key, placed, hole)


def test_pan_tilt_horn_pins_close_the_bar_loops_on_the_guide_side():
    for key, axis in (("tilt", 0), ("pan", 2)):
        pin, lever = g.horn_pin(key)
        hub = g.PIVOTS[key + "_horn"]["point"]
        plane = g.PT_BAR_PLANES[key][1]
        assert pin[axis] == lever[axis] == plane
        in_plane = lambda p: [c for i, c in enumerate(p) if i != axis]
        assert abs(_dist(in_plane(pin), in_plane(hub)) - g.HORN_STEP["pin"]) < 1e-6
        assert abs(_dist(pin, lever) - g.BARS[key + "_bar"]) < 1e-6
    tilt_pin, _ = g.horn_pin("tilt")
    assert tilt_pin[1] > g.PIVOTS["tilt_horn"]["point"][1] + 12  # horn horizontal toward +Y
    pan_pin, _ = g.horn_pin("pan")
    assert pan_pin[1] < g.PIVOTS["pan_horn"]["point"][1] - 12  # horn forward (-Y)


def test_jaw_servo_frame_and_horn_pin_close_the_connector_bar_loop_below_the_hub():
    origin, tab_x, shaft = g.servo_frame("jaw")
    assert shaft == (-1, 0, 0) and origin == (
        75.9,
        -48.6,
        23.1,
    )  # tab plane at the mount lug, the horn seat 10.35 inboard
    assert abs(g.PIVOTS["jaw_horn"]["point"][0] - (75.9 - g.SERVO_STEP["horn_seat"])) < 1e-9
    pin, lever = g.horn_pin("jaw")
    assert pin[0] == lever[0] == 58.9 and lever[1:] == (-58.1, -10.44)
    hub = g.PIVOTS["jaw_horn"]["point"]
    assert abs(_dist(pin[1:], hub[1:]) - g.HORN_STEP["pin"]) < 1e-6
    assert abs(_dist(pin, lever) - g.BARS["connector_bar"]) < 1e-6
    assert pin[1] < hub[1] - 10  # horn pointing down (-Y), away from the bracket rail


def test_stage_documents_place_each_sub_assembly_once_in_the_pt_frame():
    # Research note: the stem (eyes x 23.5..35.5, z 13..18, bottom y=-45.6) drops through the pan recess at the PT origin in
    # the desk build (plate top z=3 is y=-35.6) and into the tilt arm window (0, -13) in the neck build, where the eye centres
    # sit 78.5 above the plate top; the Mech centreline x=29.5 (eyes) is the pan axis. The mouth rides in the eyes frame.
    pt = ((0, 0, 0), g.X, g.Z)
    assert g.STAGES["noggin-stage1"] == {"noggin-base": pt, "noggin-eyes": g.EYES_ON_BASE}
    assert g.STAGES["noggin-stage2"] == {"noggin-base": pt, "noggin-stack": pt, "noggin-eyes": g.EYES_ON_STACK}
    assert g.STAGES["noggin-stage3"] == {**g.STAGES["noggin-stage2"], "noggin-mouth": g.EYES_ON_STACK}
    assert g.in_frame(g.EYES_ON_STACK, g.EYE_L) == (29.5, -28.5, 81.5)
    assert g.in_frame(g.EYES_ON_STACK, g.EYE_R) == (-29.5, -28.5, 81.5)
    assert g.in_frame(g.EYES_ON_STACK, g.STEM_BOTTOM) == (0.0, -13.0, 35.9)
    assert g.in_frame(g.EYES_ON_BASE, g.STEM_BOTTOM) == (0.0, 0.0, -7.0)  # through the 5 mm plate, feet on its top
    assert g.STEM_IN == {"noggin-stage1": "PandT base", "noggin-stage2": "tilt arm", "noggin-stage3": "tilt arm"}
    for p in [(0, 0, 0), (59, 0, 0), (-14.8, -25.6, 51)]:
        assert all(abs(a - b) < 1e-9 for a, b in zip(g.in_frame(g.EYES_ON_STACK, p), g.eyes_to_pt(p)))
