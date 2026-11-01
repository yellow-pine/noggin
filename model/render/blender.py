"""Blender side of model/render/pictures.py: runs INSIDE Blender (`Blender -b -P model/render/blender.py -- job.json`).
The job names each part's mesh (its own frame, metres) and colour, and the shots: output path, size, camera and every
part's world matrix. Look (docs/model-notes.md): satin plastic in the spool colours mixed with a two-step toon shadow,
one small highlight, ART_PX black Line Art lines on silhouettes and creases, plain light background. Prints each frame's
render time (`frame <file> <s>`), which pictures.py passes to its log."""

import json
import math
import sys
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector

BG = "#F7F4EE"
BLACK_LIFT = "#2B2B2E"  # Absolute Black drawn a touch lighter so its shading and lines read
LINE_PX, TOON, SHADOW, HIGHLIGHT = 2.5, 0.55, 0.72, 0.35  # Cansin's pick (#47 style B); the web viewer's lines
ART_PX = 1.75  # the pictures' Line Art lines: 2.5 px read too bold (Cansin, #276)
SHADOW_AT, HIGHLIGHT_AT = 0.7, 0.8  # where the toon ramps step, on the diffuse and glossy light
CREASE = 60  # degrees between face normals that draw a crease line
SAMPLES = 4  # Eevee's per frame: 64 (then 16) took CI's software GL tens of minutes (#226, #276)
SUN, WORLD = 2.6, 0.4  # the key light's and the world's strength
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
    link(band(n("ShaderNodeBsdfDiffuse"), SHADOW_AT, SHADOW, 1.0), shade.inputs["B"])  # lit = sun + ambient
    gloss = n("ShaderNodeBsdfGlossy")
    gloss.inputs["Roughness"].default_value = 0.3
    hl = n("ShaderNodeMix")
    hl.data_type = "RGBA"
    link(band(gloss, HIGHLIGHT_AT, 0.0, HIGHLIGHT), hl.inputs["Factor"])
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
    sc.eevee.taa_render_samples = SAMPLES
    sc.render.image_settings.file_format, sc.render.image_settings.color_mode = "PNG", "RGBA"
    world = bpy.data.worlds.new("w")
    sc.world = world
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = WORLD
    # Line Art (a Grease Pencil modifier, on several CPU threads) draws the lines: Freestyle took ~90 % of a frame on one
    # thread (docs/research/2026-11-01-render-profile.md, #276); its radius is set per shot (main), the stroke in metres
    gp = bpy.data.grease_pencils.new("lines")
    gp.layers.new("lines")
    ink = bpy.data.materials.new("ink")
    bpy.data.materials.create_gpencil_data(ink)
    ink.grease_pencil.color = (0, 0, 0, 1)
    gp.materials.append(ink)
    lines = bpy.data.objects.new("lines", gp)
    sc.collection.objects.link(lines)
    art = lines.modifiers.new("lines", "LINEART")
    art.source_type, art.target_layer, art.target_material = "SCENE", "lines", ink
    art.use_contour, art.use_crease, art.use_crease_on_smooth, art.use_crease_on_sharp = True, True, True, False
    art.use_intersection = art.use_material = art.use_edge_mark = art.use_loose = False
    art.crease_threshold = math.radians(180 - CREASE)  # the angle between the faces, as Freestyle measured it
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy, sun.data.angle = SUN, math.radians(12)
    sc.collection.objects.link(sun)
    return sc, cam, sun, art


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
        ob.data.materials.append(material(name, BLACK_LIFT if p["colour"] == "#000000" else p["colour"]))
        objs[name] = ob
    return objs


def flatten(path, w, h):
    """Lay the transparent render over the plain background, in place."""
    img = bpy.data.images.load(path)
    px = np.array(img.pixels[:]).reshape(h, w, 4)
    bg = np.array([int(BG[i : i + 2], 16) / 255 for i in (1, 3, 5)])  # 8-bit PNG pixels are display values
    a = px[..., 3:4]
    img.pixels[:] = np.concatenate([px[..., :3] * a + bg * (1 - a), np.ones((h, w, 1))], axis=2).ravel()
    img.save()
    bpy.data.images.remove(img)


def px_metres(cam, objs, width):
    """One pixel's size in metres at the shown parts' centre: the line's radius follows the camera, so a line is ART_PX
    wide on every shot (Line Art strokes are geometry, Freestyle's were pixels)."""
    if cam.data.type == "ORTHO":
        return cam.data.ortho_scale / width
    shown = [ob.matrix_world @ Vector(c) for ob in objs.values() if not ob.hide_render for c in ob.bound_box]
    centre = sum(shown, Vector()) / len(shown)
    depth = (cam.matrix_world.inverted() @ centre).z * -1
    return depth * cam.data.sensor_width / cam.data.lens / width


def main(job):
    sc, cam, sun, art = setup()
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
        art.radius = ART_PX * px_metres(cam, objs, w)  # Blender 5.2 draws the stroke about `radius` wide (measured)
        sc.render.filepath = shot["out"]
        t = time.monotonic()
        bpy.ops.render.render(write_still=True)
        flatten(shot["out"], w, h)
        print(f"frame {shot['out']} {time.monotonic() - t:.2f}", flush=True)


if __name__ == "__main__":  # web/glb.py imports the look
    main(json.load(open(sys.argv[sys.argv.index("--") + 1])))
