# The model's servos are DC motors behind their own position loop, fitted to the filmed servo

> #625, part of #51, from docs/research/2026-11-02-literature-simulation.md (1, Practices 1 and 2). Supersedes ADR
> 0007's servo: its position actuators clipped at stall and the trajectories' slew at the no-load speed.

A stiff position actuator that follows a command slewed at the no-load 428 deg/s sets its own peaks: a torque or an
acceleration read from it comes from the clip, not from the servo, and #51 ranks its mechanisms on dynamic torque and
checks its magnets against peak acceleration. Tan et al. (RSS 2018) closed the same gap on hardware with a DC motor
driven by the servo's own PD plus its latency, and MuJoCo 3.17 ships that motor.

- **Each servo is a `dcmotor`** (`mjcf.drive`, the one place it is built, for the Mech and the fit's rig alike):
  `nominal` at the 4.8 V sheet's stall torque and no-load speed referred to the horn, a P loop on position (`input
  pos`, kp full torque 0.5 deg off, kd critically damped on the gear train's armature), its voltage clamped at 4.8 V,
  so it stalls at the sheet's torque and runs along the torque-speed line; its command read 20 ms late (one PWM frame,
  `delay` with a linear history). Every value is inferred (mjcf.SERVO) until fitted.
- **MuJoCo's controller adds the back-EMF to its voltage**, as a current-driven motor; the servo's driver is a voltage
  H-bridge, so below the clamp the model is a little optimistic at speed. Accepted: a P law in Python on the raw
  voltage would cost a step loop of our own in every caller.
- **The trajectories send each command straight to its servo** (model/trajectories.py): the motor, its load and the
  delay set how fast it follows, so the hero's head runs its keys a delay late. `mjcf.pose` still eases its commands
  for the quasi-static sweeps. The report's swing of the stage 3 pan to -40 at the rated speed now lands, where ADR
  0007's servo carried the head through the pan four-bar's toggle.
- **`model/servo_fit.py` fits the values** with MuJoCo's sysid toolbox (`mujoco[sysid]`) to filmed takes of one servo
  (a marker on the horn, the bare horn and a load a few times the gear train's inertia, steps both ways): stall
  torque, no-load speed, armature and delay, the delay started every 10 ms since least squares finds it only from near
  it. kp stays inferred: it acts within the half-degree deadband, finer than a video reads. Lighter loads let the
  armature and the delay trade off (both shift when the horn gets going). It writes model/servo_fit.json, whose values mjcf.SERVO then takes over; the sim and the
  trajectories key on it, so CI builds them again.
- **The fitted delay is the one that plays the Takes as filmed, not the Core's own (#644).** The delay shifts the
  horn's whole motion against the commands, as the video's offset from the Core's clock does, and nothing in the kit
  shows when the Core writes (no light or sound the Core drives). `model/servo_take.py` puts each Take on the Core's
  clock by its slow opening ramp, where the horn lags its commands alike under any load (within a millisecond in the
  model), so a servo's Takes share one offset, and the fitted delay takes it in with the Core's own. A cue the Core
  drives (a light on a free pin) would tell the two apart.

## Considered options

- Keep the position actuator and slew: rejected, its peaks are its own (above).
- `input="voltage"` with the servo's P law computed per step in Python: rejected for now (above); if the fit misses
  at speed, it is the next step, as is LuGre friction (`lugre`) if it misses at low speed.
