"""Seams: servo_take.angles (a filmed clip -> the marker's angle at each frame) and servo_take.take (those angles -> the
take servo_fit reads, on the Core's clock by the take's opening ramp, #644)."""

import re

import cv2
import numpy as np
import pytest

from model import mjcf, servo_fit, servo_take

FPS = 240


def test_angles_reads_the_marker_turning_about_a_shaft_off_its_centre_at_each_frame(tmp_path):
    """A synthetic clip: the printed marker, 120 px across (12 mm at the phone's 10 px a mm), turned counter-clockwise
    (as seen) about a point beside it, 0 to 60 degrees and back past -40; angles reads each frame's time and the
    marker's angle within a quarter degree."""
    side, truth = 360, np.concatenate([np.linspace(0, 60, 30), np.linspace(60, -45, 30)])
    page = np.full((side, side), 255, np.uint8)
    page[60:180, 120:240] = cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(servo_take.MARKER), 0, 120)
    path = str(tmp_path / "clip.avi")
    video = cv2.VideoWriter(path, cv2.VideoWriter.fourcc(*"MJPG"), FPS, (side, side))
    for deg in truth:
        turn = cv2.getRotationMatrix2D((180, 200), deg, 1)
        video.write(cv2.cvtColor(cv2.warpAffine(page, turn, (side, side), borderValue=255), cv2.COLOR_GRAY2BGR))
    video.release()
    t, deg = servo_take.angles(path)
    assert t == pytest.approx(np.arange(len(truth)) / FPS, abs=1e-6)
    assert deg - deg[0] == pytest.approx(truth, abs=0.25)


def test_a_servos_takes_share_one_clock_whose_offset_the_fitted_delay_takes_in():
    """One servo off the sheet's values filmed through the Core's `take`, bare and with 85 g at 50 mm, each clip
    running 0.4 s before it and its marker turning against the command, its zero 37 degrees off: take puts both on one
    clock, a few ms off the Core's (the ramp's lag differs with the servo's values, not its load), so the rig played
    with the true values and that much less delay follows each filmed horn within half a degree (a millisecond more
    misses by 0.4 degrees on the steps)."""
    true = {**mjcf.SERVO, "stall_nm": 0.08, "no_load_rad_s": 6.0, "armature": 1.5e-4}
    writes = servo_take.commands()
    end = writes[-1][0] + 1
    takes = []
    for load_g in (0, 85):
        fine = {"load_g": load_g, "arm_mm": 50, "t_s": np.arange(0, end, 0.0005).tolist(), "command": writes}
        t, horn = servo_fit.play(true, fine)
        clip = np.arange(-0.4, end, 1 / FPS)
        takes.append(servo_take.take(clip + 0.4, 37 - np.interp(clip, t, horn), load_g, 50))
    late = [got["command"][1][0] - 0.4 for got in takes]  # the Core's first write against the clip's
    assert abs(late[0] - late[1]) < 0.001 and abs(late[0]) < 0.005, late
    for got, load_g in zip(takes, (0, 85)):
        assert (got["load_g"], got["arm_mm"], got["command"][0]) == (load_g, 50, [got["t_s"][0], 0])
        played = servo_fit.play({**true, "delay_s": true["delay_s"] - np.mean(late)}, got)[1]
        assert np.abs(played - got["horn_deg"]).max() < 0.5


def test_the_marker_to_print_reads_as_marker_0_at_12_mm():
    """The SVG's black cells drawn back into a picture at 5 px a mm, on its white margin, read as marker 0."""
    svg = servo_take.svg()
    assert 'width="16mm"' in svg  # 12 mm and a 2 mm cell of white each side
    page = np.full((80, 80), 255, np.uint8)
    for x, y in re.findall(r'<rect x="([\d.]+)" y="([\d.]+)" width="2" height="2"/>', svg):
        row, col = round((float(y) + 2) * 5), round((float(x) + 2) * 5)
        page[row : row + 10, col : col + 10] = 0
    _, ids, _ = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(servo_take.MARKER)).detectMarkers(page)
    assert ids is not None and ids.flatten().tolist() == [0]


def test_take_refuses_a_clip_without_the_ramp():
    """A clip of the horn standing still at rest: no ramp to line the Core's writes up by, so no take."""
    t = np.arange(0, 2, 1 / FPS)
    with pytest.raises(AssertionError, match="ramp"):
        servo_take.take(t, np.zeros_like(t), 0, 0)
