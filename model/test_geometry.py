"""Seam: model/geometry.py public data and functions. Expected values are literals from docs/research/2026-10-31-model.md
and docs/research/2026-10-31-shafts.md (servo shafts, horn seat)."""

from model import geometry as g


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
    # docs/build/wiring.md (servo ports) and the designer's config JSON for Core 2
    assert g.CHANNELS == {
        "core1": {1: "l_lid", 2: "l_eye", 3: "r_lid", 4: "r_eye"},
        "core2": {1: "tilt", 2: "mouth", 3: "pan"},
    }
    assert set(g.SERVO_LABEL) == {s for ch in g.CHANNELS.values() for s in ch.values()}


def test_the_horn_seats_on_the_spline_and_pins_its_bar_at_the_second_hole_from_the_end():
    # STEP half arm: holes every 2 mm to 14.75, the arm ending at 16.05; the spline tip on the bore bottom: STEP
    # z -12.17, tab plane z -0.65
    assert g.HORN_STEP["pin"] == 12.75 and g.SERVO_STEP["horn_seat"] == 11.52


def test_a_document_is_drawn_in_its_skeleton_and_the_default_skin():
    """#805: realistic and morty by default; a -mechanical document's Skeleton is mechanical, each Stage in both."""
    assert g.theme("next-stage1") == {"Skeleton": "realistic", "Skin": "morty"}
    assert g.theme("next-mech-back-mechanical") == {"Skeleton": "mechanical", "Skin": "morty"}
    assert {"next-stage1", "next-stage1-mechanical", "next-mech-back-mechanical"} <= set(g.STAGES)


def test_each_colour_group_is_printed_in_its_themes_filament():
    """#805: a Colour group's filament in a Theme, its hex the slicer's; at most four groups per value."""
    realistic, mechanical = g.theme("next-stage1"), g.theme("next-stage1-mechanical")
    assert g.filament("Bones", realistic) == ("PETG Basic", "Dark Beige", "30403", "#DBC8B6")
    assert g.filament("Bones", mechanical) == ("PETG Matte", "Gray", "35102", "#7F7E83")
    assert g.filament("eye whites", realistic) == ("PLA Basic", "Jade White", "10100", "#FFFFFF")
    assert g.filament("pupils", realistic | {"Skin": "bart"}) == ("PLA Matte", "Charcoal", "11101", "#000000")
    assert all(len(groups) <= 4 for values in g.THEMES.values() for groups in values.values())
    assert all(g.filament(group, realistic) for group, _ in g.PRINTED.values())  # every part's, by default
