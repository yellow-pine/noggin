"""python -m model.review [production|coarse] [before] (just review): the review file (model/review) at OUT."""

import argparse
import os
import sys

from model.review import MORTY, OUT, QUALITY, build

a = argparse.ArgumentParser(description="the review file (model/review)")
a.add_argument("quality", nargs="?", default="production", choices=QUALITY)
a.add_argument("before", nargs="?", default="", choices=["", "before"])
args = a.parse_args()
if not os.path.isfile(MORTY):
    print(f"review: no Morty at {MORTY} (a fresh clone): built without the Morty layer", file=sys.stderr)
build(OUT, args.quality, bool(args.before))
