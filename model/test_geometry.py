"""Seam: model/geometry.py public data and functions. Expected values are literals from docs/research/2026-10-31-model.md
and docs/research/2026-10-31-shafts.md (servo shafts, horn seat)."""

from model import geometry as g


def test_bracket_stem_centre_maps_to_tilt_window():
    assert g.eyes_to_pt((29.5, -45.6, 15.5)) == (0.0, -13.0, 35.9)


def test_transform_round_trips():
    for p in [(0, 0, 0), (59, 0, 0), (29.5, -45.6, 15.5), (-14.8, -25.6, 51)]:
        back = g.pt_to_eyes(g.eyes_to_pt(p))
        assert all(abs(a - b) < 1e-9 for a, b in zip(back, p))


def test_mirror_x_maps_left_eye_to_right():
    assert g.mirror_x(g.EYE_L) == g.EYE_R


def test_every_horn_limit_is_ours_with_its_reason():
    assert g.HORN_LIMITS == {
        "l_lid": (41, 129),
        "l_eye": (68, 112),
        "r_lid": (41, 129),
        "r_eye": (68, 112),
        "tilt": (30, 150),
        "rotate": (50, 160),
        "mouth": (15, 90),
    }
    assert g.LIMITS.keys() == g.HORN_LIMITS.keys()
    assert all(rng == g.HORN_LIMITS[k] and len(why) > 20 for k, (rng, why) in g.LIMITS.items())


