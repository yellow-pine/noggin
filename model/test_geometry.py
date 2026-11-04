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
        "core1": {1: "l_lid", 2: "yaw", 3: "r_lid", 4: "pitch"},
        "core2": {1: "tilt", 2: "mouth", 3: "pan"},
    }
    assert set(g.SERVO_LABEL) == {s for ch in g.CHANNELS.values() for s in ch.values()}


def test_the_horn_seats_on_the_spline_and_pins_its_bar_at_the_second_hole_from_the_end():
    # STEP half arm: holes every 2 mm to 14.75, the arm ending at 16.05; the spline tip on the bore bottom: STEP
    # z -12.17, tab plane z -0.65
    assert g.HORN_STEP["pin"] == 12.75 and g.SERVO_STEP["horn_seat"] == 11.52


DEFAULT_BUILD = {
    "Skeleton shape": "mechanical",
    "Skeleton palette": "black",
    "Skin shape": "cansin",
    "Skin palette": "default",
}
MORTY = {
    "Skeleton shape": "realistic",
    "Skeleton palette": "anatomical",
    "Skin shape": "morty",
    "Skin palette": "morty",
}


def test_a_theme_is_four_axes_and_each_preset_names_one_the_default_build_first():
    """#819: a Shape and a Palette per category; the Presets in order, Default build first, the default."""
    assert {a: list(v) for a, v in g.THEMES.items()} == {
        "Skeleton shape": ["realistic", "mechanical"],
        "Skeleton palette": ["anatomical", "robot", "black"],
        "Skin shape": ["none", "morty", "bart", "cansin"],  # none: the Skeleton bare (#876)
        "Skin palette": ["morty", "bart", "default"],
    }
    assert list(g.PRESETS) == ["Default build", "Morty", "Bart"]
    assert g.PRESETS["Default build"] == g.THEME == DEFAULT_BUILD and g.PRESETS["Morty"] == MORTY
    assert g.PRESETS["Bart"] == MORTY | {"Skin shape": "bart", "Skin palette": "bart"}
    assert [g.slug(p) for p in g.PRESETS] == ["default-build", "morty", "bart"]


def test_a_document_is_drawn_in_its_skeleton_shape_in_the_first_preset_of_that_shape():
    """#805, #819: a -mechanical document's Skeleton shape is mechanical, else realistic, each Stage in both; its
    colours the first Preset's in its Shape (the GLBs', which the viewer repaints)."""
    assert g.theme("stage1") == MORTY
    assert g.theme("mech-back-mechanical") == DEFAULT_BUILD
    assert {"stage1", "stage1-mechanical", "mech-back-mechanical"} <= set(g.STAGES)


def test_each_colour_group_is_printed_in_its_palettes_filament():
    """#805, #819: a Colour group's filament in a Theme's Palette, its hex the slicer's; every Palette of a category
    paints its every Colour group, in at most four filaments."""
    assert g.filament("Bones", MORTY) == ("PETG Basic", "Dark Beige", "30403", "#DBC8B6")
    # Cansin, 2026-11-03: the red lids read badly, then the dark brown; pink, matte
    assert g.filament("Linkages", MORTY) == ("PETG Matte", "Pink", "35700", "#FABBCB")
    assert g.filament("Bones", MORTY | {"Skeleton palette": "robot"}) == ("PETG Matte", "Gray", "35102", "#7F7E83")
    assert g.filament("Joints", DEFAULT_BUILD) == ("PETG Basic", "Black", "30105", "#000000")
    assert g.filament("eye whites", MORTY) == ("PLA Basic", "Jade White", "10100", "#FFFFFF")
    assert g.filament("pupils", g.PRESETS["Bart"]) == ("PLA Matte", "Charcoal", "11101", "#000000")
    assert g.filament("face", DEFAULT_BUILD) == ("PLA Pure", "Milky Pink", "17200", "#F7CED7")
    assert g.filament("accessories", DEFAULT_BUILD) == ("PLA Pure", "Apricot", "17300", "#FFB673")
    assert g.filament("clothes", DEFAULT_BUILD) == g.filament("eye whites", DEFAULT_BUILD)
    for axis in ("Skeleton palette", "Skin palette"):
        palettes = g.THEMES[axis].values()
        assert len({tuple(p) for p in palettes}) == 1  # one set of Colour groups
        assert all(len(set(p.values())) <= 4 for p in palettes)
    assert all(g.filament(group, t) for t in g.PRESETS.values() for group, _ in g.PRINTED.values())
