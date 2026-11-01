"""Under xdist (CI's -n auto) each worker writes its MJCF into a folder of its own: mjcf.write truncates and rewrites
model/build/mjcf/<doc>.xml, so a worker loading a document while another rewrites it could read half a file."""

import os

from model import mjcf

# Patched here, not in mjcf.py: mjcf.py is a sim input, so an edit runs the sim again in CI (check.yml's sim shard).
# shortcut: replaces write()'s whole defaults tuple, right while folder is its only default; redo if write gains another.
if worker := os.environ.get("PYTEST_XDIST_WORKER"):
    mjcf.write.__defaults__ = (os.path.join(mjcf.MJCF, worker),)
