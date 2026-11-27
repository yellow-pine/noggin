# PROTOTYPE, throwaway: option A of #967 in rough CAD

Not for main. The primary source behind the result posted on
https://github.com/yellow-pine/noggin/issues/967 (the eye gimbal re-laid round the lids' swept shell).

Run from a worktree of PR #1029's branch with `just ours` built, the scripts copied to `/tmp/967-proto` without their `.txt` (they are kept as text so the lint leaves a throwaway alone) and the last
implementer's `/tmp/967-lids/common.py` (here as `common_967_lids.py`) beside the private sculpt file:

1. `eyefit.py`: each eyeball's centre and radius fitted to its dome.
2. `measure.py`: the openings' edges and the skin about the fitted centres (`geom2.npz`).
3. `space.py`: the rest of the head swept over pan, tilt and jaw, as voxels (`space.npz`).
4. `optionB.py`: the re-laid parts as rough solids and every check (`optionB.out` is its last output).
   `optionA.py` is the first pass, about the old eye centres.
5. `lidsB.py`: where the lids' own carriers may stand.

`lib.py` holds the shared checks. Nothing here is tested or meant to last.
