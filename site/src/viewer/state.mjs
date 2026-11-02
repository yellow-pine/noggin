// The viewer's state as plain data (viewer.mjs): the deep link, the caption and the explode offsets; no three.js, so
// Vitest tests them (state.test.mjs) and the browser smoke only loads a Stage (#513)
import { explode, moments } from "../macros.json";

export const title = (s) => s[0].toUpperCase() + s.slice(1);

// what plays, and the Claude Code event that plays it; the Tour (no gesture) plays every gesture in turn
export const caption = (gesture) => (gesture ? `${title(gesture)}: ${moments[gesture]}` : "Tour: every gesture in turn");

// a deep link, ?stage=<n>&gesture=<g>&explode=1: the page's nth Stage button's Stage (else `fallback`, the viewer's
// own), its gesture, and exploded only where the Stage comes apart
export function opened(search, stages, fallback) {
  const link = new URLSearchParams(search), stage = stages[link.get("stage") - 1] ?? fallback;
  return { stage, gesture: link.get("gesture"), exploded: link.get("explode") === "1" && stage in explode };
}

// the deep link to what plays: the Stage by its button (where the page has them), the gesture, exploded
export function address(stages, stage, gesture, exploded) {
  const n = stages.indexOf(stage) + 1, link = new URLSearchParams();
  if (n) link.set("stage", n);
  if (gesture) link.set("gesture", gesture);
  if (exploded) link.set("explode", 1);
  return link.size ? `?${link}` : "";
}

// the offsets Explode moves the Stage's parts apart by, each part by its name (macros.json, model/render/pictures.py
// EXPLODE): none for a Stage that does not come apart
export const offsets = (stage) => explode[stage] ?? {};
