// The site's Theme (docs/adr/0022, #806, #819): a Preset of the model's (model/geometry.py PRESETS, via macros.json),
// picked in the header's bar (src/components/ThemeSelect.astro). A page marks what some Presets alone show with
// data-presets="<slug> ..." (macros.py themed); the bar puts the Preset on <html> as data-preset and css() hides the
// rest, the default's showing where nothing is picked (no script).
import { theme } from "./macros.json";

export const PRESETS = theme.presets; // {slug: {label, <axis>: value}}, the first the default
export const AXES = theme.axes; // {axis: [values]}: each category's Shape and Palette
export const PALETTES = theme.palettes; // {palette axis: {Palette: {Colour group: hex}}}
const SLUGS = Object.keys(PRESETS);

// the address's Preset (?preset=morty), else what the reader picked last (stored), else the default
export function chosen(search, stored) {
  return [new URLSearchParams(search).get("preset"), stored].find((p) => SLUGS.includes(p)) ?? SLUGS[0];
}

// one rule hiding every marked picture and text but the page's Preset's
export function css() {
  const hidden = [
    `:root:not([data-preset]) [data-presets]:not([data-presets~="${SLUGS[0]}"])`,
    ...SLUGS.map((p) => `:root[data-preset="${p}"] [data-presets]:not([data-presets~="${p}"])`),
  ];
  return `${hidden.join(",\n")} { display: none !important; }`;
}
