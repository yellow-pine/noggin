// The viewer's state: its deep link, picker address, caption and explode offsets, from the site's macros.json (npm test)
import { expect, test } from "vitest";
import { address, caption, offsets, opened } from "./state.mjs";

const stages = ["next-mech-back", "next-mech-crown"];  // the viewer page's first two head variant buttons (#664, #686)

test("a gesture's caption says which Claude Code event plays it, the Tour's says it tours", () => {
  expect(caption("wink")).toBe("Wink: a session starts (SessionStart)");
  expect(caption()).toBe("Tour: every gesture in turn");
});

test("a deep link opens its nth button's document, its gesture, and exploded only a document that comes apart", () => {
  expect(opened("?stage=1&gesture=wink", stages, "next-mech-crown")).toEqual({ stage: "next-mech-back", gesture: "wink", exploded: false });
  expect(opened("?stage=2&explode=1", stages, "next-mech-back")).toEqual({ stage: "next-mech-crown", gesture: null, exploded: true });
  expect(opened("?stage=1&explode=1", ["stage1"], "stage1").exploded).toBe(false);  // one without offsets stays together
});

test("with no link, or a Stage the page has no button for, the viewer opens its own Stage", () => {
  expect(opened("", stages, "stage3")).toEqual({ stage: "stage3", gesture: null, exploded: false });
  expect(opened("?stage=7", stages, "next-mech-back").stage).toBe("next-mech-back");
  expect(opened("?stage=1", [], "next-mech-back").stage).toBe("next-mech-back");  // the landing page's hero has no buttons
});

test("the picker keeps the address the deep link to what plays, so it can be shared", () => {
  expect(address(stages, "next-mech-back", "eureka", false)).toBe("?stage=1&gesture=eureka");
  expect(address(stages, "next-mech-crown", undefined, false)).toBe("?stage=2");  // a switch: its Tour, put together
  expect(address(stages, "next-mech-crown", undefined, true)).toBe("?stage=2&explode=1");  // the Tour is the default
  expect(address([], "next-mech-back", undefined, false)).toBe("");  // the hero, with no buttons
});

test("Explode moves every head variant's parts apart, each by a 3D offset; today's Stages have none (#664, #686)", () => {
  for (const [stage, carrier] of [["next-mech-back", "next board rack:1"], ["next-mech-crown", "next crown shelf:1"], ["next-mech-split", "next switch bracket:1"]]) {
    const apart = offsets(stage);
    expect(Object.keys(apart)).toEqual(expect.arrayContaining(["next torso:1", carrier]));
    for (const d of Object.values(apart)) expect(d).toHaveLength(3);
    expect(Object.values(apart).some((d) => d.some((x) => x !== 0))).toBe(true);
  }
  expect(offsets("stage3")).toEqual({});
});
