// The viewer's state: its deep link, picker address, caption and explode offsets, from the site's macros.json (npm test)
import { expect, test } from "vitest";
import { address, caption, offsets, opened } from "./state.mjs";

const stages = ["next-mech-a", "next-mech-b"];  // the viewer page's Base candidate buttons, 1 2 (#664)

test("a gesture's caption says which Claude Code event plays it, the Tour's says it tours", () => {
  expect(caption("wink")).toBe("Wink: a session starts (SessionStart)");
  expect(caption()).toBe("Tour: every gesture in turn");
});

test("a deep link opens its nth button's document, its gesture, and exploded only a document that comes apart", () => {
  expect(opened("?stage=1&gesture=wink", stages, "next-mech-b")).toEqual({ stage: "next-mech-a", gesture: "wink", exploded: false });
  expect(opened("?stage=2&explode=1", stages, "next-mech-a")).toEqual({ stage: "next-mech-b", gesture: null, exploded: true });
  expect(opened("?stage=1&explode=1", ["stage1"], "stage1").exploded).toBe(false);  // one without offsets stays together
});

test("with no link, or a Stage the page has no button for, the viewer opens its own Stage", () => {
  expect(opened("", stages, "stage3")).toEqual({ stage: "stage3", gesture: null, exploded: false });
  expect(opened("?stage=7", stages, "next-mech-a").stage).toBe("next-mech-a");
  expect(opened("?stage=1", [], "next-mech-a").stage).toBe("next-mech-a");  // the landing page's hero has no buttons
});

test("the picker keeps the address the deep link to what plays, so it can be shared", () => {
  expect(address(stages, "next-mech-a", "eureka", false)).toBe("?stage=1&gesture=eureka");
  expect(address(stages, "next-mech-b", undefined, false)).toBe("?stage=2");  // a switch: its Tour, put together
  expect(address(stages, "next-mech-b", undefined, true)).toBe("?stage=2&explode=1");  // the Tour is the default
  expect(address([], "next-mech-a", undefined, false)).toBe("");  // the hero, with no buttons
});

test("Explode moves both Base candidates' parts apart, each by a 3D offset; today's Stages have none (#664)", () => {
  for (const [stage, carrier] of [["next-mech-a", "next board tray:1"], ["next-mech-b", "next board tower:1"]]) {
    const apart = offsets(stage);
    expect(Object.keys(apart)).toEqual(expect.arrayContaining(["next base plate:1", carrier]));
    for (const d of Object.values(apart)) expect(d).toHaveLength(3);
    expect(Object.values(apart).some((d) => d.some((x) => x !== 0))).toBe(true);
  }
  expect(offsets("stage3")).toEqual({});
});
