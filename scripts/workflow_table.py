"""The CI/CD table, derived from .github/workflows (#397, docs/adr/0011): each workflow's name, file, triggers (with
their branches, tags, paths, workflows or crons) and jobs, and its purpose: the first line of the header comment right
under its `name:`, a trailing period dropped (#422). macros.py hands it to the site's CI/CD page, docs/ci-cd.md
(#425, docs/adr/0009)."""

import re
from pathlib import Path

import yaml

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"


def code(values):
    return ", ".join(f"`{v}`" for v in values)


def trigger(event, spec):
    """`push` (`main`; paths: `ci/*.Dockerfile`): the branches and tags bare, every other filter but types by name;
    each value in code, so GitHub reads no `*` as emphasis."""
    if event == "schedule":
        return f"`{event}` ({code(s['cron'] for s in spec)})"
    spec = spec or {}
    filters = [code(v) if k in ("branches", "tags") else f"{k}: {code(v)}" for k, v in spec.items() if k != "types"]
    return f"`{event}`" + (f" ({'; '.join(filters)})" if filters else "")


def row(path):
    text = path.read_text()
    # a regex: PyYAML drops comments (ruamel.yaml keeps them, a new dependency for this one line)
    purpose = re.match(r"name: .*\n# (.+?)\.?\n", text)
    if not purpose:
        raise ValueError(f"{path.name}: no header comment under `name:`, whose first line is its purpose")
    flow = yaml.safe_load(text)
    on = flow[True]  # YAML 1.1 reads the `on` key as true
    on = on if isinstance(on, dict) else dict.fromkeys([on] if isinstance(on, str) else on)  # `on: x`, `on: [x, y]`
    jobs = dict.fromkeys(re.sub(r" \(\$\{\{.*\}\}\)$", "", j["name"]) for j in flow["jobs"].values())  # matrix suffix
    triggers = ", ".join(trigger(e, s) for e, s in on.items())
    return f"| {flow['name']} | `{path.name}` | {triggers} | {', '.join(jobs)} | {purpose[1]} |"


def table(workflows=WORKFLOWS):
    rows = [row(p) for p in sorted(workflows.glob("*.yml"))]
    return "\n".join(["| Workflow | File | Triggers | Jobs | Does |", "|---|---|---|---|---|", *rows])
