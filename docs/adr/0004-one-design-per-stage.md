# One Fusion design per stage, plus a top assembly

The Twin could be a single Fusion design with everything inside, or one design per Stage (eyes, pan-tilt,
mouth) inserted as Sub-assemblies into a top design `noggin`. We chose the latter: each Stage carries
its own joints and can be rebuilt and versioned by script on its own, the top assembly only adds the
joints between Stages (bracket stem into tilt arm, jaw onto bracket), and a future Stage or a redesigned
base is one more design rather than a rebuild of everything.

## Consequences

- Scripts rebuild a Stage document in place and save a new version; the top assembly references
  those versions, so after a Stage rebuild the top assembly is re-saved too.
- Joints across a referenced Sub-assembly must use its exposed geometry; where that is awkward,
  a joint origin is placed in the Stage design for the top assembly to use.
