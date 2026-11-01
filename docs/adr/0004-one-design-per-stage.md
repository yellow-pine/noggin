# Sub-assemblies by reference into cumulative Stages

> Superseded 2026-10-31 (#88): Fusion is gone; our CadQuery parts (model/printed, model/envelopes.py) and the Python engine (since retired, ADR 0007) are the model; FreeCAD opens `make step` exports.

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
eyes owns the eye bracket and the eye mech; mouth owns the jaws, the servo mount and the jaw bar. A Stage
that needs another Stage's geometry inserts that design as a reference (`addByInsert`), never a copy, and the top
assembly inserts the three Stages once. Underneath, every STL and STEP is converted to a solid once into a parts
library design and inserted by reference, so builds stop re-converting meshes (docs/research/2026-10-31-fusion-throughput.md).

### Implemented 2026-10-31 (#32): copies for jointed parts, references for context

`make model-parts` converts each STL (with its spool appearance and PLA material) and STEP once into
`parts/`. Measured over the 31 parts: inserting them by reference takes 42 s, as copies 85 s, as references with
`breakLink` 83 s; the old per-Stage mesh converts took about 60 s plus the timeline growth. A referenced component
cannot be renamed (`root component name cannot be changed`) and the joint-origin sketches `fusion_lib.joint_origin`
adds would land in the shared library component, so parts that carry Pivots are inserted as copies
(`addByInsert(..., isReferencedComponent=False)`: the stored solid, no convert), and grounded context without joints
(the base plate in noggin-eyes, noggin-eyes in noggin-mouth) by reference. Moving the Pivot origins into the library
parts would make everything referenceable; not done. Rebuilds compare the library version plus the placement matrix.
Chunking: custom events only fire while the build pumps `adsk.doEvents()` (nothing is dispatched once the MCP call
returns), so `fusion_lib.chunked` fires one part insert per event from inside the call and returns after the last.

## Update 2026-10-31 (second): cumulative Stages over sub-assemblies

Cansin's Stages are build states, not ownership units. Four sub-assemblies own the parts once (noggin-base: plate,
electronics set 1, switch 1, battery 1; noggin-stack: upright, tilt arm, bearing, pan/tilt servos, bars, set 2,
switch 2, battery 2; noggin-eyes; noggin-mouth). Three Stage designs insert them by reference: noggin-stage1 =
base + eyes with the stem in the pan recess (the desk today), noggin-stage2 = base + stack + eyes on the tilt arm,
noggin-stage3 = stage 2 + mouth, the full Mech. Simulation, photo comparison and reports run per Stage; the
"top assembly" is Stage 3. (#81: one pack and switch board on noggin-base feed both shields through a Y lead, as the
pan-tilt guide builds it; noggin-stack carries receiver shield 2 and Core 2 only.)

### Implemented 2026-10-31 (#17)

`model/base.py` and `model/stack.py` (split from pan_tilt.py, the electronics set shared in `model/electronics.py`);
`noggin-eyes` dropped its base context, `noggin-mouth` keeps its eyes reference (hidden in Stage 3). `model/stage.py`
inserts each sub-assembly once by reference at the frames in `model/geometry.py` STAGES and holds them with as-built rigid
joints (no geometry, so nothing is written into a referenced design): stack on base, bracket stem in STEM_IN's part (depth
inferred), top jaw on the bracket; it prints the part count and the duplicates (none) as the proof. The old `noggin-pan-tilt`
document and its sweep report stay as the geometry fixture of base + stack.

## Update 2026-10-31 (#31, #47): what stands

The original "one design per stage plus a top assembly" is superseded by the updates above: four Sub-assemblies
(base, stack, eyes, mouth) own their parts once, and three cumulative Stage documents (noggin-stage1..3) insert them by
reference. Fusion only builds documents: no screenshots, no canvases, no proxy bodies; the engine simulates
(ADR 0006) and Blender renders.

## Update 2026-11-01 (#172): the desk eyes

Stage 1 puts the desk eye bracket's stem through the base plate's slot, not the pan recess
(docs/research/2026-11-01-eyes-on-plate.md).
