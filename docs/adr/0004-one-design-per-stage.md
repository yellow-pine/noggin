# One Fusion design per stage, plus a top assembly

The Model could be a single Fusion design with everything inside, or one design per Stage (eyes, pan-tilt,
mouth) inserted as Sub-assemblies into a top design `noggin`. We chose the latter: each Stage carries
its own joints and can be rebuilt and versioned by script on its own, the top assembly only adds the
joints between Stages (bracket stem into tilt arm, jaw onto bracket), and a future Stage or a redesigned
base is one more design rather than a rebuild of everything.

## Consequences

- Scripts rebuild a Stage document in place and save a new version; the top assembly references
  those versions, so after a Stage rebuild the top assembly is re-saved too.
- Joints across a referenced Sub-assembly must use its exposed geometry; where that is awkward,
  a joint origin is placed in the Stage design for the top assembly to use.

## Update 2026-10-31: exclusive ownership and references

Each part lives in exactly one Stage design: pan-tilt owns the base, both electronics sets and the batteries;
eyes owns main bracket v2 and the eye mech; mouth owns the jaws, the servo mount and the connector bar. A Stage
that needs another Stage's geometry inserts that design as a reference (`addByInsert`), never a copy, and the top
assembly inserts the three Stages once. Underneath, every STL and STEP is converted to a solid once into a parts
library design and inserted by reference, so builds stop re-converting meshes (docs/research/2026-10-31-fusion-throughput.md).

### Implemented 2026-10-31 (#32): copies for jointed parts, references for context

`make model-parts` converts each STL (with its proxy body, spool appearance and PLA material) and STEP once into
`parts/`. Measured over the 31 parts: inserting them by reference takes 42 s, as copies 85 s, as references with
`breakLink` 83 s; the old per-Stage mesh converts took about 60 s plus the timeline growth. A referenced component
cannot be renamed (`root component name cannot be changed`) and the joint-origin sketches `fusion_lib.joint_origin`
adds would land in the shared library component, so parts that carry Pivots are inserted as copies
(`addByInsert(..., isReferencedComponent=False)`: the stored solid, no convert), and grounded context without joints
(the PandT base in noggin-eyes, noggin-eyes in noggin-mouth) by reference. Moving the Pivot origins into the library
parts would make everything referenceable; not done. Rebuilds compare the library version plus the placement matrix.
Chunking: custom events only fire while the build pumps `adsk.doEvents()` (nothing is dispatched once the MCP call
returns), so `fusion_lib.chunked` fires one part insert per event from inside the call and returns after the last.

## Update 2026-10-31 (#17): four sub-assemblies, three cumulative Stage documents

The top assembly `noggin` is replaced by Stage documents that show what each build on the desk looks like: `noggin-stage1`
= base + eyes with the bracket stem through the pan recess, `noggin-stage2` = base + stack + eyes with the stem in the tilt
arm window, `noggin-stage3` = stage2 + mouth. The pan-tilt design is split so the base plate can be shared: `noggin-base`
(PandT base, electronics set 1, switch 1, battery 1) and `noggin-stack` (the neck: bearing block, pan base, upright, tilt
arm, servos, horns, bars, electronics set 2, switch 2, battery 2). `noggin-eyes` no longer carries the base as context;
`noggin-mouth` keeps its eyes reference, hidden in stage3. A Stage document inserts each sub-assembly once by reference
(model/geometry.py STAGES, STEM_IN) and holds them with as-built rigid joints (no geometry, so nothing is written into a
referenced design): stack on base, stem in STEM_IN's part, top jaw on the bracket. model/stage.py prints the part count
and the duplicates (none) as the proof. The old `noggin-pan-tilt` document and its sweep report stay as the geometry
fixture of base + stack.
