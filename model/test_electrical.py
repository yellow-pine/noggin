"""Seam: electrical.budget(), the dict the Mech-wide report merges (channel map, current caps, stall worst case,
battery runtime per scenario)."""

from model import electrical

B = electrical.budget()


def test_channel_map_matches_the_build_notes():
    assert B["channels"]["core1"] == {1: "l_lid", 2: "l_eye", 3: "r_lid", 4: "r_eye"}
    assert B["channels"]["core2"] == {1: "tilt", 2: "mouth", 3: "pan"}


def test_all_servos_at_stall_with_the_shield_and_a_wifi_burst_stay_under_the_3a_cap_on_each_shield():
    assert B["cap_a"] == 3.0
    # servos at stall + shield standby 60 mA + an ESP32-C3 Wi-Fi transmit burst 335 mA
    assert abs(B["stall_a"]["core1"] - (4 * 0.65 + 0.060 + 0.335)) < 1e-9
    assert abs(B["stall_a"]["core2"] - (3 * 0.65 + 0.060 + 0.335)) < 1e-9
    assert all(a < B["cap_a"] for a in B["stall_a"].values())


def test_both_cores_listen_on_wifi_in_every_scenario():
    hold = B["hold_a_per_servo"]
    assert abs(B["draw_a"]["core2"]["rest"] - (0.060 + 3 * (0.008 + hold) + 0.084)) < 1e-9  # + Wi-Fi receive


def test_leads_run_every_servo_to_its_header_and_each_pack_through_its_switch_to_its_shield():
    leads = {name: (a, b, mm) for name, a, b, mm in electrical.leads()}  # Port names, as the Fusion builds name them
    assert len(leads) == 7 + 2 + 2
    assert leads["l_eye servo -> Core 1 PWM2"] == ("Core 1 servo PWM2", "L eye servo lead", 250)
    assert leads["pan servo -> Core 2 PWM3"][1] == "pan servo lead"
    assert leads["mouth servo -> Core 2 PWM2"][1] == "jaw servo lead"
    assert leads["pack 2 -> switch 2"] == ("battery 2 lead", "switch board 2 hole", 100)
    assert leads["switch 1 -> shield 1"][1:] == ("Core 1 XH power", 100)


def test_runtime_orders_the_scenarios_and_uses_the_gesture_durations():
    h = B["runtime_h"]["core1"]
    assert h["rest"] > h["session"] > h["demo"] > 1.0
    assert (
        abs(B["session_moving_s_per_hour"] - (20 * 2.120 + 10 * 5.295)) < 0.01
    )  # eureka 2, attention 1 (eyes/replay.py)
    assert B["pack"] == {"mah": 800, "cutoff_v": 5.8}
