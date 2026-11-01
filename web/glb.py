"""Blender side of web/build.py: runs INSIDE Blender (`Blender -b -P web/glb.py -- job.json`). Loads the Stage's
parts in the pictures' satin (model/render/blender.py; the toon band and lines are render-only), keys every part's
world pose per frame of each motion into its own action, stashes each as an NLA track named for the motion (the
exporter merges tracks of one name into one glTF clip) and exports a Draco GLB, Y-up as glTF is."""

import json
import os
import sys

import bpy
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model.render import blender as look  # noqa: E402


def main(job):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = job["fps"]  # one trajectory frame per scene frame
    objs = look.load(job["parts"])
    for name, ob in objs.items():
        nt = ob.active_material.node_tree  # glTF carries the satin only: the toon band and its emission are Eevee's
        nt.links.new(nt.nodes["Principled BSDF"].outputs[0], nt.nodes["Material Output"].inputs["Surface"])
        ob.rotation_mode = "QUATERNION"
        ob.animation_data_create()
        for motion, frames in job["motions"].items():
            q = None
            for i, frame in enumerate(frames):
                ob.matrix_world = Matrix(frame[name])
                if q is not None:
                    ob.rotation_quaternion.make_compatible(q)  # no sign flip between frames
                q = ob.rotation_quaternion.copy()
                ob.keyframe_insert("location", frame=i)
                ob.keyframe_insert("rotation_quaternion", frame=i)
            action = ob.animation_data.action
            action.name = f"{motion} {name}"
            ob.animation_data.nla_tracks.new().name = motion
            ob.animation_data.nla_tracks[-1].strips.new(motion, 0, action)
            ob.animation_data.action = None
        ob.matrix_world = Matrix(next(iter(job["motions"].values()))[0][name])  # at rest when nothing plays
    bpy.ops.export_scene.gltf(
        filepath=job["out"],
        export_format="GLB",
        export_apply=True,  # the pictures' modifiers: weighted normals, the lifted pupil
        export_animation_mode="NLA_TRACKS",
        export_draco_mesh_compression_enable=True,
    )


main(json.load(open(sys.argv[sys.argv.index("--") + 1])))
