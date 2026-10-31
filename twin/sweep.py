"""Mac-side driver for the horn sweep (`make twin-check`): one Fusion call per horn so the UI breathes between
calls and a crash loses one horn, then the per-horn reports are merged into twin/build/<doc>-report.json."""
import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))


def merge(parts):
    """One report from per-horn reports: horns and violations accumulate, the rest comes from the first part."""
    report = dict(parts[0], horns={}, violations=[], interference=[], contacts=[])
    for p in parts:
        report["horns"].update(p["horns"])
        for key in ("violations", "interference", "contacts"):
            report[key] += p.get(key, [])
    return report


def main():
    import fusion_run
    check = open(os.path.join(HERE, "check.py")).read()
    doc = check.split('DOC = "')[1].split('"')[0]
    out = os.path.join(HERE, "build")
    for f in glob.glob(os.path.join(out, f"{doc}-*.json")):
        os.remove(f)
    horns = json.loads(fusion_run.run_script(check.replace("HORN = None", 'HORN = "?"'))["message"])
    for horn in horns:
        print(fusion_run.run_script(check.replace("HORN = None", f"HORN = {horn!r}"))["message"], end="")
    parts = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(out, f"{doc}-*.json"))) if not f.endswith("-report.json")]
    with open(os.path.join(out, f"{doc}-report.json"), "w") as f:
        json.dump(merge(parts), f, indent=1)


if __name__ == "__main__":
    main()
