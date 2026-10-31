"""PROTOTYPE (throwaway, #47 style pick): render the posed parts from model/render/proto_export.py in three styles,
same camera. Run: Blender -b -P model/render/proto_blender.py -- <parts_dir> <out_dir>
Writes <out_dir>/style-A.png, style-B.png, style-C.png and style-variants.jpg (side by side).
A lighter: satin plastic, soft shadow, thin dark-grey lines. B medium: satin mixed with a two-step toon, one highlight,
black lines. C stronger: cel shading (one shadow band, one highlight band), bold black lines."""

import json
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1 :]
parts_dir, out = (os.path.abspath(a) for a in args)
W, H = 1200, 900
BG = "#F7F4EE"
BLACK_LIFT = "#2B2B2E"  # Absolute Black drawn a touch lighter so its shading and lines read
STYLES = {  # line px, line colour, toon mix (0 satin .. 1 cel), shadow tone, highlight strength
    "A": dict(px=1.5, line="#4A4A4A", toon=0.0, shadow=0.0, hl=0.0),
    "B": dict(px=2.5, line="#000000", toon=0.55, shadow=0.72, hl=0.35),
    "C": dict(px=3.5, line="#000000", toon=1.0, shadow=0.62, hl=0.55),
}


def lin(hexc):
    c = [int(hexc[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]


def material(name, hexc, s):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    nt.nodes.clear()
    n, link = nt.nodes.new, nt.links.new
    outn = n("ShaderNodeOutputMaterial")
    satin = n("ShaderNodeBsdfPrincipled")
    satin.inputs["Base Color"].default_value = lin(hexc)
    satin.inputs["Roughness"].default_value = 0.45
    satin.inputs["Specular IOR Level"].default_value = 0.25
    if not s["toon"]:
        link(satin.outputs[0], outn.inputs["Surface"])
        return m
    # toon: diffuse light -> two-step ramp times the base colour, plus one hard glossy highlight band
    diff = n("ShaderNodeBsdfDiffuse")
    d_rgb = n("ShaderNodeShaderToRGB")
    d_bw = n("ShaderNodeRGBToBW")
    ramp = n("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].color = (s["shadow"],) * 3 + (1,)
    ramp.color_ramp.elements[1].position = 0.7  # lit = sun + ambient; shadow = ambient only
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    link(diff.outputs[0], d_rgb.inputs[0])
    link(d_rgb.outputs["Color"], d_bw.inputs[0])
    link(d_bw.outputs[0], ramp.inputs[0])
    shade = n("ShaderNodeMix")
    shade.data_type, shade.blend_type = "RGBA", "MULTIPLY"
    shade.inputs["Factor"].default_value = 1.0
    shade.inputs["A"].default_value = lin(hexc)
    link(ramp.outputs["Color"], shade.inputs["B"])
    gloss = n("ShaderNodeBsdfGlossy")
    gloss.inputs["Roughness"].default_value = 0.3
    g_rgb = n("ShaderNodeShaderToRGB")
    g_bw = n("ShaderNodeRGBToBW")
    g_ramp = n("ShaderNodeValToRGB")
    g_ramp.color_ramp.interpolation = "CONSTANT"
    g_ramp.color_ramp.elements[1].position = 0.8
    g_ramp.color_ramp.elements[1].color = (s["hl"],) * 3 + (1,)
    link(gloss.outputs[0], g_rgb.inputs[0])
    link(g_rgb.outputs["Color"], g_bw.inputs[0])
    link(g_bw.outputs[0], g_ramp.inputs[0])
    hl = n("ShaderNodeMix")
    hl.data_type = "RGBA"
    link(g_ramp.outputs["Color"], hl.inputs["Factor"])
    link(shade.outputs["Result"], hl.inputs["A"])
    hl.inputs["B"].default_value = (1, 1, 1, 1)
    emit = n("ShaderNodeEmission")
    link(hl.outputs["Result"], emit.inputs["Color"])
    if s["toon"] >= 1:
        link(emit.outputs[0], outn.inputs["Surface"])
        return m
    mix = n("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = s["toon"]
    link(satin.outputs[0], mix.inputs[1])
    link(emit.outputs[0], mix.inputs[2])
    link(mix.outputs[0], outn.inputs["Surface"])
    return m


def scene_setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
    sc.render.film_transparent = True  # the background is laid in below, so it does not light the parts
    sc.view_settings.view_transform = "Standard"  # spool colours as given, no filmic desaturation
    sc.eevee.taa_render_samples = 64
    world = bpy.data.worlds.new("w")
    world.color = (1, 1, 1)
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (1, 1, 1, 1)
    sc.world = world
    meta = json.load(open(os.path.join(parts_dir, "manifest.json")))
    objs = {}
    for ply, p in meta["parts"].items():
        bpy.ops.wm.ply_import(filepath=os.path.join(parts_dir, ply))
        ob = bpy.context.selected_objects[0]
        ob.name = p["name"]
        ob.data.transform(Matrix.Scale(0.001, 4))  # mm -> m
        ob.data.shade_smooth()
        ob.data.set_sharp_from_angle(angle=math.radians(35))  # smooth the STL facets, keep designed edges crisp
        wn = ob.modifiers.new("wn", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        if (
            "pupil" in ob.name
        ):  # the pupil face lies on the eyeball sphere: lift it so it neither z-fights nor dashes its outline
            ob.modifiers.new("lift", "DISPLACE").strength = 0.0003
        objs[ob] = BLACK_LIFT if p["colour"] == "#000000" else p["colour"]
    # camera: front-left three-quarter (viewer's left of the Mech's front, which faces -Y), looking down 25 deg,
    # fitted to every vertex
    el, az = math.radians(25), math.radians(45)
    back = Vector((-math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.lens, cam.data.clip_start, cam.data.clip_end = 60, 0.01, 10
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.rotation_euler = (-back).to_track_quat("-Z", "Y").to_euler()
    pts = np.concatenate([np.array([(o.matrix_world @ v.co)[:] for v in o.data.vertices]) for o in objs])
    co, _ = cam.camera_fit_coords(bpy.context.evaluated_depsgraph_get(), pts.ravel().tolist())
    target = Vector(pts.mean(axis=0))
    cam.location = target + (Vector(co) - target) * 1.08  # a little margin
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sc.collection.objects.link(sun)
    sun.rotation_euler = -Vector(
        (0.35, -0.7, 0.9)
    )  # key light from the upper front, a little right: the near sides take the shadow.to_track_quat("-Z", "Y").to_euler()
    sun.data.angle = math.radians(12)
    return sc, objs, sun, world


def lines(sc, s):
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode = "ABSOLUTE"
    sc.render.line_thickness = 1.0
    vl = sc.view_layers[0]
    vl.use_freestyle = True
    fs = vl.freestyle_settings
    fs.crease_angle = math.radians(120)  # Blender measures the face angle: 120 = normals 60 deg apart
    ls = fs.linesets[0] if fs.linesets else fs.linesets.new("lines")
    ls.select_by_visibility, ls.visibility = True, "VISIBLE"
    ls.select_by_edge_types = True
    for t in ("silhouette", "border", "crease"):
        setattr(ls, "select_" + t, True)
    for t in ("contour", "external_contour", "material_boundary", "suggestive_contour", "ridge_valley", "edge_mark"):
        setattr(ls, "select_" + t, False)
    if ls.linestyle is None:  # factory-empty files carry no line style
        ls.linestyle = bpy.data.linestyles.new("line")
    ls.linestyle.color = lin(s["line"])[:3]
    ls.linestyle.thickness = s["px"]
    ls.linestyle.chaining = "PLAIN"


def flatten(path):
    """Lay the transparent render over the plain background, in place; returns the RGB array (rows bottom-up)."""
    img = bpy.data.images.load(path)
    px = np.array(img.pixels[:]).reshape(H, W, 4)
    bg = np.array([int(BG[i : i + 2], 16) / 255 for i in (1, 3, 5)])  # 8-bit PNG pixels are display values
    a = px[..., 3:4]
    rgb = px[..., :3] * a + bg * (1 - a)
    img.pixels[:] = np.concatenate([rgb, np.ones((H, W, 1))], axis=2).ravel()
    img.save()
    bpy.data.images.remove(img)
    return rgb


sc, objs, sun, world = scene_setup()
sides = []
for key, s in STYLES.items():
    for ob, hexc in objs.items():
        ob.data.materials.clear()
        ob.data.materials.append(material(f"{key}-{ob.name}", hexc, s))
    soft = key == "A"
    sun.data.energy = 1.5 if soft else 2.6
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6 if soft else 0.4
    lines(sc, s)
    path = os.path.join(out, f"style-{key}.png")
    sc.render.filepath = path
    sc.render.image_settings.file_format, sc.render.image_settings.color_mode = "PNG", "RGBA"
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"style-{key}: {time.time() - t:.1f} s")
    sides.append(flatten(path))
both = bpy.data.images.new("variants", W * 3, H)
both.pixels[:] = np.concatenate([np.concatenate([r, np.ones((H, W, 1))], axis=2) for r in sides], axis=1).ravel()
both.filepath_raw = os.path.join(out, "style-variants.jpg")
both.file_format = "JPEG"
both.save()
