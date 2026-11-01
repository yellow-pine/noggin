"""The CI base image (ci/base.Dockerfile) carries the mermaid-cli mkdocs.yml pins: a stale one would only make the
diagram test download again what the image was built to hold."""

import re
from pathlib import Path

import yaml
from mkdocs.utils.yaml import get_yaml_loader

ROOT = Path(__file__).resolve().parent.parent


def dockerfile_args(dockerfile):
    return dict(re.findall(r"^ARG (\w+)=(\S+)$", (ROOT / "ci" / dockerfile).read_text(), flags=re.M))


def test_the_base_image_has_the_mermaid_cli_test_site_renders_with():
    mermaid = yaml.load((ROOT / "mkdocs.yml").read_text(), Loader=get_yaml_loader())["extra"]["mermaid"]
    base = dockerfile_args("base.Dockerfile")
    assert (base["MERMAID"], base["MERMAID_CLI"]) == (str(mermaid["version"]), str(mermaid["cli"]))
