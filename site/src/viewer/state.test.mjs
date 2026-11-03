// The viewer's state: its deep link, picker address, caption and Explode's steps, from the site's macros.json (npm test)
import { expect, test } from "vitest";
import { address, between, bony, caption, opened, skeleton } from "./state.mjs";

const stages = ["next-stage1", "next-stage2", "next-mech-back"];  // the viewer page's Stage buttons (#720)

test("a gesture's caption says which Claude Code event plays it, the Tour's says it tours", () => {
  expect(caption("wink")).toBe("Wink: a session starts (SessionStart)");
  expect(caption()).toBe("Tour: every gesture in turn");
});

test("a GLB's name is its Stage's as Bones and its Skeleton's suffix (#805)", () => {
  expect([bony("next-stage2-mechanical"), skeleton("next-stage2-mechanical")]).toEqual(["next-stage2", "-mechanical"]);
  expect([bony("next-stage2"), skeleton("next-stage2")]).toEqual(["next-stage2", ""]);
});

test("a deep link opens its nth Stage in its Skeleton, its gesture, and its Explode level", () => {
  expect(opened("?stage=1&gesture=wink", stages, "x")).toEqual({ stage: "next-stage1", gesture: "wink", explode: 0 });
  expect(opened("?stage=3&skeleton=mechanical&explode=1", stages, "x")).toEqual({
    stage: "next-mech-back-mechanical", gesture: null, explode: 1,
  });
  expect(opened("?stage=3&explode=2", stages, "x").explode).toBe(2);  // the Parts level (#811)
  for (const [link, level] of [["9", 2], ["-1", 0], ["parts", 0]]) expect(opened(`?explode=${link}`, stages, "x").explode).toBe(level);
  expect(opened("?stage=2&skeleton=wooden", stages, "x").stage).toBe("next-stage2");  // a Skeleton the page lacks
});

test("with no link, or a Stage the page has no button for, the viewer opens its own Stage", () => {
  expect(opened("", stages, "next-mech-back")).toEqual({ stage: "next-mech-back", gesture: null, explode: 0 });
  expect(opened("?stage=7&skeleton=mechanical", stages, "next-mech-back").stage).toBe("next-mech-back");
  expect(opened("?stage=1", [], "next-mech-back").stage).toBe("next-mech-back");  // a page with no buttons
});

test("the switches keep the address the deep link to what plays, so it can be shared", () => {
  expect(address(stages, "next-stage1", "eureka", 0)).toBe("?stage=1&gesture=eureka");
  expect(address(stages, "next-stage2-mechanical", undefined, 0)).toBe("?stage=2&skeleton=mechanical");  // a switch: its Tour
  expect(address(stages, "next-mech-back", undefined, 1)).toBe("?stage=3&explode=1");  // the Tour is the default
  expect(address(stages, "next-mech-back", "wink", 2)).toBe("?stage=3&gesture=wink&explode=2");
  expect(address(stages, "stage3", undefined, 0)).toBe("");  // a Stage the page has no button for
  expect(address([], "next-mech-back", undefined, 0)).toBe("");  // a page with no buttons
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
