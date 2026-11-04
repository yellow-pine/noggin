// The viewer's state: its deep link, picker address, caption and Explode's steps, from the site's macros.json (npm test)
import { expect, test } from "vitest";
import { ANIMATING, address, between, caption, glb, mixed, opened, paint, touched } from "./state.mjs";

const stages = ["stage1", "stage2", "mech-back"];  // the viewer page's Stage buttons (#720)

test("a gesture's caption says which Claude Code event plays it, the Tour's says it tours", () => {
  expect(caption("wink")).toBe("Wink: a session starts (SessionStart)");
  expect(caption()).toBe("Tour: every gesture in turn");
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

test("the viewer's mix is the Preset's Shapes and Palettes, each axis the address names another of instead (#819)", () => {
  expect(mixed("", "default-build")).toEqual({
    "skeleton-shape": "mechanical", "skeleton-palette": "black", "skin-shape": "cansin", "skin-palette": "default",
  });
  const mix = mixed("?preset=morty&skeleton-palette=black&skin-palette=lisa", "morty");
  expect(mix).toEqual({ "skeleton-shape": "realistic", "skeleton-palette": "black", "skin-shape": "morty", "skin-palette": "morty" });
});

test("with no Preset picked, the viewer opens on the bare anatomical Skeleton, its Skin Morty once on (#883)", () => {
  expect(mixed("", undefined)).toEqual({
    "skeleton-shape": "realistic", "skeleton-palette": "anatomical", "skin-shape": "none", "skin-palette": "morty",
  });
  expect(mixed("?skin-shape=bart", undefined)["skin-shape"]).toBe("bart");  // the address still names any
});

test("a mix paints each Colour group in its Palette's hex, black as Blender draws it (#819)", () => {
  const colours = paint(mixed("?skeleton-palette=anatomical", "default-build"));
  expect(colours.Bones).toBe("#DBC8B6");  // PETG Basic Dark Beige
  expect(colours.Mounts).toBe("#2B2B2E");  // PETG Basic Black, lifted
  expect(colours.face).toBe("#F7CED7");  // PLA Pure Milky Pink
  expect(colours.servo).toBeUndefined();  // the hardware keeps its grey
});

test("a deep link opens its nth Stage, its gesture, and its Explode level", () => {
  expect(opened("?stage=1&gesture=wink", stages, "x")).toEqual({ stage: "stage1", gesture: "wink", explode: 0 });
  expect(opened("?preset=morty&stage=3&explode=1", stages, "x")).toEqual({
    stage: "mech-back", gesture: null, explode: 1,
  });
  expect(opened("?stage=3&explode=2", stages, "x").explode).toBe(2);  // the Parts level (#811)
  for (const [link, level] of [["9", 2], ["-1", 0], ["parts", 0]]) expect(opened(`?explode=${link}`, stages, "x").explode).toBe(level);
});

test("with no link, or a Stage the page has no button for, the viewer opens its own Stage", () => {
  expect(opened("", stages, "mech-back")).toEqual({ stage: "mech-back", gesture: null, explode: 0 });
  expect(opened("?stage=7", stages, "mech-back").stage).toBe("mech-back");
  expect(opened("?stage=1", [], "mech-back").stage).toBe("mech-back");  // a page with no buttons
});

test("the switches keep the address the deep link to what plays, so it can be shared, the Theme's kept", () => {
  expect(address(stages, "stage1", "eureka", 0)).toBe("?stage=1&gesture=eureka");
  const themed = "?preset=morty&skin-palette=bart&stage=1&gesture=wink";  // the bar's Preset, the viewer's mix (#819)
  expect(address(stages, "stage2", undefined, 0, themed)).toBe("?preset=morty&skin-palette=bart&stage=2");
  expect(address(stages, "mech-back", undefined, 1)).toBe("?stage=3&explode=1");  // the Tour is the default
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
  expect(opened("?gesture=wink&explode=1", [], "stage1")).toEqual({ stage: "stage1", gesture: "wink", explode: 1 });
  expect(opened(undefined, [], "stage1")).toEqual({ stage: "stage1", gesture: null, explode: 0 });
});
