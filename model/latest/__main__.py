"""python -m model.latest (just latest): the latest file (model/latest) at LATEST."""

import os
import sys

from model.latest import LATEST, build
from model.review import MORTY

if not os.path.isfile(MORTY):
    print(f"latest: no Morty at {MORTY} (a fresh clone): Skin reference stays empty", file=sys.stderr)
build(LATEST)
