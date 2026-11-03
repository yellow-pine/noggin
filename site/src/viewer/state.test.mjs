// The viewer's state: its deep link, picker address, caption and explode offsets, from the site's macros.json (npm test)
import { expect, test } from "vitest";
import { address, bony, caption, offsets, opened, skeleton } from "./state.mjs";

const stages = ["next-stage1", "next-stage2", "next-mech-back"];  // the viewer page's Stage buttons (#720)

test("a gesture's caption says which Claude Code event plays it, the Tour's says it tours", () => {
  expect(caption("wink")).toBe("Wink: a session starts (SessionStart)");
  expect(caption()).toBe("Tour: every gesture in turn");
});

test("a GLB's name is its Stage's as Bones and its Skeleton's suffix (#805)", () => {
  expect([bony("next-stage2-mechanical"), skeleton("next-stage2-mechanical")]).toEqual(["next-stage2", "-mechanical"]);
  expect([bony("next-stage2"), skeleton("next-stage2")]).toEqual(["next-stage2", ""]);
});

test("a deep link opens its nth Stage in its Skeleton, its gesture, and exploded only a document that comes apart", () => {
  expect(opened("?stage=1&gesture=wink", stages, "x")).toEqual({ stage: "next-stage1", gesture: "wink", exploded: false });
  expect(opened("?stage=3&skeleton=mechanical&explode=1", stages, "x")).toEqual({
    stage: "next-mech-back-mechanical", gesture: null, exploded: true,
  });
  expect(opened("?stage=2&skeleton=wooden", stages, "x").stage).toBe("next-stage2");  // a Skeleton the page lacks
  expect(opened("?stage=1&explode=1", ["stage1"], "stage1").exploded).toBe(false);  // one without offsets stays together
});

test("with no link, or a Stage the page has no button for, the viewer opens its own Stage", () => {
  expect(opened("", stages, "next-mech-back")).toEqual({ stage: "next-mech-back", gesture: null, exploded: false });
  expect(opened("?stage=7&skeleton=mechanical", stages, "next-mech-back").stage).toBe("next-mech-back");
  expect(opened("?stage=1", [], "next-mech-back").stage).toBe("next-mech-back");  // a page with no buttons
});

test("the switches keep the address the deep link to what plays, so it can be shared", () => {
  expect(address(stages, "next-stage1", "eureka", false)).toBe("?stage=1&gesture=eureka");
  expect(address(stages, "next-stage2-mechanical", undefined, false)).toBe("?stage=2&skeleton=mechanical");  // a switch: its Tour
  expect(address(stages, "next-mech-back", undefined, true)).toBe("?stage=3&explode=1");  // the Tour is the default
  expect(address(stages, "stage3", undefined, false)).toBe("");  // a Stage the page has no button for
  expect(address([], "next-mech-back", undefined, false)).toBe("");  // a page with no buttons
});

test("Explode moves every Stage's parts apart in every Skeleton, each by a 3D offset (#664, #720)", () => {
  for (const [stage, part] of [["next-stage1", "next test stand:1"], ["next-mech-back-mechanical", "next board rack:1"]]) {
    const apart = offsets(stage);
    expect(Object.keys(apart)).toEqual(expect.arrayContaining(["next gimbal frame:1", part]));
    for (const d of Object.values(apart)) expect(d).toHaveLength(3);
    expect(Object.values(apart).some((d) => d.some((x) => x !== 0))).toBe(true);
  }
  expect(offsets("stage3")).toEqual({});
});
