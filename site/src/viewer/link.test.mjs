// The viewer's deep link, picker address, caption and explode offsets, from the site's macros.json (npm test)
import { expect, test } from "vitest";
import { address, caption, offsets, opened } from "./link.mjs";

const stages = ["stage1", "stage2", "stage3"];  // the viewer page's Stage buttons, 1 2 3

test("a gesture's caption says which Claude Code event plays it, the Tour's says it tours", () => {
  expect(caption("wink")).toBe("Wink: a session starts (SessionStart)");
  expect(caption()).toBe("Tour: every gesture in turn");
});

test("a deep link opens its nth Stage button's Stage, its gesture, and exploded only a Stage that comes apart", () => {
  expect(opened("?stage=1&gesture=wink", stages, "stage3")).toEqual({ stage: "stage1", gesture: "wink", exploded: false });
  expect(opened("?stage=3&explode=1", stages, "stage3")).toEqual({ stage: "stage3", gesture: null, exploded: true });
  expect(opened("?stage=1&explode=1", stages, "stage3").exploded).toBe(false);  // Stage 1 has no exploded view
});

test("with no link, or a Stage the page has no button for, the viewer opens its own Stage", () => {
  expect(opened("", stages, "stage3")).toEqual({ stage: "stage3", gesture: null, exploded: false });
  expect(opened("?stage=7", stages, "stage3").stage).toBe("stage3");
  expect(opened("?stage=1", [], "stage3").stage).toBe("stage3");  // the landing page's hero has no Stage buttons
});

test("the picker keeps the address the deep link to what plays, so it can be shared", () => {
  expect(address(stages, "stage1", "eureka", false)).toBe("?stage=1&gesture=eureka");
  expect(address(stages, "stage3", undefined, false)).toBe("?stage=3");  // a Stage switch: its Tour, put together
  expect(address(stages, "stage3", undefined, true)).toBe("?stage=3&explode=1");  // the Tour is the default: no gesture
  expect(address([], "stage3", undefined, false)).toBe("");  // the hero, with no Stage buttons
});

test("Explode moves Stage 3's parts apart, each by a 3D offset; Stages 1 and 2 have none", () => {
  const apart = offsets("stage3");
  expect(Object.keys(apart)).toEqual(expect.arrayContaining(["base plate:1", "receiver shield 1:1", "Core 1:1"]));
  for (const d of Object.values(apart)) expect(d).toHaveLength(3);
  expect(Object.values(apart).some((d) => d.some((x) => x !== 0))).toBe(true);
  expect(offsets("stage1")).toEqual({});
  expect(offsets("stage2")).toEqual({});
});
