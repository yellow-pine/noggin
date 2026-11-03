// The viewer's state as plain data (viewer.mjs): the deep link, the caption and Explode's levels; no three.js, so
// Vitest tests them (state.test.mjs) and the browser smoke only loads a Stage (#513)
import { moments, published } from "../macros.json";
import { AXES, PALETTES, PRESETS } from "../theme.mjs";

export const title = (s) => s[0].toUpperCase() + s.slice(1);

// what plays, and the Claude Code event that plays it; the Tour (no gesture) plays every gesture in turn
export const caption = (gesture) => (gesture ? `${title(gesture)}: ${moments[gesture]}` : "Tour: every gesture in turn");

// a Stage's GLB in a Skeleton shape: its name as Bones and the Shape's suffix (#704, #805: "-mechanical"), as macros.py
// stage_switch has them; Blender draws the GLBs per Shape alone (#819)
export const glb = (stage, shape) => stage + (published.stages.skeletons[shape] ?? "");

// the viewer's mix (#819): the Preset's value on each axis (src/theme.mjs), unless the address names another
// (?skeleton-palette=black)
export function mixed(search, preset) {
  const link = new URLSearchParams(search);
  return Object.fromEntries(
    Object.entries(AXES).map(([a, values]) => [a, values.includes(link.get(a)) ? link.get(a) : PRESETS[preset][a]]),
  );
}

// {Colour group: hex} a mix paints a GLB's materials in, each named by its group (web/glb.py): its Palettes'
export const paint = (mix) => Object.assign({}, ...Object.entries(PALETTES).map(([a, palettes]) => palettes[mix[a]]));

// Explode's levels (#811), each a button: every part home, each sub-assembly apart, each part apart
export const LEVELS = ["Assembled", "Sub-assemblies", "Parts"];

// a deep link, ?stage=<n>&gesture=<g>&explode=<level>: the page's nth Stage button's Stage (else `fallback`, the
// viewer's own), its gesture, and its Explode level (LEVELS' index, 0 by default); its Shapes and Palettes are the
// mix's (mixed)
export function opened(search, stages, fallback) {
  const link = new URLSearchParams(search), stage = stages[link.get("stage") - 1] ?? fallback;
  const explode = Math.min(Math.max(parseInt(link.get("explode")) || 0, 0), LEVELS.length - 1);
  return { stage, gesture: link.get("gesture"), explode };
}

// the deep link to what plays: the Stage by its button (where the page has them), the gesture, the Explode level; the
// rest of the address (the Preset, the mix) kept
export function address(stages, stage, gesture, explode, search = "") {
  const n = stages.indexOf(stage) + 1, link = new URLSearchParams(search);
  for (const k of ["stage", "gesture", "explode"]) link.delete(k);
  if (n) link.set("stage", n);
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
