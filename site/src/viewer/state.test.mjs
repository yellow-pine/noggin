// The viewer's state: its deep link, picker address, caption and Explode's steps, from the site's macros.json (npm test)
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { expect, test } from "vitest";
import { moments } from "../macros.json";
import {
  ANIMATING, VIEW, address, between, caption, glb, looped, mixed, moves, opened, paint, partOf, shows, touched,
} from "./state.mjs";
import { PRESETS } from "../theme.mjs";

const stages = ["stage1", "stage2", "mech-back"];  // the viewer page's Stage buttons (#720)

test("every clip's caption says what plays: a gesture's the Claude Code event, Rest's and the hero loop's their own", () => {
  expect(caption("wink")).toBe("Wink: a session starts (SessionStart)");
  expect(caption("rest")).toBe("Rest: the Mech at rest, between gestures");
  expect(caption("hero")).toBe("Hero: the demo loop, every move in one");
  for (const c of [...Object.keys(moments), "rest", "hero"]) expect(caption(c)).not.toMatch(/undefined/);
});

test("with no gesture named, a viewer plays its Stage's hero loop, else Rest (a Stage with no neck)", () => {
  expect(looped(["wink", "hero", "rest"])).toBe("hero");
  expect(looped(["hero", "wink", "rest"])).toBe("hero");
  expect(looped(["wink", "rest"])).toBe("rest");
});

test("a view= opens the camera from the front, the side or isometric; none, or an unknown one, the default framing", () => {
  expect(opened("?view=front", [], "x").view).toEqual([0, 0, 1]);  // glTF's Y-up: the eyes face +Z
  expect(opened("?view=side", [], "x").view).toEqual([1, 0, 0]);  // its left, as the panels (pictures.py VIEWS)
  expect(opened("?view=isometric", [], "x").view).toEqual([1, 1, 1]);
  for (const s of ["", "?view=top"]) expect(opened(s, [], "x").view).toEqual(VIEW);
});

test("a part= shows that part alone, every copy of it, the rest ghosted; none, every part", () => {
  const { part } = opened("?part=L+lid+horn", [], "x");
  expect(part).toBe("L lid horn");
  expect(shows(part, "L lid horn:1")).toBe(true);  // Blender's node, its copy number after the colon
  expect(shows(part, "L lid horn")).toBe(true);
  expect(shows(part, "L lid horn link:1")).toBe(false);
  expect(shows(part, "R lid horn:1")).toBe(false);
  expect(shows(opened("", [], "x").part, "R lid horn:1")).toBe(true);
});

test("a mesh's part is its glTF node's name as Blender wrote it, which part= picks", async () => {
  const gltf = {
    asset: { version: "2.0" },
    scene: 0,
    scenes: [{ nodes: [0] }],
    nodes: [{ name: "jaw:1", mesh: 0, extras: { explode: [0, 0, 0] } }],
    buffers: [{ byteLength: 36 }],
    bufferViews: [{ buffer: 0, byteLength: 36 }],
    accessors: [{ bufferView: 0, componentType: 5126, count: 3, type: "VEC3", min: [0, 0, 0], max: [0, 0, 0] }],
    meshes: [{ primitives: [{ attributes: { POSITION: 0 } }] }],
  };
  // a GLB as Blender exports one (web/glb.py): its JSON, padded to 4 bytes, then its binary chunk
  const json = Buffer.from(JSON.stringify(gltf).padEnd(Math.ceil(JSON.stringify(gltf).length / 4) * 4));
  const chunk = (type, data) => Buffer.concat([Buffer.from(new Uint32Array([data.length, type]).buffer), data]);
  const body = Buffer.concat([chunk(0x4e4f534a, json), chunk(0x004e4942, Buffer.alloc(36))]);
  const glb = Buffer.concat([Buffer.from(new Uint32Array([0x46546c67, 2, 12 + body.length]).buffer), body]);
  const { scene } = await new GLTFLoader().parseAsync(glb.buffer.slice(glb.byteOffset, glb.byteOffset + glb.length), "");
  const meshes = [];
  scene.traverse((o) => o.isMesh && meshes.push(o));
  expect(meshes.map(partOf)).toEqual(["jaw:1"]);
  expect(shows("jaw", partOf(meshes[0]))).toBe(true);
});

test("view= and part= round-trip through the address the viewer page writes", () => {
  const link = address(stages, "stage1", "wink", 0, "?view=side&part=jaw");
  expect(link).toBe("?view=side&part=jaw&stage=1&gesture=wink");
  expect(opened(link, stages, "x")).toMatchObject({ stage: "stage1", gesture: "wink", part: "jaw", view: [1, 0, 0] });
});

test("an embed only rotates, the wheel and a pinch left to the page; the viewer page zooms and pans too", () => {
  expect(moves(false)).toEqual({ enableRotate: true, enableZoom: false, enablePan: false });
  expect(moves(true)).toEqual({ enableRotate: true, enableZoom: true, enablePan: true });
});

test("a GLB's name is its Stage's as Bones and its Skeleton shape's suffix (#805, #819)", () => {
  expect(glb("stage2", "mechanical")).toBe("stage2-mechanical");
  expect(glb("stage2", "realistic")).toBe("stage2");
});

test("Skin shape none draws Stage 3 bare, the Skeleton alone; a Stage without a Skin draws as it is (#876)", () => {
  expect(glb("mech-back", "realistic", "none")).toBe("mech-back-bare");
  expect(glb("mech-back", "mechanical", "none")).toBe("mech-back-mechanical-bare");
  expect(glb("mech-back", "realistic", "bart")).toBe("mech-back");
  expect(glb("stage2", "mechanical", "none")).toBe("stage2-mechanical");
});