def test_bars_are_measured_pivot_spacings():
    assert g.BARS == {
        "lid_bar": 41.0,
        "lid_crank": 41.0,
        "tilt_bar": 20.0,
        "pan_bar": 15.0,
        "jaw_bar": 44.1,
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


def test_pivots_name_frame_axis_and_none_is_inferred():
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
    for p in g.PIVOTS.values():
        assert p["frame"] in ("eyes", "pt")
        assert not p.get("inferred")  # every shaft settled by the STEPs, STLs and guide pictures (#62)


def test_horn_pivots_sit_at_the_horn_seat_on_the_shaft_the_guides_show():
    # docs/research/2026-10-31-shafts.md: horn inner face, shaft 8.56 from the near tab hole, flange on the lug face
    want = {
        "l_lid_horn": ((-19.59, -13.21, 40.0), (1, 0, 0)),
        "r_lid_horn": ((78.59, -13.21, 40.0), (1, 0, 0)),
        "l_eye_horn": ((2.56, -1.63, 27.0), (0, 1, 0)),  # the case side on the bracket floor z 21 (#67)
        "r_eye_horn": ((56.44, -1.63, 27.0), (0, 1, 0)),
        "tilt_horn": ((15.13, 14.09, 18.38), (1, 0, 0)),  # centred on the tower holes (#67)
        "pan_horn": ((-20.5, 38.11, 27.17), (0, 0, 1)),
        "jaw_horn": ((83.29, -48.6, 33.67), (1, 0, 0)),
    }
    for name, (point, axis) in want.items():
        p = g.PIVOTS[name]
        assert _dist(p["point"], point) < 0.01 and p["axis"] == axis, (name, p)
    assert g.SERVO_STEP["horn_seat"] == 11.52  # spline tip on the bore bottom: STEP z -12.17, tab plane z -0.65


def test_servo_frame_puts_tab_holes_on_the_measured_holes_and_shaft_toward_the_horn():
    for key, shaft_dir in [
        ("l_lid", (-1, 0, 0)),
        ("r_lid", (1, 0, 0)),
        ("l_eye", (0, 1, 0)),
        ("r_eye", (0, 1, 0)),
        ("jaw", (1, 0, 0)),
    ]:
        origin, tab_x, shaft = g.servo_frame(key)
        assert shaft == shaft_dir
        shaft_x = g.SERVO_STEP["shaft"][0]
        placed = [[o + (h[0] - shaft_x) * u for o, u in zip(origin, tab_x)] for h in g.SERVO_STEP["tab_holes"]]
        for hole in g.SERVOS[key]["tab_holes"]:
            # within the mating check's 0.2 (the lugs' pitch is 27.58..28.0 printed against the servo's 27.8)
            assert min(_dist(p, hole) for p in placed) < 0.2, (key, placed, hole)


def test_pan_tilt_servo_frames_put_tab_holes_on_the_measured_holes():
    for key, shaft_dir in [("tilt", (-1, 0, 0)), ("pan", (0, 0, 1))]:
        origin, tab_x, shaft = g.servo_frame(key)
        assert shaft == shaft_dir
        shaft_x = g.SERVO_STEP["shaft"][0]
        placed = [[o + (h[0] - shaft_x) * u for o, u in zip(origin, tab_x)] for h in g.SERVO_STEP["tab_holes"]]
        for hole in g.SERVOS[key]["tab_holes"]:
            # within the mating check's 0.2 (the lugs' pitch is 27.58..28.0 printed against the servo's 27.8)
            assert min(_dist(p, hole) for p in placed) < 0.2, (key, placed, hole)


def test_pan_tilt_horn_pins_close_the_bar_loops_on_the_guide_side():
    for key, axis in (("tilt", 0), ("pan", 2)):
        pin, lever = g.horn_pin(key)
        hub = g.PIVOTS[key + "_horn"]["point"]
        plane = g.PT_BAR_PLANES[key][1]
        assert pin[axis] == lever[axis] == plane == {"tilt": 9.5, "pan": 28.3}[key]  # on the lever face / top
        in_plane = lambda p: [c for i, c in enumerate(p) if i != axis]
        assert abs(_dist(in_plane(pin), in_plane(hub)) - g.HORN_STEP["pin"]) < 1e-6
        assert abs(_dist(pin, lever) - g.BARS[key + "_bar"]) < 1e-6
    tilt_pin, _ = g.horn_pin("tilt")
    assert tilt_pin[1] > g.PIVOTS["tilt_horn"]["point"][1] + 12  # horn horizontal toward +Y
    pan_pin, _ = g.horn_pin("pan")
    assert pan_pin[1] < g.PIVOTS["pan_horn"]["point"][1] - 12  # horn forward (-Y)


def test_jaw_servo_frame_and_horn_pin_close_the_connector_bar_loop_below_the_hub():
    origin, tab_x, shaft = g.servo_frame("jaw")
    assert shaft == (1, 0, 0) and _dist(origin, (71.77, -48.6, 33.67)) < 1e-9  # tab plane inside the mount plate
    pin, lever = g.horn_pin("jaw")
    # the jaw bar is cranked 13 mm along the pin: horn end flush under the horn arm, jaw end on the jaw lug's outer face
    assert pin[0] == 84.64 and lever == (71.64, -58.1, -10.44)
    hub = g.PIVOTS["jaw_horn"]["point"]
    assert abs(_dist(pin[1:], hub[1:]) - g.HORN_STEP["pin"]) < 1e-6
    assert abs(_dist(pin[1:], lever[1:]) - g.BARS["jaw_bar"]) < 1e-6
    assert pin[1] < hub[1] - 10  # horn pointing down (-Y), away from the bracket rail


def test_stage_documents_place_each_sub_assembly_once_in_the_pt_frame():
    # Research note: the stem (eyes x 23.5..35.5, z 13..18, bottom y=-45.6) drops through the pan recess at the PT origin in
    # the desk build (plate top z=3 is y=-35.6) and into the tilt arm window (0, -13) in the neck build, where the eye centres
    # sit 78.5 above the plate top; the Mech centreline x=29.5 (eyes) is the pan axis. The mouth rides in the eyes frame.
    pt = ((0, 0, 0), g.X, g.Z)
    assert g.STAGES["noggin-stage1"] == {"noggin-base": pt, "noggin-eyes": g.EYES_ON_BASE}
    assert g.STAGES["noggin-stage2"] == {"noggin-base": pt, "noggin-stack": pt, "noggin-eyes": g.EYES_ON_STACK}
    assert g.STAGES["noggin-stage3"] == {**g.STAGES["noggin-stage2"], "noggin-mouth": g.EYES_ON_STACK}
    on_stack, on_base = (lambda p, f=f: _apply(g.align_rows(*f), p) for f in (g.EYES_ON_STACK, g.EYES_ON_BASE))
    assert on_stack(g.EYE_L) == (29.5, -28.5, 81.5)
    assert on_stack(g.EYE_R) == (-29.5, -28.5, 81.5)
    assert on_stack(g.STEM_BOTTOM) == (0.0, -13.0, 35.9) == g.STEM_AT["noggin-stage2"]
    assert (
        on_base(g.STEM_BOTTOM) == (0.0, 0.0, -7.0) == g.STEM_AT["noggin-stage1"]
    )  # through the 5 mm plate, feet on its top
    assert g.STEM_IN == {"noggin-stage1": "base plate", "noggin-stage2": "tilt arm", "noggin-stage3": "tilt arm"}
    for p in [(0, 0, 0), (59, 0, 0), (-14.8, -25.6, 51)]:
        assert all(abs(a - b) < 1e-9 for a, b in zip(on_stack(p), g.eyes_to_pt(p)))


def _apply(rows, p):
    return tuple(round(sum(r[i] * c for i, c in enumerate((*p, 1.0))), 9) + 0.0 for r in rows[:3])


def test_align_rows_take_a_local_frame_onto_a_world_frame():
    assert g.align_rows((1, 2, 3)) == [[1, 0, 0, 1], [0, 1, 0, 2], [0, 0, 1, 3], [0, 0, 0, 1]]
    m = g.align_rows((10, 0, 0), (0, 1, 0), (0, 0, 1))  # local x onto world y, about z
    assert _apply(m, (1, 0, 0)) == (10.0, 1.0, 0.0) and _apply(m, (0, 1, 0)) == (9.0, 0.0, 0.0)
    m = g.align_rows((0, 0, 0), (1, 0, 0), (0, 0, 1), from_origin=(5, 5, 0))  # the local point (5, 5) onto the origin
    assert _apply(m, (5, 5, 0)) == (0.0, 0.0, 0.0)
    m = g.align_rows((0, 0, 0), (1, 0, 1), (0, 0, 1))  # a stepped link: x is made normal to z
    assert _apply(m, (1, 0, 0)) == (1.0, 0.0, 0.0)


def test_one_channel_table_maps_each_cores_headers_to_its_servos():
    # docs/build-notes.md (servo ports) and the designer's config JSON for Core 2
    assert g.CHANNELS == {
        "core1": {1: "l_lid", 2: "l_eye", 3: "r_lid", 4: "r_eye"},
        "core2": {1: "tilt", 2: "mouth", 3: "pan"},
    }
    assert set(g.SERVO_LABEL) == {s for ch in g.CHANNELS.values() for s in ch.values()}
    assert g.EYES_SERVOS == tuple(g.CHANNELS["core1"].values())


def test_receiver_shields_sit_on_the_base_standoff_tops_with_the_core_under_each():
    # base plate STL: the receiver standoffs top at z 16 (r 1.1 pins up to 18); the Core plugs in under the shield as in
    # the receiver STEP and Cansin's build (docs/build-photos/eyes-top.jpg, references build-photos/eyes-side)
    assert g.receiver_at(1) == (38.0, 52.0, 16.0) and g.receiver_at(2) == (38.0, 85.0, 16.0)
    m = g.align_rows(g.receiver_at(1), *g.RECEIVER_AXES)
    assert _apply(m, g.RECEIVER_STEP["xh_power"]) == (47.75, 52.0, 25.62)  # XH socket toward the plate's +x edge
    assert _apply(m, (0, -10.68, -13.39)) == (
        51.39,
        52.0,
        5.32,
    )  # Core USB-C: under the shield, +x, 2.3 above the plate


def test_one_pack_and_one_switch_board_feed_both_shields_as_the_pan_tilt_guide_builds_it():
    # pan-tilt guide p.10 (Y adapter from a single battery) and p.23 (one pack, one switch board, two shields)
    assert not hasattr(g, "BATTERY_STACK_Z") and not hasattr(g, "CORE_FLIP")  # no pack 2; the Core is not flipped
    # pack in the box's pocket (STL x -50..-21.5, y 73..125, floor z 3), its lead at the front end (both photos)
    m = g.align_rows(*g.battery_at())
    assert _apply(m, (0, 0, g.BATTERY_STEP["floor_z"])) == (-35.75, 125.0, 3.0)
    assert _apply(m, g.BATTERY_STEP["plug"]) == (-39.25, 72.5, 14.65)
    # the cable holder of the eyes build on the two posts between the shields and the pack (Cansin's build, guide p.23)
    assert g.STANDOFFS["pt_base"]["cable_holder"] == [(6.0, 68.5, 13.0), (6.0, 92.5, 13.0)]
    m = g.align_rows(*g.CABLE_HOLDER_AT, **g.CABLE_HOLDER_FROM)  # the wire keeper STL (eyes frame) onto those posts
    assert _apply(m, (29.5, -22.6, 51.0)) == (6.0, 68.5, 13.0) and _apply(m, (29.5, -22.6, 75.0)) == (6.0, 92.5, 13.0)
    assert _apply(m, (29.5, -19.6, 51.0))[2] == 16.0  # 3 mm thick, lying on the post tops


def test_switch_board_1_lies_in_the_two_clip_holder_at_the_base_back_edge():
    # base plate STL (docs/research/2026-10-31-shafts.md): post (34.5, 108.5) and both clip shelves top z 9, clip walls'
    # inner faces x 18 / 51, back wall y 126; eyes guide p.13, pan-tilt guide p.23
    m = g.align_rows(*g.switch_at(), g.SWITCH_STEP["hole"])
    assert _apply(m, g.SWITCH_STEP["hole"]) == (34.5, 108.5, 9.0)
    pcb = [_apply(m, (x, 0, z)) for x in (-7.25, 13.25) for z in (-16, 16)]  # the PCB bottom's corners
    xs, ys, zs = zip(*pcb)
    assert (min(xs), max(xs), min(ys), max(ys), set(zs)) == (18.5, 50.5, 105.5, 126.0, {9.0})
    assert _apply(m, (0, 1, 0))[2] == 10.0  # parts up; the slide switch's underside drops between the shelves
    # switch STEP lever tip (-1.76, 15.16, 0): at the back-edge end above the back wall (top z 11), reachable from behind
    # (Cansin's build, docs/build-photos/eyes-top.jpg)
    assert _apply(m, (-1.76, 15.16, 0)) == (34.5, 120.51, 24.16)
    # the XH sockets at the PCB ends: the pack's lead in at the -x end, the Y lead out at the +x end (the build photo)
    assert _apply(m, g.SWITCH_STEP["in"]) == (19.0, 119.5, 13.5) and _apply(m, g.SWITCH_STEP["out"]) == (
        50.0,
        119.5,
        13.5,
    )


def test_sub_assembly_parts_tables_name_printed_parts():
    stems = {k.split(" (")[0] for k in g.PRINTED}
    for table in (g.EYES_PARTS, g.STACK_PARTS, g.MOUTH_PARTS):
        assert {row[1] for row in table} <= stems
    assert ("tilt arm", "tilt arm", (0, 0, g.TILT_ARM_SHIFT_Z)) in g.STACK_PARTS


def test_every_eye_mech_horn_pins_its_bar_at_the_second_hole_from_the_end_and_the_lid_horns_are_drilled_out():
    # STEP half arm: holes every 2 mm to 14.75, the arm ending at 16.05; eyes guide p.15 step 5 (2 mm drill, 2 horns) and
    # Cansin's build (the lid horns drilled, the eye horns not)
    assert g.HORN_STEP["pin"] == 12.75 and g.HORN_STEP["pin_r"] == {"lid": 1.0, "eye": 0.5}
