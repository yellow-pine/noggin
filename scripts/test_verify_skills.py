"""verify_skills.mjs: restored skills in .agents/skills must match computedHash in skills-lock.json."""

import json
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).with_name("verify_skills.mjs")
SKILL = "---\nname: demo\ndescription: a demo skill\n---\nhello\n"
# what skills@1.7.4 `add` wrote to skills-lock.json for this folder (its localeCompare puts references/ before SKILL.md)
DEMO_HASH = "780fd6aa5931bc22b4e20114021c6c2549e22681ba281b0916b8e5094b60e392"


def project(tmp_path: Path, hashes: dict[str, str]) -> Path:
    skills = {name: {"source": "x/y", "sourceType": "github", "computedHash": h} for name, h in hashes.items()}
    (tmp_path / "skills-lock.json").write_text(json.dumps({"version": 1, "skills": skills}))
    demo = tmp_path / ".agents/skills/demo"
    (demo / "references").mkdir(parents=True)
    (demo / "SKILL.md").write_text(SKILL)
    (demo / "references/a.md").write_text("ref\n")
    return tmp_path


def verify(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["node", SCRIPT], cwd=cwd, capture_output=True, text=True)


def test_restored_skills_that_match_the_lock_pass(tmp_path):
    assert verify(project(tmp_path, {"demo": DEMO_HASH})).returncode == 0


def test_a_changed_file_fails_and_names_the_skill(tmp_path):
    cwd = project(tmp_path, {"demo": DEMO_HASH})
    (cwd / ".agents/skills/demo/references/a.md").write_text("tampered\n")
    out = verify(cwd)
    assert out.returncode != 0
    assert "demo" in out.stderr


def test_a_skill_that_was_not_restored_fails(tmp_path):
    out = verify(project(tmp_path, {"demo": DEMO_HASH, "missing": DEMO_HASH}))
    assert out.returncode != 0
    assert "missing" in out.stderr
