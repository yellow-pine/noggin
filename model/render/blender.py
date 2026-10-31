"""Blender side of model/render/pictures.py: runs INSIDE Blender (`Blender -b -P model/render/blender.py -- job.json`).
The job names each part's mesh (its own frame, metres) and colour, and the shots: output path, size, camera and every
part's world matrix. Look (docs/model-notes.md): satin plastic in the spool colours mixed with a two-step toon shadow,
one small highlight, 2.5 px black Freestyle lines on silhouettes, borders and creases, plain light background."""

import json
import math
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

LINE_PX, TOON, SHADOW, HIGHLIGHT = 2.5, 0.55, 0.72, 0.35  # Cansin's pick (#47 style B)
KEY = (0.62, 0.60, 0.51)  # key light toward the camera's upper right, in the camera's (right, up, back) frame


def lin(hexc):
    c = [int(hexc[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]


def material(name, hexc):
    """Satin principled BSDF mixed with a toon pass: diffuse light through a two-step ramp times the base colour,
    plus one hard glossy highlight band (Shader to RGB: Eevee only)."""
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    nt.nodes.clear()
    n, link = nt.nodes.new, nt.links.new

    def band(shader, at, low, high):
        rgb, bw, ramp = n("ShaderNodeShaderToRGB"), n("ShaderNodeRGBToBW"), n("ShaderNodeValToRGB")
        ramp.color_ramp.interpolation = "CONSTANT"
        ramp.color_ramp.elements[0].color = (low,) * 3 + (1,)
        ramp.color_ramp.elements[1].position = at
        ramp.color_ramp.elements[1].color = (high,) * 3 + (1,)
        link(shader.outputs[0], rgb.inputs[0])
        link(rgb.outputs["Color"], bw.inputs[0])
        link(bw.outputs[0], ramp.inputs[0])
        return ramp.outputs["Color"]

    satin = n("ShaderNodeBsdfPrincipled")
    satin.inputs["Base Color"].default_value = lin(hexc)
    satin.inputs["Roughness"].default_value = 0.45
    satin.inputs["Specular IOR Level"].default_value = 0.25
    shade = n("ShaderNodeMix")
    shade.data_type, shade.blend_type = "RGBA", "MULTIPLY"
    shade.inputs["Factor"].default_value = 1.0
    shade.inputs["A"].default_value = lin(hexc)
    link(band(n("ShaderNodeBsdfDiffuse"), 0.7, SHADOW, 1.0), shade.inputs["B"])  # lit = sun + ambient
    gloss = n("ShaderNodeBsdfGlossy")
    gloss.inputs["Roughness"].default_value = 0.3
    hl = n("ShaderNodeMix")
    hl.data_type = "RGBA"
    link(band(gloss, 0.8, 0.0, HIGHLIGHT), hl.inputs["Factor"])
    link(shade.outputs["Result"], hl.inputs["A"])
    hl.inputs["B"].default_value = (1, 1, 1, 1)
    emit = n("ShaderNodeEmission")
    link(hl.outputs["Result"], emit.inputs["Color"])
    mix = n("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = TOON
    link(satin.outputs[0], mix.inputs[1])
    link(emit.outputs[0], mix.inputs[2])
    link(mix.outputs[0], n("ShaderNodeOutputMaterial").inputs["Surface"])
    return m


def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.film_transparent = True  # the background is laid in after, so it does not light the parts
    sc.view_settings.view_transform = "Standard"  # spool colours as given
    sc.eevee.taa_render_samples = 64
    sc.render.image_settings.file_format, sc.render.image_settings.color_mode = "PNG", "RGBA"
    world = bpy.data.worlds.new("w")
    sc.world = world
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.4
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode, sc.render.line_thickness = "ABSOLUTE", 1.0
    vl = sc.view_layers[0]
    vl.use_freestyle = True
    vl.freestyle_settings.crease_angle = math.radians(120)  # the angle between faces: normals 60 deg apart
    ls = vl.freestyle_settings.linesets.new("lines")
    ls.select_by_visibility, ls.visibility, ls.select_by_edge_types = True, "VISIBLE", True
    for t in ("silhouette", "border", "crease"):
        setattr(ls, "select_" + t, True)
    ls.linestyle = bpy.data.linestyles.new("line")
    ls.linestyle.color, ls.linestyle.thickness, ls.linestyle.chaining = (0, 0, 0), LINE_PX, "PLAIN"
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy, sun.data.angle = 2.6, math.radians(12)
    sc.collection.objects.link(sun)
    return sc, cam, sun


def load(parts):
    objs = {}
    for name, p in parts.items():
        bpy.ops.wm.ply_import(filepath=p["ply"])
        ob = bpy.context.selected_objects[0]
        ob.name = name
        ob.data.shade_smooth()
        ob.data.set_sharp_from_angle(angle=math.radians(35))  # smooth the STL facets, keep designed edges crisp
        ob.modifiers.new("wn", "WEIGHTED_NORMAL").keep_sharp = True
        if (
            "pupil" in name
        ):  # the pupil face lies on the eyeball sphere: lifted, it neither z-fights nor dashes its outline
            ob.modifiers.new("lift", "DISPLACE").strength = 0.0003
        ob.data.materials.append(material(name, p["colour"]))  # Absolute Black already lifted (scene.drawn)
        objs[name] = ob
    return objs


def flatten(path, w, h, hexc):
    """Lay the transparent render over the plain background (hexc, scene.BG), in place."""
    img = bpy.data.images.load(path)
    px = np.array(img.pixels[:]).reshape(h, w, 4)
    bg = np.array([int(hexc[i : i + 2], 16) / 255 for i in (1, 3, 5)])  # 8-bit PNG pixels are display values
    a = px[..., 3:4]
    img.pixels[:] = np.concatenate([px[..., :3] * a + bg * (1 - a), np.ones((h, w, 1))], axis=2).ravel()
    img.save()
    bpy.data.images.remove(img)


def main(job):
    sc, cam, sun = setup()
    objs = load(job["parts"])
    for shot in job["shots"]:
        for name, ob in objs.items():
            ob.hide_render = name not in shot["pose"]  # a shot shows only the parts it poses
            if not ob.hide_render:
                ob.matrix_world = Matrix(shot["pose"][name])
        c = shot["camera"]
        cam.matrix_world = Matrix(c["matrix"])
        cam.data.type = "PERSP" if c["lens"] else "ORTHO"
        if c["lens"]:
            cam.data.lens = c["lens"]
        else:
            cam.data.ortho_scale = c["ortho_scale"]
        cam.data.clip_start, cam.data.clip_end = 0.001, 10
        key = cam.matrix_world.to_3x3() @ Vector(KEY)
        sun.rotation_euler = (-key).to_track_quat("-Z", "Y").to_euler()
        w, h = shot["size"]
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
        sc.render.filepath = shot["out"]
        bpy.ops.render.render(write_still=True)
        flatten(shot["out"], w, h, job["bg"])


main(json.load(open(sys.argv[sys.argv.index("--") + 1])))
