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

## Option (b), 2026-11-27 (#967 comment 7226349814)

Scratch for Cansin's option (b): the lower lid's edge on the bottom rim, the upper lid's the same curve. Copied to
`/tmp/967-s5b` without the `b-` and `.txt`, run from a worktree of main with `just ours` built:

1. `b-rims.py`: each opening's rim on his 37.1 mm ball from the eye white's cut (`rims.npz`).
2. `b-protoB.py`: the lids' angles, what stands in their sweep on main's parts, his skin over them (`b-protoB.out`;
   it reads the last implementer's `/tmp/967-s5/L.npz`, `R.npz`).
3. `b-lids_job.py` with `b-lids_blender.py`: the lids open, half shut and shut as plain surfaces in Cansin's review
   file (`~/Desktop/noggin-stage3.blend`), with the shut line 6.5 deg over the eye's middle; `b-shot.py` renders it.
   A rebuild of the review file drops the preview: run `lids_job.py` again.

`cups.py`: each push-rod's cup against its ball's neck on the exact solids (#1073).
