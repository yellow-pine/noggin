"""`just live-check` (#29) against a fake Mech: what the noggin CLI and just answer, and the noggin.log they write."""

from noggin.live_check import run, write

SERVICE = "noggin service 0.3.0 abc1234"


class Mech:
    """Two Cores, a cable and a switch: answers the commands the live check runs, as the Mac would."""

    def __init__(self, log, deaf=()):
        self.log, self.deaf = log, set(deaf)  # a deaf Core never beacons
        self.on, self.flashed, self.t, self.prompts = True, set(), 0.0, []

    def sh(self, cmd):
        if cmd == "just flash-usb":
            self.flashed.add(self.plugged)
            return 0, "Core reset\n"
        if cmd == "noggin/noggin status":
            lines = [self.link(c) for c in ("eyes", "neck")]
            return 0, "\n".join(lines) + f"\n{SERVICE}\nmode follow\n"
        if cmd.startswith("noggin/noggin flash "):
            core = cmd.split()[-1]
            if core in self.deaf:
                return 1, f"flash failed: no beacon from {core} in 22.0 s (switched off? just flash-usb)\n"
            return 0, f"flashed {core}: eyes.mpy stamp.mpy, uptime 2s\n"
        if cmd == "noggin/noggin wink 3":
            with self.log.open("a") as f:
                for core in ("eyes", "neck"):
                    sent = f"sent {core} ['wink 3']" if core not in self.deaf else f"no Link, dropped {core} ['wink 3']"
                    f.write(f"12:00:00 {sent}\n")
            return 0, ""
        assert cmd == "just start", cmd
        return 0, ""

    def link(self, core):
        if not self.on or core in self.deaf or core not in self.flashed:
            return f"{core} offline"
        return f"{core} wifi 10.0.0.{len(core)} uptime 5s program 0.3.0 abc1234"

    def ask(self, prompt):
        self.prompts.append(prompt)
        if "cable" in prompt and "Plug" in prompt:
            self.plugged = prompt.split()[2]  # "Plug the <core> Core's ..."
        if "off" in prompt and "Switch" in prompt:
            self.on = False
        elif "Switch" in prompt:
            self.on = True

    def clock(self):
        return self.t

    def wait(self, s):
        self.t += s


def check(tmp_path, **kw):
    log = tmp_path / "noggin.log"
    log.write_text("11:59:59 listening\n")
    mech = Mech(log, **kw)
    return mech, run(mech.sh, mech.ask, log, mech.clock, mech.wait)


def test_both_cores_pass_every_step_and_the_human_is_asked_only_for_the_cable_and_the_switch(tmp_path):
    mech, rows = check(tmp_path)
    assert [(step, core, result) for step, core, result, _ in rows] == [
        ("USB flash", "eyes", "ok"),
        ("USB flash", "neck", "ok"),
        ("Wi-Fi flash", "eyes", "ok"),
        ("Wi-Fi flash", "neck", "ok"),
        ("Wi-Fi, cable in", "eyes", "ok"),
        ("Wi-Fi, cable in", "neck", "ok"),
        ("Wi-Fi, cable out", "eyes", "ok"),
        ("Wi-Fi, cable out", "neck", "ok"),
        ("Mech off", "eyes", "ok"),
        ("Mech off", "neck", "ok"),
        ("Mech back on", "eyes", "ok"),
        ("Mech back on", "neck", "ok"),
    ]
    assert rows[4][3] == "wifi 10.0.0.4 uptime 5s program 0.3.0 abc1234; wink 3 acked"
    assert [p.split(".")[0] for p in mech.prompts] == [
        "Plug the eyes Core's cable into the Mac, every other cable out",
        "Plug the neck Core's cable into the Mac, every other cable out",
        "Unplug every cable from the Mech",
        "Switch the Mech off",
        "Switch the Mech on",
    ]


def test_a_core_that_never_beacons_fails_its_steps_and_the_rest_still_runs(tmp_path):
    _, rows = check(tmp_path, deaf={"neck"})
    neck = {step: (result, detail) for step, core, result, detail in rows if core == "neck"}
    eyes = {step: result for step, core, result, _ in rows if core == "eyes"}
    assert set(eyes.values()) == {"ok"}
    assert neck["USB flash"] == ("FAIL", "offline 90 s after the flash")
    assert neck["Wi-Fi flash"] == ("FAIL", "flash failed: no beacon from neck in 22.0 s (switched off? just flash-usb)")
    assert neck["Wi-Fi, cable out"] == ("FAIL", "offline; no Link, dropped neck ['wink 3']")
    assert neck["Mech off"][0] == "ok"  # offline, as it should be with the Mech off
    assert neck["Mech back on"] == ("FAIL", "offline 90 s after the switch; no Link, dropped neck ['wink 3']")


def test_the_results_are_appended_to_the_page_as_a_dated_table(tmp_path):
    page = tmp_path / "live-check.md"
    page.write_text("# Live check\n")
    write([("USB flash", "eyes", "ok", "wifi a|b")], page, "2026-11-03, noggin service 0.3.0 abc1234")
    assert page.read_text() == (
        "# Live check\n\n## 2026-11-03, noggin service 0.3.0 abc1234\n\n"
        "| Step | Core | Result | Detail |\n| --- | --- | --- | --- |\n| USB flash | eyes | ok | wifi a\\|b |\n"
    )
