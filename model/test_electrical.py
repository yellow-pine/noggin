"""Seam: model/electrical.py, the SPICE circuit of the Mech's supply (PySpice on ngspice): its operating point on a
hand-checkable circuit, worst_case() (the entry the Mech-wide report merges) and leads() (what model/cables.py
routes)."""

from PySpice.Spice.Netlist import Circuit

from model import electrical


def test_one_resistor_and_one_load_obey_ohms_law():
    c = Circuit("ohm")
    c.V("pack", "a", c.gnd, 6)
    c.R("lead", "a", "b", 1)
    c.I("load", "b", c.gnd, 1)  # 1 A through 1 ohm: 1 V lost, 5 V left
    assert abs(electrical.operating_point(c)["b"] - 5.0) < 1e-9


W = electrical.worst_case()  # every servo at stall and both Cores in a Wi-Fi transmit burst, on one pack


def test_the_one_pack_feeds_both_shields_with_every_servo_at_stall_and_both_cores_bursting():
    for case in ("nominal", "cutoff"):
        # 7 servos at 650 mA stall + 2 x (shield standby 60 mA + an ESP32-C3 transmit burst 335 mA): 5.34 A on a 3 A pack
        assert abs(W[case]["pack_a"] - 5.34) < 1e-6
        assert abs(W[case]["shield_a"]["core1"] - (4 * 0.65 + 0.060 + 0.335)) < 1e-6
        assert abs(W[case]["shield_a"]["core2"] - (3 * 0.65 + 0.060 + 0.335)) < 1e-6
    assert W["cap_a"] == 3.0 and all(a < 3.0 for a in W["nominal"]["shield_a"].values())


def test_on_a_nominal_pack_every_servo_keeps_its_minimum_and_both_cores_their_3v3():
    nominal = W["nominal"]
    assert nominal["pack_v"] == 7.4 and W["servo_min_v"] == 4.8 and W["brownout_v"] == 2.51
    assert set(nominal["servo_v"]) == {"l_lid", "l_eye", "r_lid", "r_eye", "tilt", "mouth", "pan"}
    # the shield's 5 V rail holds; the servo lead's two 250 mm conductors (26 AWG, 0.134 ohm/m) drop 0.65 A x 0.067 ohm
    assert all(abs(v - 4.956) < 0.001 for v in nominal["servo_v"].values())
    assert all(abs(v - 3.3) < 1e-6 for v in nominal["core_v"].values())


def test_at_the_packs_cutoff_the_servos_sag_below_their_minimum_and_the_cores_stay_above_brownout():
    cutoff = W["cutoff"]
    assert cutoff["pack_v"] == 5.8  # the pack's over-discharge protection (its datasheet)
    assert all(v < W["servo_min_v"] for v in cutoff["servo_v"].values())  # "sluggish when the battery is low"
    assert all(v > W["brownout_v"] for v in cutoff["core_v"].values())


def test_leads_run_every_servo_to_its_header_and_the_one_pack_through_its_switch_and_a_y_lead_to_both_shields():
    assert electrical.CHANNELS["core1"] == {1: "l_lid", 2: "l_eye", 3: "r_lid", 4: "r_eye"}  # the build notes
    assert electrical.CHANNELS["core2"] == {1: "tilt", 2: "mouth", 3: "pan"}
    leads = {name: (a, b, mm) for name, a, b, mm in electrical.leads()}  # stages.py Port names
    assert len(leads) == 7 + 1 + 2
    assert leads["l_eye servo -> Core 1 PWM2"] == ("L eye servo lead", "Core 1 servo PWM2", 250)
    assert leads["pan servo -> Core 2 PWM3"][0] == "pan servo lead"
    assert leads["mouth servo -> Core 2 PWM2"][0] == "jaw servo lead"
    assert leads["pack 1 -> switch 1"] == ("battery 1 lead", "switch board 1 in", 100)
    # pan-tilt guide p.10: the Y adapter, one branch per shield from the switch board's output
    assert leads["switch 1 -> shield 1"] == ("switch board 1 out", "Core 1 XH power", 100)
    assert leads["switch 1 -> shield 2"] == ("switch board 1 out", "Core 2 XH power", 100)
