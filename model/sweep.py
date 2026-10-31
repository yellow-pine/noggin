"""Mac-side driver for the horn sweep (`DOC=noggin-pan-tilt|noggin-mouth make model-check`, default noggin-eyes): one Fusion call
per horn so the UI breathes between calls and a crash loses one horn, then the per-horn reports are merged into
model/build/<doc>-report.json. Usage: sweep.py [doc] [--merge-only]"""
import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))


def merge(parts):
    """One report from per-horn reports: horns and violations accumulate, the rest comes from the first part."""
    report = dict(parts[0], horns={}, violations=[], interference=[], contacts=[], calibrated={})
    for p in parts:
        report["horns"].update(p["horns"])
        report["calibrated"].update(p.get("calibrated", {}))
        for key in ("violations", "interference", "contacts"):
            report[key] += p.get(key, [])
    # Hits at the calibrated servo ends (eyes/calibration.json, past the designer's limits) go under calibrated[horn]
    for key in ("violations", "contacts"):
        for hit in [h for h in report[key] if h.get("calibrated")]:
            report[key].remove(hit)
            report["calibrated"].setdefault(hit["horn"], {}).setdefault(key, []).append({"deg": hit["deg"], "pair": hit["pair"]})
            report["interference"] = [i for i in report["interference"] if i["pose"] != f"{hit['horn']} {hit['deg']}"]
    return report


def main():
    import fusion_run
    import beams, fits, sim   # model/ siblings (sys.path[0] is this folder when run as a script)
    TABLES = {"noggin-eyes": (fits.EYES_JOINTS, beams.EYES_BEAMS), "noggin-pan-tilt": (fits.PT_JOINTS, beams.PT_BEAMS),
              "noggin-mouth": (fits.MOUTH_JOINTS, beams.MOUTH_BEAMS)}
    check = open(os.path.join(HERE, "check.py")).read()
    doc = next((a for a in sys.argv[1:] if not a.startswith("--")), "noggin-eyes")
    check = check.replace('DOC = "noggin-eyes"', f'DOC = "{doc}"')
    out = os.path.join(HERE, "build")
    if "--merge-only" not in sys.argv:   # re-threshold the last sweep without Fusion
        for f in glob.glob(os.path.join(out, f"{doc}-*.json")):
            os.remove(f)
        horns = json.loads(fusion_run.run_script(check.replace("HORN = None", 'HORN = "?"'))["message"])
        for horn in horns:
            print(fusion_run.run_script(check.replace("HORN = None", f"HORN = {horn!r}"))["message"], end="")
    parts = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(out, f"{doc}-*.json"))) if not f.endswith("-report.json")]
    joints, links = TABLES[doc]
    report = sim.enrich(merge(parts), fits.fit_table(joints), beams.beam_table(links))
    with open(os.path.join(out, f"{doc}-report.json"), "w") as f:
        json.dump(report, f, indent=1)


if __name__ == "__main__":
    main()
