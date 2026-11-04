"""Seam: model/electrical.py, the SPICE circuit of the Mech's supply (ngspice through spicelib): its operating point on a
hand-checkable circuit, the pack by its charge (pack_ohm(), pack_ocv()) and when its protector cuts (cuts()),
worst_case() (the entry the Mech-wide report merges)."""

import pytest

from model import electrical


def test_the_standard_tilt_servo_reaches_the_actual_five_volt_supply_loads():
    """#902: the larger tilt's published 1.4 A must not inherit the owned micro servo's 0.65 A."""
    loads = {
        line.split()[0]: float(line.split()[-1]) for line in electrical.mech(0.5).splitlines() if line.startswith("I")
    }
    assert loads["Itilt"] == pytest.approx(1.4)
    assert loads["Iyaw"] == pytest.approx(0.5666666667)  # owned micro's 0.55..0.65 A interpolated at the regulated 5 V


def test_one_resistor_and_one_load_obey_ohms_law():
    c = "* ohm\nVpack a 0 6\nRlead a b 1\nIload b 0 1"  # 1 A through 1 ohm: 1 V lost, 5 V left
    assert abs(electrical.operating_point(c)["b"] - 5.0) < 1e-9


def test_the_packs_resistance_is_flat_above_a_fifth_of_its_charge_and_rises_steeply_to_half_an_ohm_at_empty():
    # Chen & Rincon-Mora 2006 eq. 3 per cell (75 mohm from mid charge, 231 at empty), two in series plus the 40 mohm
    # protection MOSFETs: 0.19 ohm flat, about 0.50 at empty (docs/research/2026-11-02-literature-electrical.md 1)
    assert all(abs(electrical.pack_ohm(soc) - 0.189) < 0.001 for soc in (0.3, 0.5, 1.0))
    assert abs(electrical.pack_ohm(0.2) - 0.192) < 0.001  # within 2 % of flat
    assert electrical.pack_ohm(0.1) > electrical.pack_ohm(0.2) + 0.015
    assert abs(electrical.pack_ohm(0.0) - 0.501) < 0.001


def test_the_protector_cuts_on_the_cells_loaded_voltage_held_under_5v8_past_its_delay_not_on_the_resting_voltage():
    # the resting voltage, Chen eq. 2 per cell: 3.67 V at 10 % (the note's "about 3.68"), 3.52 V at 5 % (the note 1)
    assert round(electrical.pack_ocv(0.10) / 2, 2) == 3.67 and round(electrical.pack_ocv(0.05) / 2, 2) == 3.52
    # at 5 % the pack rests at 7.03 V, far above 5.8 V, yet 5.34 A (the worst case) pulls its cells to 5.74 V: a cut
    # once held past the protector's shortest delay, 20 ms less its 20 % tolerance (the BQ2970 datasheet)
    assert electrical.cuts(0.05, 5.34, 20) and not electrical.cuts(0.05, 5.34, 15)
    assert not electrical.cuts(0.05, 1.0, 1000)  # one servo's start
    assert not electrical.cuts(0.5, 5.34, 1000)  # mid charge: 6.81 V under the worst case


W = electrical.worst_case()  # every servo at stall and both Cores in a Wi-Fi transmit burst, on one pack


def test_the_one_pack_feeds_both_shields_with_every_servo_at_stall_and_both_cores_bursting():
    for case in ("nominal", "cutoff"):
        # Six micro servos at 5 V (0.5667 A) plus the standard's full published 1.4 A and both Cores: 5.59 A.
        assert W[case]["pack_a"] == pytest.approx(5.59)
        assert W[case]["shield_a"]["core1"] == pytest.approx(2.662)
        assert W[case]["shield_a"]["core2"] == pytest.approx(2.928)
    assert W["cap_a"] == 3.0 and all(a < 3.0 for a in W["nominal"]["shield_a"].values())


def test_the_nominal_simultaneous_stall_reports_the_standard_leads_drop_and_keeps_both_cores_at_3v3():
    nominal = W["nominal"]
    assert nominal["pack_v"] == 7.4 and W["servo_min_v"] == 4.8 and W["brownout_v"] == 2.51
    assert set(nominal["servo_v"]) == {"l_lid", "yaw", "r_lid", "pitch", "tilt", "mouth", "pan"}
    assert all(abs(nominal["servo_v"][n] - 4.882) < 0.001 for n in ("l_lid", "yaw", "r_lid", "pitch"))
    assert all(abs(nominal["servo_v"][n] - 4.874) < 0.001 for n in ("mouth", "pan"))
    # The actual 320 mm standard lead drops 1.4 A x 0.08576 ohm. This deliberately exposes an unsafe all-stall
    # condition (also 5.59 A on a 3 A pack); test_report's existing minimum-voltage gate must still reject it.
    assert nominal["servo_v"]["tilt"] == pytest.approx(4.792)
    assert nominal["servo_v"]["tilt"] < W["servos"]["tilt"]["min_v"]
    assert all(abs(v - 3.3) < 1e-6 for v in nominal["core_v"].values())


def test_the_worst_case_cuts_the_pack_while_it_still_rests_far_above_its_cutoff():
    cutoff = W["cutoff"]
    # the protector trips once the worst case pulls the cells to 5.8 V (its datasheet): at about 5 % charge, resting
    # at 7.0-7.1 V, where the pack's resistance has risen to about 0.27 ohm
    assert cutoff["cells_v"] == 5.8 and W["cutoff_delay_ms"] == 16
    assert 0.05 < cutoff["soc"] < 0.06 and 7.0 < cutoff["pack_v"] < 7.1 and abs(cutoff["pack_ohm"] - 0.27) < 0.01
    # a pack resting at its nominal 7.4 V is at 13 % on Chen's curve, just inside the knee: 0.203 ohm, not 0.189
    nominal = W["nominal"]
    assert nominal["pack_v"] == 7.4 and abs(nominal["soc"] - 0.13) < 0.005 and abs(nominal["pack_ohm"] - 0.203) < 0.001


def test_at_the_cut_the_servos_sag_below_their_minimum_and_the_cores_keep_their_3v3():
    cutoff = W["cutoff"]
    assert all(v < W["servo_min_v"] for v in cutoff["servo_v"].values())  # "sluggish when the battery is low"
    assert all(abs(v - 3.3) < 1e-6 for v in cutoff["core_v"].values())  # the pack cuts before a Core browns out
    # 5.8 V less 5.59 A through the MOSFETs, the pack lead, the power-path board's battery FET, the switch and the neck
    # cable's 250 mm of 24 AWG up the post (#858), the shield's branch, the rail's 0.5 V dropout and the servo lead:
    # Core 1's shield (4 servos) sags further than Core 2's (3)
    assert all(abs(cutoff["servo_v"][n] - 4.191) < 0.001 for n in ("l_lid", "yaw", "r_lid", "pitch"))
    assert all(abs(cutoff["servo_v"][n] - 4.184) < 0.001 for n in ("mouth", "pan"))
    assert cutoff["servo_v"]["tilt"] == pytest.approx(4.101)
