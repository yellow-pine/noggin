// The viewer's state as plain data (viewer.mjs): the deep link, the caption and Explode's levels; no three.js, so
// Vitest tests them (state.test.mjs) and the browser smoke only loads a Stage (#513)
import { moments, published } from "../macros.json";

export const title = (s) => s[0].toUpperCase() + s.slice(1);

// what plays, and the Claude Code event that plays it; the Tour (no gesture) plays every gesture in turn
export const caption = (gesture) => (gesture ? `${title(gesture)}: ${moments[gesture]}` : "Tour: every gesture in turn");

// a GLB's name splits into its Stage's (realistic, as Bones) and its Skeleton's suffix (#704, #805: "-mechanical"),
// the Skeletons' as macros.py stage_switch has them
const SUFFIXES = published.stages.skeletons.map((s) => s.suffix).filter(Boolean);
export const skeleton = (stage) => SUFFIXES.find((s) => stage.endsWith(s)) ?? "";
export const bony = (stage) => stage.slice(0, stage.length - skeleton(stage).length);

// Explode's levels (#811), each a button: every part home, each sub-assembly apart, each part apart
export const LEVELS = ["Assembled", "Sub-assemblies", "Parts"];

// a deep link, ?stage=<n>&skeleton=mechanical&gesture=<g>&explode=<level>: the page's nth Stage button's Stage (else
// `fallback`, the viewer's own) in its Skeleton, its gesture, and its Explode level (LEVELS' index, 0 by default)
export function opened(search, stages, fallback) {
  const link = new URLSearchParams(search), base = stages[link.get("stage") - 1];
  const stage = base ? base + (SUFFIXES.find((s) => s === `-${link.get("skeleton")}`) ?? "") : fallback;
  const explode = Math.min(Math.max(parseInt(link.get("explode")) || 0, 0), LEVELS.length - 1);
  return { stage, gesture: link.get("gesture"), explode };
}

// the deep link to what plays: the Stage by its button (where the page has them) and its Skeleton, the gesture, the
// Explode level
export function address(stages, stage, gesture, explode) {
  const n = stages.indexOf(bony(stage)) + 1, link = new URLSearchParams();
  if (n) link.set("stage", n);
  if (n && skeleton(stage)) link.set("skeleton", skeleton(stage).slice(1));
  if (gesture) link.set("gesture", gesture);
  if (explode) link.set("explode", explode);
  return link.size ? `?${link}` : "";
}

// values (one array per level) `x` of the way through the levels, 0 at the first: between the two levels round it,
// eased so each step starts and stops still
export function between(values, x) {
  const i = Math.min(Math.floor(x), values.length - 2), f = x - i, e = f * f * f * (f * (f * 6 - 15) + 10);
  return values[i].map((v, k) => v + (values[i + 1][k] - v) * e);
}
