# Where the pictures jobs' per-frame time goes

## CI (run 41329223689, site-pictures @714bb6e)
- The logs can't separate Freestyle from Eevee. `pictures.py` captures Blender's stdout and prints it only when the job fails.
- Wall time per frame, startup included: wince 13.8 s, bored 16.3, attention 18.6, thinking 19.9, eureka 20.4, wink 20.6, hero (640x480) 23.1.
- Runner variance: the same hero job with the same settings took 15.0 s per frame in run 41327038151 (westus3) and 23.1 s here (eastus2).

## Local test (M5 with Metal, Blender 5.2.2, stage1 gesture shot, 329k triangles, 480x360)
| variant | s/frame |
|---|---|
| Eevee 16 + Freestyle (current) | 1.60 |
| Eevee 1 + Freestyle | 1.50 |
| Eevee 16 / 1, no lines | 0.15 / 0.09 |
| Eevee 1 or 4 + inverted hull | 0.12 |
| Workbench + hull | 0.07 |
| Eevee 1 + Line Art | 0.85 |
| Freestyle + Culling | 1.52 (no gain) |

Freestyle breakdown from `--debug-freestyle` (one CPU thread, every frame):
- mesh cleaning 0.27 s and WEdge 0.13 s
- view map 0.82 s (196k edges)
- strokes 0.10 s and stroke render 0.06 s

That is about 90 % of the frame.

The stroke render is a second render by the same engine with the Eevee settings copied over (BlenderStrokeRenderer.cpp:110-126). On CI that means two 16-sample Eevee renders per frame.

## Docs (5.2 manual)
- Freestyle loads every mesh at once.
- The View Map Cache only helps when the geometry is static.
- "As Render Pass" changes compositing only, not the work.
- Eevee samples cost time linearly. Shadows are always jittered in final renders.
- Line Art recomputes on the CPU per modifier and frame unless baked.
- Workbench has no shadow maps and no Shader-to-RGB.

## CI estimates, 480x360 (inferred)
CI's single core is about 2-2.5x slower than the M5's, so Freestyle takes ~3-4 s. The rest is Eevee on llvmpipe at ≈0.3-0.6 s per sample across both renders.
- **(a) Eevee 1 + Freestyle: ~4-6 s per frame.**
  - Same look.
  - Shadows get noisier; set the sun angle to 0.
- **(b) Eevee 1-4 + hull: ~1-3 s per frame.**
  - Draws contours only, with no crease or border lines.
  - Speckles at 1 sample.
  - With backface culling, faces whose normals are flipped vanish (the eyeball bars here).
- **(c) Workbench + hull: ~0.5-1.5 s per frame.**
  - Loses the toon look.

## Biggest cuts
1. Drop Freestyle, using a hull or Line Art instead.
2. Lower the samples to 1-4.
3. Decimate the PLYs. The Freestyle view map scales with the face count.
4. Split the frames across more matrix jobs.

To settle the CI split, run one wince job (~4 min) with `--debug-freestyle` and Blender's stdout printed.
