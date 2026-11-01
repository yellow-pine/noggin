# Tuning

```
noggin/noggin pose lids 0.3 eyes 95     # pose mode: hold it, hooks ignored, until follow; each set re-sends it
noggin/noggin set l_lid_rest 70          # live calibration, saved to eyes/calibration.json
noggin/noggin exercise 10                # gentle run-in, 10 minutes
make demo ARGS="bored 2"                 # one gesture, to see a change
make follow                              # back to reacting to Claude Code
```

Pose mode holds a pose while you tune: every `set` re-sends it, so a lid's closed, rest and open ends can be compared
side by side, both eyes at a half-open pose as well as at the ends. What the numbers mean and the lessons from tuning
the real lids are under [Calibration](../build/calibration.md).
