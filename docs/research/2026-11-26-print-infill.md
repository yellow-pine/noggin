# What a printed part weighs: the slicer's default process (#1003)

The sim weighed every printed part as solid filament until #1003. Cansin decided to weigh them at their real print
infill. His own slicer settings aren't recorded, so the model takes Bambu Studio's default process, the slicer for the
Bambu filaments the parts are printed in (inferred).

## The default process

From Bambu Studio's system profiles (master, read 2026-11-26):

- [`resources/profiles/BBL/process/fdm_process_common.json`](https://github.com/bambulab/BambuStudio/blob/master/resources/profiles/BBL/process/fdm_process_common.json):
  `wall_loops` 2, `outer_wall_line_width` 0.42, `inner_wall_line_width` 0.45, `layer_height` 0.2,
  `bottom_shell_layers` 3, `sparse_infill_density` 15%, `sparse_infill_pattern` grid.
- [`fdm_process_single_0.20.json`](https://github.com/bambulab/BambuStudio/blob/master/resources/profiles/BBL/process/fdm_process_single_0.20.json),
  which the single-nozzle 0.20 mm profiles inherit: `top_shell_layers` 5, `top_shell_thickness` 1.0.

## What the model takes

- Walls about 0.87 mm (0.42 + 0.45), the top 1.0 mm (5 x 0.2) and the bottom 0.6 mm (3 x 0.2).
- One skin about 0.85 mm thick round the whole surface, and a 15% core inside it (model/mjcf.py mass()).
- A part thinner than two skins prints solid.
- The grid's own line overlap and the slicer's gap fill are left out (inferred).
