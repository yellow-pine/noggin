// The viewer's state as plain data (viewer.mjs): the deep link, the caption and Explode's levels; no three.js, so
// Vitest tests them (state.test.mjs) and the browser smoke only loads a Stage (#513)
import { moments, published } from "../macros.json";
import { AXES, PALETTES, PRESETS } from "../theme.mjs";

export const title = (s) => s[0].toUpperCase() + s.slice(1);

// what plays: a gesture's Claude Code event, Rest's and the hero loop's own line ("next hero" until #895)
const OWN_LINE = { rest: "the Mech at rest, between gestures", hero: "the demo loop, every move in one" };
export function caption(clip) {
  const name = clip.replace(/^next /, "");
  return `${title(name)}: ${moments[name] ?? OWN_LINE[name]}`;
}

// what a viewer plays with no gesture named, round and round: its Stage's hero loop, else Rest (Stage 1: no neck)
export const looped = (clips) => clips.find((c) => c.replace(/^next /, "") === "hero") ?? "rest";

// a Stage's GLB in a Skeleton shape and a Skin shape: its name as Bones, the Skeleton shape's suffix (#704, #805:
// "-mechanical"), then the Skin shape's where the site serves that GLB (#876: none's "-bare", Stage 3's alone), as
// macros.py stage_switch has them; Blender draws the GLBs per Shape alone, the viewer paints each Palette (#819)
export function glb(stage, shape, skin) {
  const bones = stage + (published.stages.skeletons[shape] ?? ""), bare = bones + (published.stages.skins[skin] ?? "");
  return published.viewer.includes(`${bare}.glb`) ? bare : bones;
}

// the viewer's own mix, where no Preset is picked: the Default build (#889), the first Preset's with Skin shape none
// (its first; already the Default build's after #895), so a Skin switched on is the Default Skin palette
const OWN = { ...Object.values(PRESETS)[0], "skin-shape": AXES["skin-shape"][0] };

// the viewer's mix (#819): the picked Preset's value on each axis (src/theme.mjs), else its own, unless the address
// names another (?skeleton-palette=black)
export function mixed(search, preset) {
  const link = new URLSearchParams(search), from = PRESETS[preset] ?? OWN;
  return Object.fromEntries(
    Object.entries(AXES).map(([a, values]) => [a, values.includes(link.get(a)) ? link.get(a) : from[a]]),
  );
}

// {Colour group: hex} a mix paints a GLB's materials in, each named by its group (web/glb.py): its Palettes', black
// as `black`, the charcoal the GLB's look draws it in (web/glb.py, #914)
export const paint = (mix, black) =>
  Object.fromEntries(
    Object.entries(PALETTES).flatMap(([a, palettes]) =>
      Object.entries(palettes[mix[a]] ?? {}).map(([group, hex]) => [group, hex === "#000000" ? black : hex]),
    ),
  );

// Explode's levels (#811), each a button: every part home, each sub-assembly apart, each part apart
export const LEVELS = ["Assembled", "Sub-assemblies", "Parts"];

// the camera's direction from the Stage, in glTF's Y-up (the eyes face +Z, the Mech's left is +X): view= picks one, as
// the pictures' (model/render/pictures.py VIEWS, FRONT); without it the default framing, the old hero GIF's view, 15
// deg to the Mech's right and 15 deg up
export const VIEWS = { front: [0, 0, 1], side: [1, 0, 0], isometric: [1, 1, 1] };
export const VIEW = [-0.25, 0.259, 0.933];

// a deep link, ?stage=<n>&gesture=<g>&explode=<level>&view=<view>&part=<part>: the page's nth Stage button's Stage
// (else `fallback`, the viewer's own), its gesture, its Explode level (LEVELS' index, 0 by default), its view (VIEWS)
// and the one part it shows at full look (none: every part); its Shapes and Palettes are the mix's (mixed)
export function opened(search, stages, fallback) {
  const link = new URLSearchParams(search), stage = stages[link.get("stage") - 1] ?? fallback;
  const explode = Math.min(Math.max(parseInt(link.get("explode")) || 0, 0), LEVELS.length - 1);
  return { stage, gesture: link.get("gesture"), explode, view: VIEWS[link.get("view")] ?? VIEW, part: link.get("part") };
}

// whether a GLB's node (its part's name, Blender's copy number after a colon) is drawn at full look: every one, or the
// part= one's copies alone, the rest ghosted
export const shows = (part, node) => !part || node.replace(/:\d+$/, "") === part;
// a mesh's part: the glTF name of the node it is or sits in (Blender's object, web/glb.py), which GLTFLoader keeps in
// userData.name (its .name is sanitised: "next jaw:1" becomes "next_jaw1")
export const partOf = (o) => o.userData.name ?? (o.parent ? partOf(o.parent) : "");

// what the reader's drag may do (OrbitControls): an embed only turns, the wheel and a pinch left to scroll the page past
// it; the /viewer page's zooms and pans too
export const moves = (full) => ({ enableRotate: true, enableZoom: full, enablePan: full });

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

// the viewers on screen, by when they came into view or were last touched (a drag): the last ANIMATING of them
// animate, the rest hold still, so a page of viewers costs no more than three (#839)
export const ANIMATING = 3;
export const touched = (seen, viewer, on) => [...seen.filter((v) => v !== viewer), ...(on ? [viewer] : [])];

// values (one array per level) `x` of the way through the levels, 0 at the first: between the two levels round it,
// eased so each step starts and stops still
export function between(values, x) {
  const i = Math.min(Math.floor(x), values.length - 2), f = x - i, e = f * f * f * (f * (f * 6 - 15) + 10);
  return values[i].map((v, k) => v + (values[i + 1][k] - v) * e);
}
