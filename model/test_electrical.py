"""Seam: electrical.budget(), the dict the Mech-wide report merges (channel map, current caps, stall worst case,
battery runtime per scenario)."""

import importlib.util
import os

spec = importlib.util.spec_from_file_location(
    "electrical", os.path.join(os.path.dirname(__file__), "electrical.py")
)  # by path: eyes/ owns `eyes`
electrical = importlib.util.module_from_spec(spec)
spec.loader.exec_module(electrical)
B = electrical.budget()


def test_channel_map_matches_the_build_notes():
    assert B["channels"]["core1"] == {1: "l_lid", 2: "l_eye", 3: "r_lid", 4: "r_eye"}
    assert B["channels"]["core2"] == {1: "tilt", 2: "mouth", 3: "pan"}


def test_all_servos_at_stall_stay_under_the_3a_cap_on_each_shield():
    assert B["cap_a"] == 3.0
    assert abs(B["stall_a"]["core1"] - 4 * 0.65) < 1e-9 and abs(B["stall_a"]["core2"] - 3 * 0.65) < 1e-9
    assert all(a < B["cap_a"] for a in B["stall_a"].values())


def test_runtime_orders_the_scenarios_and_uses_the_gesture_durations():
    h = B["runtime_h"]["core1"]
    assert h["rest"] > h["session"] > h["demo"] > 1.0
    assert (
        abs(B["session_moving_s_per_hour"] - (20 * 2.120 + 10 * 5.295)) < 0.01
    )  # eureka 2, attention 1 (eyes/replay.py)
    assert B["pack"] == {"mah": 800, "cutoff_v": 5.8}


def test_runtime_includes_the_radio_draw():
    assert B["wifi_a"] == 0.100
    h = {core: {k: round(v, 2) for k, v in hours.items()} for core, hours in B["runtime_h"].items()}
    assert h == {
        "core1": {"rest": 2.76, "session": 2.70, "demo": 1.61},
        "core2": {"rest": 3.10, "session": 3.10, "demo": 1.93},
    }
