"""Decimated copies of the printed parts for the Fusion sweep (Fusion measures 10-75k-face faceted bodies at
seconds per pair; ~1500 faces measure in a blink). Run: Blender -b -P model/proxies.py -- <models_dir>... <out>
Writes <out>/<stem>.stl for every STL in the given model folders. `make model-proxies`."""
import bpy, glob, os, sys
TARGET = 1500
args = sys.argv[sys.argv.index("--") + 1:]
out = os.path.abspath(args[-1])
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
for folder in args[:-1]:
    for path in sorted(glob.glob(os.path.join(folder, "*.stl"))):
        bpy.ops.wm.stl_import(filepath=path)
        ob = bpy.context.selected_objects[0]
        n = len(ob.data.polygons)
        if n > TARGET:
            m = ob.modifiers.new("dec", "DECIMATE"); m.ratio = TARGET / n
            bpy.context.view_layer.objects.active = ob; bpy.ops.object.modifier_apply(modifier="dec")
        bpy.ops.wm.stl_export(filepath=os.path.join(out, os.path.basename(path)), export_selected_objects=True)
        print(f"{os.path.basename(path)}: {n} -> {len(ob.data.polygons)} faces")
        bpy.data.objects.remove(ob)
