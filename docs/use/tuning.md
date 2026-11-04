# Tuning

Each command, from the repo on the Mac with the noggin service running, and what it changes:

```
noggin/noggin pose lids 0.3 eyes 95     # pose mode: hold this pose, hooks ignored, until follow
noggin/noggin set l_lid_rest 70          # change one calibration number, live, saved to eyes/calibration.json
noggin/noggin reload                     # resend eyes/calibration.json to the Core, after editing it by hand
noggin/noggin exercise 10                # a gentle run-in, mid-range only, for 10 minutes
just demo bored 2                        # repeat one gesture, 5 s apart, to see a change
just demo                                # every gesture on a loop
just follow                              # back to reacting to Claude Code
```

- `pose lids <0-1> [eyes <angle>]` holds the lids at that opening (0 closed, 1 open) and the eyes at that yaw (90
  straight ahead) until `just follow`; Claude Code's hooks are ignored meanwhile.
- `set <key> <value>` changes one number in `eyes/calibration.json` and sends it to the Core at once; in pose mode it
  re-sends the pose, so a lid's closed, rest and open ends can be compared side by side, both eyes at a half-open pose
  as well as at the ends. The keys and what each means are under [Calibration](../build/calibration.md#what-the-numbers-are).
- `release` unpowers the servos, so they slump under gravity; any command powers them again.
- `demo` and `demo <gesture> [level]` play gestures with the hooks ignored; `just follow` (or a restart) ends it.

Set a lid's ends first, then its rest, then the opening fractions (`lid_rest`, `lid_think`, `lid_open`), watching a
gesture after each.