test("a Skin shape drawn on Stage 3 draws its own GLB, after the Skeleton shape's suffix (#813)", () => {
  expect(glb("mech-back", "mechanical", "cansin")).toBe("mech-back-mechanical-cansin");
  expect(glb("mech-back", "realistic", "cansin")).toBe("mech-back-cansin");
  expect(glb("mech-back", "realistic", "morty")).toBe("mech-back");
  expect(glb("stage1", "realistic", "cansin")).toBe("stage1");
});

test("the viewer's mix is the Preset's Shapes and Palettes, each axis the address names another of instead (#819)", () => {
  expect(mixed("", "default-build")).toEqual({
    "skeleton-shape": "mechanical", "skeleton-palette": "black", "skin-shape": "none", "skin-palette": "default",
  });
  const mix = mixed("?preset=morty&skeleton-palette=black&skin-palette=lisa", "morty");
  expect(mix).toEqual({ "skeleton-shape": "realistic", "skeleton-palette": "black", "skin-shape": "morty", "skin-palette": "morty" });
});

test("with no Preset picked, the viewer opens on the Default build: mechanical, black, no Skin (#889)", () => {
  const { "skin-palette": palette, ...build } = mixed("", undefined);
  expect(build).toEqual({ "skeleton-shape": "mechanical", "skeleton-palette": "black", "skin-shape": "none" });
  expect(palette).toBe(Object.values(PRESETS)[0]["skin-palette"]);  // the default Skin palette
  expect(mixed("?skin-shape=bart", undefined)["skin-shape"]).toBe("bart");  // the address still names any
});

test("a mix paints each Colour group in its Palette's hex, black as the GLB's look draws it (#819, #914)", () => {
  const colours = paint(mixed("?skeleton-palette=anatomical", "default-build"), "#3A3A3C");
  expect(colours.Bones).toBe("#DBC8B6");  // PETG Basic Dark Beige
  expect(colours.Mounts).toBe("#3A3A3C");  // PETG Basic Black, lifted to the GLB's black
  expect(colours.face).toBe("#F7CED7");  // PLA Pure Milky Pink
  expect(colours.servo).toBeUndefined();  // the hardware keeps its grey
});

test("a deep link opens its nth Stage, its gesture, and its Explode level", () => {
  expect(opened("?stage=1&gesture=wink", stages, "x")).toMatchObject({ stage: "stage1", gesture: "wink", explode: 0 });
  expect(opened("?preset=morty&stage=3&explode=1", stages, "x")).toMatchObject({
    stage: "mech-back", gesture: null, explode: 1,
  });
  expect(opened("?stage=3&explode=2", stages, "x").explode).toBe(2);  // the Parts level (#811)
  for (const [link, level] of [["9", 2], ["-1", 0], ["parts", 0]]) expect(opened(`?explode=${link}`, stages, "x").explode).toBe(level);
});

test("with no link, or a Stage the page has no button for, the viewer opens its own Stage", () => {
  expect(opened("", stages, "mech-back")).toMatchObject({ stage: "mech-back", gesture: null, explode: 0 });
  expect(opened("?stage=7", stages, "mech-back").stage).toBe("mech-back");
  expect(opened("?stage=1", [], "mech-back").stage).toBe("mech-back");  // a page with no buttons
});

test("the switches keep the address the deep link to what plays, so it can be shared, the Theme's kept", () => {
  expect(address(stages, "stage1", "eureka", 0)).toBe("?stage=1&gesture=eureka");
  const themed = "?preset=morty&skin-palette=bart&stage=1&gesture=wink";  // the bar's Preset, the viewer's mix (#819)
  expect(address(stages, "stage2", undefined, 0, themed)).toBe("?preset=morty&skin-palette=bart&stage=2");
  expect(address(stages, "mech-back", undefined, 1)).toBe("?stage=3&explode=1");  // the hero loop is the default
  expect(address(stages, "mech-back", "wink", 2)).toBe("?stage=3&gesture=wink&explode=2");
  expect(address(stages, "stage3", undefined, 0)).toBe("");  // a Stage the page has no button for
  expect(address([], "mech-back", undefined, 0, "?preset=bart")).toBe("?preset=bart");  // a page with no buttons
});

test("each Explode step moves from one level to the next, still at both ends, half way at its middle (#811)", () => {
  const levels = [[0, 0, 0], [0, 2, 0], [0, 2, 4]];
  expect(between(levels, 0)).toEqual([0, 0, 0]);
  expect(between(levels, 0.5)).toEqual([0, 1, 0]);
  expect(between(levels, 1)).toEqual([0, 2, 0]);
  expect(between(levels, 1.5)).toEqual([0, 2, 2]);
  expect(between(levels, 2)).toEqual([0, 2, 4]);
  expect(between(levels, 0.01)[1]).toBeLessThan(0.0001);  // eased: it starts still
});

test("of the viewers on screen, the three that came into view or were touched last animate (#839)", () => {
  expect(ANIMATING).toBe(3);
  let seen = [];
  for (const v of ["a", "b", "c", "d"]) seen = touched(seen, v, true);  // scrolled into view in turn
  expect(seen.slice(-ANIMATING)).toEqual(["b", "c", "d"]);
  seen = touched(seen, "a", true);  // a drag on the one held still
  expect(seen.slice(-ANIMATING)).toEqual(["c", "d", "a"]);
  seen = touched(seen, "d", false);  // scrolled away
  expect(seen).toEqual(["b", "c", "a"]);
});

test("a viewer in a page opens on its own link, the Stage its own (#839)", () => {
  expect(opened("?gesture=wink&explode=1", [], "stage1")).toMatchObject({ stage: "stage1", gesture: "wink", explode: 1 });
  expect(opened(undefined, [], "stage1")).toMatchObject({ stage: "stage1", gesture: null, explode: 0 });
});
